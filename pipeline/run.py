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

REMOTE_WORDS = ["remote", "worldwide", "anywhere", "emea", "africa", "mena"]


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
    db.sync_boards(conn, load_boards())
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


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="pipeline.run")
    p.add_argument("--db", default=config.DB_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch every active board and diff into the database")
    f.add_argument("--limit", type=int, help="only fetch the first N boards (quick test)")
    sub.add_parser("stats", help="print totals")
    args = p.parse_args(argv)

    conn = db.connect(args.db)
    if args.cmd == "fetch":
        report = asyncio.run(cmd_fetch(conn, args.limit))
    else:
        report = cmd_stats(conn)
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n\n")


if __name__ == "__main__":
    main()
