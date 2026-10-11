"""Groq (OpenAI-compatible) chat completions: the free fallback once Gemini's quota is used."""

import asyncio
import json
import os

import httpx

from pipeline import config
from pipeline.classify.gemini import ModelError, QuotaError
from pipeline.classify.prompt import SYSTEM, user_message
from pipeline.classify.schema import JSON_SCHEMA, Extraction

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def available() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "User-Agent": config.USER_AGENT,
        },
        timeout=120,
    )


def request_body(job: dict) -> dict:
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_message(job)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "extraction", "schema": JSON_SCHEMA, "strict": False},
        },
        "temperature": 0,
        "reasoning_effort": "low",
    }


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


async def generate(client: httpx.AsyncClient, job: dict) -> tuple[Extraction, int, int]:
    for attempt in range(5):
        try:
            r = await client.post(URL, json=request_body(job))
        except httpx.HTTPError:
            await asyncio.sleep(4 * 2**attempt)
            continue
        if r.status_code == 429:
            # Daily request or token caps end the day for this provider; per-minute caps
            # say how long to wait.
            if "per day" in r.text.lower():
                raise QuotaError(f"Groq daily quota: {r.text[:200]}")
            await asyncio.sleep(min(60, float(r.headers.get("retry-after") or 10)))
            continue
        if r.status_code >= 500:
            await asyncio.sleep(4 * 2**attempt)
            continue
        if r.status_code >= 400:
            raise ModelError(f"HTTP {r.status_code}: {r.text[:300]}")
        return parse_response(r.json())
    raise ModelError("Groq: gave up after retries")
