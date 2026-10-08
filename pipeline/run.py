"""CLI: python -m pipeline.run fetch [--limit N] | stats"""

import argparse
import asyncio
import csv
import os
import sys
from datetime import UTC, datetime

from pipeline import config, db
from pipeline.connectors import CONNECTORS
from pipeline.http import FetchError, make_client
from pipeline.models import Board, FetchResult

REMOTE_WORDS = ["remote", "worldwide", "anywhere", "emea", "africa"]


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_boards(path: str = config.BOARDS_CSV) -> list[Board]:
    with open(path, newline="", encoding="utf-8") as f:
        return [Board(**row) for row in csv.DictReader(f)]


async def fetch_board(client, board: Board, sem: asyncio.Semaphore) -> FetchResult:
    async with sem:
        try:
            jobs = await CONNECTORS[board.ats].fetch(client, board)
            return FetchResult(board=board, ok=True, jobs=jobs)
        except (FetchError, KeyError, TypeError, ValueError) as e:
            return FetchResult(board=board, ok=False, error=f"{type(e).__name__}: {e}"[:300])


async def fetch_all(boards: list[Board]):
    """Yield results as they complete, max MAX_CONCURRENCY in flight."""
    sem = asyncio.Semaphore(config.MAX_CONCURRENCY)
    async with make_client() as client:
        tasks = [asyncio.create_task(fetch_board(client, b, sem)) for b in boards]
        for done in asyncio.as_completed(tasks):
            yield await done


async def cmd_fetch(conn, limit: int | None) -> str:
    retired = db.sync_boards(conn, load_boards(), now())
    if retired:
        print(f"  retired {retired} boards no longer in the seed list", file=sys.stderr)
    boards = db.active_boards(conn)[:limit] if limit else db.active_boards(conn)
    run_id = db.start_run(conn, now())
    t = {"boards_ok": 0, "boards_failed": 0, "new": 0, "updated": 0, "expired": 0}
    failures, deactivated = [], []
    i = 0
    async for res in fetch_all(boards):
        i += 1
        diff = db.apply_result(conn, res, now())
        t["boards_ok" if res.ok else "boards_failed"] += 1
        t["new"] += diff.new
        t["updated"] += diff.updated
        t["expired"] += diff.expired
        if not res.ok:
            failures.append(f"{res.board.ats}/{res.board.slug}: {res.error}")
        if diff.deactivated:
            deactivated.append(f"{res.board.ats}/{res.board.slug}")
        if i % 50 == 0:
            print(f"  {i}/{len(boards)} boards", file=sys.stderr)
    db.finish_run(conn, run_id, now(), t)

    lines = [
        f"## {config.PRODUCT_NAME} fetch run #{run_id}",
        "",
        "| boards ok | boards failed | new | updated | expired |",
        "|---|---|---|---|---|",
        f"| {t['boards_ok']} | {t['boards_failed']} | {t['new']} | {t['updated']} "
        f"| {t['expired']} |",
    ]
    if deactivated:
        lines += ["", f"**Deactivated after {config.MAX_CONSECUTIVE_FAILURES} failures:**"]
        lines += [f"- {d}" for d in deactivated]
    if failures:
        lines += ["", "<details><summary>Failed boards</summary>", ""]
        lines += [f"- {f}" for f in sorted(failures)] + ["", "</details>"]
    return "\n".join(lines)


def cmd_stats(conn) -> str:
    q = conn.execute
    open_ = "expired_at IS NULL"
    out = [f"## {config.PRODUCT_NAME} stats", ""]
    total = q(f"SELECT COUNT(*) FROM jobs WHERE {open_}").fetchone()[0]
    boards = q(f"SELECT COUNT(DISTINCT source || board_slug) FROM jobs WHERE {open_}").fetchone()[0]
    active = q("SELECT COUNT(*) FROM boards WHERE active = 1").fetchone()[0]
    out.append(f"Open jobs: **{total}** from **{boards}** boards ({active} active boards)\n")

    out += ["| source | boards | open jobs |", "|---|---|---|"]
    for r in q(
        f"""SELECT source, COUNT(DISTINCT board_slug) b, COUNT(*) n FROM jobs WHERE {open_}
            GROUP BY source ORDER BY n DESC"""
    ):
        out.append(f"| {r['source']} | {r['b']} | {r['n']} |")

    run = q("SELECT * FROM runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    if run:
        out.append(
            f"\nLast run #{run['id']} ({run['started_at']}): {run['jobs_new']} new, "
            f"{run['jobs_updated']} updated, {run['jobs_expired']} expired, "
            f"{run['boards_failed']} boards failed"
        )

    out += ["", "Location text mentions (open jobs):", ""]
    for w in REMOTE_WORDS:
        n = q(
            f"SELECT COUNT(*) FROM jobs WHERE {open_} AND "
            "(location_raw LIKE ? OR remote_flag_raw LIKE ?)",
            (f"%{w}%", f"%{w}%"),
        ).fetchone()[0]
        out.append(f"- {w}: {n}")
    any_ = " OR ".join(["location_raw LIKE ? OR remote_flag_raw LIKE ?"] * len(REMOTE_WORDS))
    params = [f"%{w}%" for w in REMOTE_WORDS for _ in (0, 1)]
    n = q(f"SELECT COUNT(*) FROM jobs WHERE {open_} AND ({any_})", params).fetchone()[0]
    out.append(f"- any of the above: **{n}**")

    out += ["", "Top companies:", ""]
    for r in q(
        f"""SELECT company_name, COUNT(*) n FROM jobs WHERE {open_}
            GROUP BY company_name ORDER BY n DESC LIMIT 10"""
    ):
        out.append(f"- {r['company_name']}: {r['n']}")
    return "\n".join(out)


async def cmd_classify(conn, limit: int | None, batch: bool, yes: bool) -> str:
    from pipeline.classify import runner

    if busy := runner.open_batches(conn):
        return f"A batch is still open ({', '.join(busy)}). Run classify-collect first."
    jobs, counts = runner.triage(conn, limit)
    tin, tout, usd = runner.estimate(jobs, batch)
    mode = "batch" if batch else "sync"
    lines = [
        f"## {config.PRODUCT_NAME} classify ({mode}, {config.CLASSIFIER_MODEL})",
        "",
        f"Pre-filtered as on-site or no remote signal: {counts['skipped']}. "
        f"Reused earlier extractions: {counts['reused']}.",
        f"To classify: {len(jobs)} unique postings, about {tin:,} input and {tout:,} output "
        f"tokens, estimated **${usd:.2f}**.",
    ]
    if not jobs:
        return "\n".join(lines)
    if usd > config.MAX_USD_WITHOUT_CONFIRM and not yes:
        lines.append(f"Over ${config.MAX_USD_WITHOUT_CONFIRM:.0f}: not started. Re-run with --yes.")
        return "\n".join(lines)
    print("\n".join(lines), file=sys.stderr)
    if batch:
        name = await runner.submit_batch(conn, jobs)
        lines.append(f"Submitted batch `{name}`. Run classify-collect later.")
    else:
        t = await runner.run_sync(conn, jobs)
        real = (t["input_tokens"] * config.PRICE_IN + t["output_tokens"] * config.PRICE_OUT) / 1e6
        lines.append(
            f"Classified {t['done']}, errors {t['errors']}. Actual tokens: "
            f"{t['input_tokens']:,} in, {t['output_tokens']:,} out, about ${real:.2f}."
        )
    return "\n".join(lines)


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env support for local runs. Real environment variables win."""
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                os.environ.setdefault(key.strip(), value.strip())


def main(argv=None) -> None:
    load_dotenv()
    p = argparse.ArgumentParser(prog="pipeline.run")
    p.add_argument("--db", default=config.DB_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch every active board and diff into the database")
    f.add_argument("--limit", type=int, help="only fetch the first N boards (quick test)")
    sub.add_parser("stats", help="print totals")
    c = sub.add_parser("classify", help="extract eligibility fields for pending jobs")
    c.add_argument("--limit", type=int, help="only classify N postings")
    c.add_argument("--batch", action="store_true", help="submit through the Batch API (half price)")
    c.add_argument("--yes", action="store_true", help="run even if the estimate is over the cap")
    sub.add_parser("classify-collect", help="store results of finished batches")
    args = p.parse_args(argv)

    conn = db.connect(args.db)
    if args.cmd == "fetch":
        report = asyncio.run(cmd_fetch(conn, args.limit))
    elif args.cmd == "classify":
        report = asyncio.run(cmd_classify(conn, args.limit, args.batch, args.yes))
    elif args.cmd == "classify-collect":
        from pipeline.classify import runner

        lines = asyncio.run(runner.collect(conn)) or ["No open batches."]
        report = "\n".join(f"- {x}" for x in lines)
    else:
        report = cmd_stats(conn)
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n\n")


if __name__ == "__main__":
    main()
