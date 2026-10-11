"""Gemini REST calls: one-off generateContent and the Batch API. Only this file knows Gemini."""

import asyncio
import json
import os

import httpx

from pipeline import config
from pipeline.classify.prompt import SYSTEM, user_message
from pipeline.classify.schema import JSON_SCHEMA, Extraction

BASE = "https://generativelanguage.googleapis.com"


class ModelError(Exception):
    pass


class QuotaError(ModelError):
    """The provider's free quota for today is used up (or the account is out of credit)."""


def api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ModelError("GEMINI_API_KEY is not set")
    return key


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"x-goog-api-key": api_key(), "User-Agent": config.USER_AGENT},
        timeout=120,
    )


def request_body(job: dict) -> dict:
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user_message(job)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": JSON_SCHEMA,
            "temperature": 0,
        },
    }


def parse_response(data: dict) -> tuple[Extraction, int, int]:
    """generateContent response -> (extraction, input tokens, output tokens)."""
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ModelError(f"no content: {json.dumps(data)[:300]}") from e
    usage = data.get("usageMetadata", {})
    out = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    try:
        return Extraction.model_validate_json(text), usage.get("promptTokenCount", 0), out
    except ValueError as e:
        raise ModelError(f"invalid extraction: {e}"[:300]) from e


async def _post(client: httpx.AsyncClient, url: str, **kw) -> httpx.Response:
    for attempt in range(5):
        if attempt:
            await asyncio.sleep(min(60, 4 * 2**attempt))
        try:
            r = await client.post(url, **kw)
        except httpx.HTTPError:
            continue
        if r.status_code == 429 and "perday" in r.text.lower().replace("_", "").replace(" ", ""):
            raise QuotaError(f"Gemini daily quota: {r.text[:200]}")
        if r.status_code == 402:
            raise QuotaError(f"HTTP 402: {r.text[:200]}")
        if r.status_code == 429 or r.status_code >= 500:
            continue
        if r.status_code >= 400:
            raise ModelError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r
    raise ModelError(f"gave up after retries: {url}")


async def generate(client: httpx.AsyncClient, job: dict) -> tuple[Extraction, int, int]:
    url = f"{BASE}/v1beta/models/{config.CLASSIFIER_MODEL}:generateContent"
    r = await _post(client, url, json=request_body(job))
    return parse_response(r.json())


# Batch API: upload a JSONL file, create a batch from it, poll, download results.


async def batch_submit(client: httpx.AsyncClient, lines: list[dict], display_name: str) -> str:
    payload = "\n".join(json.dumps(x) for x in lines).encode()
    start = await _post(
        client,
        f"{BASE}/upload/v1beta/files",
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(len(payload)),
            "X-Goog-Upload-Header-Content-Type": "application/jsonl",
        },
        json={"file": {"display_name": display_name}},
    )
    upload_url = start.headers["x-goog-upload-url"]
    done = await _post(
        client,
        upload_url,
        headers={"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"},
        content=payload,
    )
    file_name = done.json()["file"]["name"]
    r = await _post(
        client,
        f"{BASE}/v1beta/models/{config.CLASSIFIER_MODEL}:batchGenerateContent",
        json={"batch": {"display_name": display_name, "input_config": {"file_name": file_name}}},
    )
    return r.json()["name"]


async def batch_status(client: httpx.AsyncClient, name: str) -> tuple[str, str | None]:
    """(state, result file name if finished). Handles both documented response shapes."""
    r = await client.get(f"{BASE}/v1beta/{name}")
    r.raise_for_status()
    d = r.json()
    meta = d.get("metadata", d)
    state = meta.get("state", "UNKNOWN")
    out = d.get("response") or meta.get("output") or d.get("dest") or {}
    return state, out.get("responsesFile") or out.get("fileName")


async def batch_results(client: httpx.AsyncClient, file_name: str) -> list[dict]:
    r = await client.get(f"{BASE}/download/v1beta/{file_name}:download", params={"alt": "media"})
    r.raise_for_status()
    return [json.loads(line) for line in r.text.splitlines() if line.strip()]
