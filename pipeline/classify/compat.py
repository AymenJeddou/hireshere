"""OpenAI-compatible chat completions on free tiers (Groq, Mistral): extra classifiers that work
the queue next to Gemini. One class; each provider is a few lines of configuration below."""

import asyncio
import json
import os

import httpx

from pipeline import config
from pipeline.classify.gemini import ModelError, QuotaError
from pipeline.classify.prompt import SYSTEM, user_message
from pipeline.classify.schema import JSON_SCHEMA, Extraction


class Provider:
    def __init__(self, name: str, url: str, key_env: str, model: str, rpm_env: str, extra: dict):
        self.name, self.url, self.key_env, self.model = name, url, key_env, model
        self.rpm_env, self.extra = rpm_env, extra

    def available(self) -> bool:
        return bool(os.environ.get(self.key_env))

    @property
    def rpm(self) -> float:
        return float(os.environ.get(self.rpm_env, "0"))

    def make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {os.environ[self.key_env]}",
                "User-Agent": config.USER_AGENT,
            },
            timeout=120,
        )

    def request_body(self, job: dict) -> dict:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_message(job)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": JSON_SCHEMA, "strict": False},
            },
            "temperature": 0,
            **self.extra,
        }

    async def generate(self, client: httpx.AsyncClient, job: dict) -> tuple[Extraction, int, int]:
        r = None
        for attempt in range(5):
            try:
                r = await client.post(self.url, json=self.request_body(job))
            except httpx.HTTPError:
                await asyncio.sleep(4 * 2**attempt)
                continue
            if r.status_code == 429:
                # Daily or monthly caps end the run for this provider; per-minute caps say how
                # long to wait.
                body = r.text.lower()
                no_plan = r.headers.get("x-ratelimit-limit-req-minute") == "0"  # e.g. no free plan
                if no_plan or "per day" in body or "per month" in body or "monthly" in body:
                    raise QuotaError(f"{self.name} quota: {r.text[:200]}")
                await asyncio.sleep(min(60, float(r.headers.get("retry-after") or 10)))
                continue
            if r.status_code == 402:
                raise QuotaError(f"{self.name} HTTP 402: {r.text[:200]}")
            if r.status_code >= 500:
                await asyncio.sleep(4 * 2**attempt)
                continue
            if r.status_code >= 400:
                raise ModelError(f"{self.name} HTTP {r.status_code}: {r.text[:300]}")
            return parse_response(r.json())
        if r is not None and r.status_code == 429:
            # Still rate limited after every retry: leave the queue to the other providers.
            raise QuotaError(f"{self.name}: still rate limited after retries")
        raise ModelError(f"{self.name}: gave up after retries")


def parse_response(data: dict) -> tuple[Extraction, int, int]:
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ModelError(f"no content: {json.dumps(data)[:300]}") from e
    usage = data.get("usage") or {}
    try:
        e = Extraction.model_validate_json(text)
    except ValueError as err:
        raise ModelError(f"invalid extraction: {err}"[:300]) from err
    return e, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


GROQ = Provider(
    "Groq",
    "https://api.groq.com/openai/v1/chat/completions",
    "GROQ_API_KEY",
    os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
    "GROQ_RPM",
    {"reasoning_effort": "low"},
)
MISTRAL = Provider(
    "Mistral",
    "https://api.mistral.ai/v1/chat/completions",
    "MISTRAL_API_KEY",
    os.environ.get("MISTRAL_MODEL", "mistral-small-latest"),
    "MISTRAL_RPM",
    {},
)
EXTRA = [GROQ, MISTRAL]
