"""Pick jobs to classify, estimate cost, call the model, store extractions by content_hash."""

import asyncio
import json
import re
import sqlite3
import sys
from datetime import UTC, datetime

from pipeline import config
from pipeline.classify import gemini
from pipeline.classify.prompt import SYSTEM, prefilter, user_message
from pipeline.classify.schema import JSON_SCHEMA, Extraction

COLS = (
    "id, content_hash, company_name, title, location_raw, remote_flag_raw, "
    "employment_type_raw, description_text"
)
EST_OUTPUT_TOKENS = 220
# The docs say JOB_STATE_*, the live API says BATCH_STATE_*: match on the suffix.
DEAD = ("_FAILED", "_CANCELLED", "_EXPIRED")  # finished without results


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def open_batches(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name, state FROM batches WHERE state != 'COLLECTED'")
    return [name for name, state in rows if not state.endswith(DEAD)]


def triage(conn: sqlite3.Connection, limit: int | None = None) -> tuple[list[dict], dict]:
    """Mark pre-filtered jobs skipped and reuse known extractions. Returns one job per
    content_hash that still needs the model, plus counts."""
    rows = conn.execute(
        f"SELECT {COLS} FROM jobs WHERE expired_at IS NULL "
        # Newest first: fresh jobs matter most (alerts, Telegram); the backlog fills spare capacity.
        "AND classify_status IN ('pending', 'error', 'skipped') ORDER BY first_seen_at DESC, id"
    ).fetchall()
    known = {r[0] for r in conn.execute("SELECT content_hash FROM extractions")}
    todo: dict[str, dict] = {}
    counts = {"skipped": 0, "reused": 0}
    with conn:
        for r in rows:
            job = dict(r)
            if prefilter(job):
                conn.execute(
                    "UPDATE jobs SET classify_status = 'skipped' WHERE id = ?", (job["id"],)
                )
                counts["skipped"] += 1
            elif job["content_hash"] in known:
                conn.execute("UPDATE jobs SET classify_status = 'done' WHERE id = ?", (job["id"],))
                counts["reused"] += 1
            else:
                todo.setdefault(job["content_hash"], job)
    jobs = list(todo.values())
    return (jobs[:limit] if limit else jobs), counts


def estimate(jobs: list[dict], batch: bool) -> tuple[int, int, float]:
    overhead = len(SYSTEM) + len(json.dumps(JSON_SCHEMA))
    tin = sum((overhead + len(user_message(j))) // 4 for j in jobs)
    tout = EST_OUTPUT_TOKENS * len(jobs)
    usd = (tin * config.PRICE_IN + tout * config.PRICE_OUT) / 1e6
    return tin, tout, usd / 2 if batch else usd


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def verify_evidence(e: Extraction, job: dict) -> bool:
    """The quote must really appear in the posting. If not, confidence drops to low."""
    source = _norm(
        " ".join(str(job[k] or "") for k in ("title", "location_raw", "description_text"))
    )
    quote = re.sub(
        r"^(location field|workplace flag|title)\s*:\s*", "", e.evidence_quote, flags=re.I
    )
    ok = bool(quote) and _norm(quote) in source
    if not ok:
        e.confidence = "low"
    return ok


def save(
    conn: sqlite3.Connection, job: dict, e: Extraction, tin: int, tout: int, model: str = ""
) -> None:
    data = e.model_dump() | {"evidence_verified": verify_evidence(e, job)}
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO extractions VALUES (?, ?, ?, ?, ?, ?)",
            (
                job["content_hash"],
                model or config.CLASSIFIER_MODEL,
                json.dumps(data),
                tin,
                tout,
                now(),
            ),
        )
        conn.execute(
            "UPDATE jobs SET classify_status = 'done' WHERE content_hash = ? "
            "AND classify_status IN ('pending', 'error')",
            (job["content_hash"],),
        )


def mark_error(conn: sqlite3.Connection, content_hash: str) -> None:
    with conn:
        conn.execute(
            "UPDATE jobs SET classify_status = 'error' WHERE content_hash = ? "
            "AND classify_status = 'pending'",
            (content_hash,),
        )


async def run_sync(conn: sqlite3.Connection, jobs: list[dict]) -> dict:
    """Free tiers, each provider paced to its own limit and working the same queue at the same
    time: Gemini and Groq. A provider stops at its daily quota; the others carry on. Jobs left
    when time or every quota runs out stay pending for the next run."""
    from collections import deque

    from pipeline.classify import compat

    providers = [(gemini, config.CLASSIFIER_MODEL, config.GEMINI_RPM)]
    providers += [(p, p.model, p.rpm) for p in compat.EXTRA if p.available()]
    t = {"done": 0, "errors": 0, "input_tokens": 0, "output_tokens": 0, "left": 0, "by": {}}
    queue = deque(jobs)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + config.CLASSIFY_MINUTES * 60 if config.CLASSIFY_MINUTES else None

    async def worker(mod, model: str, rpm: float) -> None:
        async with mod.make_client() as client:
            while queue and not (deadline and loop.time() > deadline):
                job = queue.popleft()
                started = loop.time()
                try:
                    e, tin, tout = await mod.generate(client, job)
                except gemini.QuotaError as err:
                    print(f"  {model}: {err}"[:200], file=sys.stderr)
                    queue.appendleft(job)  # another provider takes it
                    return
                except gemini.ModelError as err:
                    print(f"  error {job['id']}: {err}"[:300], file=sys.stderr)
                    mark_error(conn, job["content_hash"])
                    t["errors"] += 1
                else:
                    save(conn, job, e, tin, tout, model)
                    t["done"] += 1
                    t["by"][model] = t["by"].get(model, 0) + 1
                    t["input_tokens"] += tin
                    t["output_tokens"] += tout
                    if t["done"] % 50 == 0:
                        print(f"  {t['done']}/{len(jobs)} classified", file=sys.stderr)
                if rpm:
                    wait = 60 / rpm - (loop.time() - started)
                    if wait > 0:
                        await asyncio.sleep(wait)

    await asyncio.gather(*(worker(*p) for p in providers))
    t["left"] = len(queue)
    return t


async def submit_batch(conn: sqlite3.Connection, jobs: list[dict]) -> str:
    lines = [{"key": j["content_hash"], "request": gemini.request_body(j)} for j in jobs]
    async with gemini.make_client() as client:
        name = await gemini.batch_submit(client, lines, f"{config.PRODUCT_NAME}-{now()}")
    with conn:
        conn.execute(
            "INSERT INTO batches (name, model, submitted_at, requests, state) VALUES (?,?,?,?,?)",
            (name, config.CLASSIFIER_MODEL, now(), len(jobs), "JOB_STATE_PENDING"),
        )
    return name


async def collect(conn: sqlite3.Connection) -> list[str]:
    """Poll open batches once and store finished results. Returns status lines."""
    report = []
    async with gemini.make_client() as client:
        for name in open_batches(conn):
            state, file_name = await gemini.batch_status(client, name)
            if not state.endswith("_SUCCEEDED") or not file_name:
                with conn:
                    conn.execute("UPDATE batches SET state = ? WHERE name = ?", (state, name))
                report.append(f"{name}: {state}")
                continue
            results = await gemini.batch_results(client, file_name)
            hashes = [r.get("key") for r in results]
            jobs = {
                r["content_hash"]: dict(r)
                for r in conn.execute(
                    f"SELECT {COLS} FROM jobs WHERE content_hash IN "
                    f"({','.join('?' * len(hashes))})",
                    hashes,
                )
            }
            ok = err = 0
            for r in results:
                job = jobs.get(r.get("key"))
                if not job:
                    continue
                try:
                    if "error" in r:
                        raise gemini.ModelError(str(r["error"])[:300])
                    e, tin, tout = gemini.parse_response(r["response"])
                    save(conn, job, e, tin, tout)
                    ok += 1
                except gemini.ModelError:
                    mark_error(conn, job["content_hash"])
                    err += 1
            with conn:
                conn.execute(
                    "UPDATE batches SET state = 'COLLECTED', finished_at = ? WHERE name = ?",
                    (now(), name),
                )
            report.append(f"{name}: collected {ok} extractions, {err} errors")
    return report
