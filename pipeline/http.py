"""Shared polite HTTP client: clear User-Agent, timeout, retries with backoff."""

import asyncio

import httpx

from pipeline import config


class FetchError(Exception):
    pass


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"},
        timeout=config.TIMEOUT_SECONDS,
        follow_redirects=True,
    )


async def get_json(client: httpx.AsyncClient, url: str, params: dict | None = None):
    """GET and decode JSON. Retries timeouts, 429 and 5xx. Raises FetchError otherwise."""
    last = ""
    for attempt in range(config.RETRIES + 1):
        if attempt:
            await asyncio.sleep(2**attempt)
        try:
            r = await client.get(url, params=params)
        except httpx.HTTPError as e:
            last = f"{type(e).__name__}: {e}"
            continue
        if r.status_code == 429 or r.status_code >= 500:
            last = f"HTTP {r.status_code}"
            continue
        if r.status_code >= 400:
            raise FetchError(f"HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise FetchError(f"bad JSON: {e}") from e
    raise FetchError(last)
