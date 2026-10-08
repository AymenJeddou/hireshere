"""SQLite schema and the diff rules from docs/SPEC.md section 6."""

import sqlite3
from dataclasses import dataclass

from pipeline import config
from pipeline.models import Board, FetchResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS boards (
    ats TEXT NOT NULL,
    slug TEXT NOT NULL,
    company_name TEXT NOT NULL,
    website TEXT,
    source_of_entry TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    last_ok_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    PRIMARY KEY (ats, slug)
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    board_slug TEXT NOT NULL,
    company_name TEXT NOT NULL,
    title TEXT NOT NULL,
    location_raw TEXT,
    remote_flag_raw TEXT,
    department TEXT,
    employment_type_raw TEXT,
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT,
    description_text TEXT,
    apply_url TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expired_at TEXT,
    classify_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (classify_status IN ('pending', 'done', 'skipped', 'error'))
);
CREATE INDEX IF NOT EXISTS jobs_board ON jobs (source, board_slug);
CREATE INDEX IF NOT EXISTS jobs_classify ON jobs (classify_status);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    boards_ok INTEGER DEFAULT 0,
    boards_failed INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    jobs_expired INTEGER DEFAULT 0
);
"""

JOB_FIELDS = [
    "source", "board_slug", "company_name", "title", "location_raw", "remote_flag_raw",
    "department", "employment_type_raw", "salary_min", "salary_max", "salary_currency",
    "description_text", "apply_url", "content_hash",
]  # fmt: skip


@dataclass
class Diff:
    new: int = 0
    updated: int = 0
    expired: int = 0
    deactivated: bool = False


def connect(path: str = config.DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def sync_boards(conn: sqlite3.Connection, boards: list[Board], now: str = "") -> int:
    """Add boards from the seed list. Existing rows keep their health state.

    Boards no longer in the seed list are retired and their open jobs expired:
    a deliberate removal, unlike a fetch failure. Returns how many were retired.
    """
    keep = {(b.ats, b.slug) for b in boards}
    with conn:
        gone = [
            (r["ats"], r["slug"])
            for r in conn.execute("SELECT ats, slug FROM boards WHERE active = 1")
            if (r["ats"], r["slug"]) not in keep
        ]
        for ats, slug in gone:
            conn.execute(
                "UPDATE boards SET active = 0, last_error = 'removed from seed list' "
                "WHERE ats = ? AND slug = ?",
                (ats, slug),
            )
            conn.execute(
                "UPDATE jobs SET expired_at = ? WHERE source = ? AND board_slug = ? "
                "AND expired_at IS NULL",
                (now, ats, slug),
            )
        conn.executemany(
            """INSERT INTO boards (ats, slug, company_name, website, source_of_entry)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (ats, slug) DO UPDATE SET company_name = excluded.company_name,
                 website = excluded.website, source_of_entry = excluded.source_of_entry""",
            [(b.ats, b.slug, b.company_name, b.website, b.source_of_entry) for b in boards],
        )
    return len(gone)


def active_boards(conn: sqlite3.Connection) -> list[Board]:
    rows = conn.execute("SELECT * FROM boards WHERE active = 1 ORDER BY ats, slug")
    return [Board(**{k: r[k] or "" for k in Board.model_fields}) for r in rows]


def apply_result(conn: sqlite3.Connection, result: FetchResult, now: str) -> Diff:
    b, diff = result.board, Diff()
    with conn:
        if not result.ok:
            # Rule 3: a failed fetch never expires anything.
            conn.execute(
                """UPDATE boards SET consecutive_failures = consecutive_failures + 1,
                   last_error = ? WHERE ats = ? AND slug = ?""",
                (result.error, b.ats, b.slug),
            )
            # Rule 5: retire a board after N failures in a row.
            cur = conn.execute(
                "UPDATE boards SET active = 0 WHERE ats = ? AND slug = ? AND active = 1 "
                "AND consecutive_failures >= ?",
                (b.ats, b.slug, config.MAX_CONSECUTIVE_FAILURES),
            )
            diff.deactivated = cur.rowcount > 0
            return diff

        conn.execute(
            """UPDATE boards SET consecutive_failures = 0, last_ok_at = ?, last_error = NULL
               WHERE ats = ? AND slug = ?""",
            (now, b.ats, b.slug),
        )
        existing = {
            r["id"]: (r["content_hash"], r["expired_at"])
            for r in conn.execute(
                "SELECT id, content_hash, expired_at FROM jobs WHERE source = ? AND board_slug = ?",
                (b.ats, b.slug),
            )
        }
        seen = set()
        for job in result.jobs:
            if job.id in seen:
                continue
            seen.add(job.id)
            values = [getattr(job, f) for f in JOB_FIELDS]
            if job.id not in existing:
                conn.execute(
                    f"""INSERT INTO jobs (id, {", ".join(JOB_FIELDS)}, first_seen_at, last_seen_at)
                        VALUES (?, {", ".join("?" * len(JOB_FIELDS))}, ?, ?)""",
                    [job.id, *values, now, now],
                )
                diff.new += 1
                continue
            old_hash, expired_at = existing[job.id]
            changed = old_hash != job.content_hash
            # Rule 1: refresh last_seen_at and clear expired_at.
            # Rule 4: a content change sends the job back to the classifier.
            conn.execute(
                f"""UPDATE jobs SET {", ".join(f"{f} = ?" for f in JOB_FIELDS)},
                    last_seen_at = ?, expired_at = NULL,
                    classify_status = CASE WHEN ? THEN 'pending' ELSE classify_status END
                    WHERE id = ?""",
                [*values, now, changed, job.id],
            )
            if changed or expired_at:
                diff.updated += 1
        # Rule 2: anything not in a successful fetch is gone.
        gone = [i for i, (_, exp) in existing.items() if i not in seen and exp is None]
        conn.executemany("UPDATE jobs SET expired_at = ? WHERE id = ?", [(now, i) for i in gone])
        diff.expired = len(gone)
    return diff


def start_run(conn: sqlite3.Connection, now: str) -> int:
    with conn:
        return conn.execute("INSERT INTO runs (started_at) VALUES (?)", (now,)).lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, now: str, totals: dict) -> None:
    with conn:
        conn.execute(
            """UPDATE runs SET finished_at = ?, boards_ok = ?, boards_failed = ?,
               jobs_new = ?, jobs_updated = ?, jobs_expired = ? WHERE id = ?""",
            (now, totals["boards_ok"], totals["boards_failed"], totals["new"],
             totals["updated"], totals["expired"], run_id),
        )  # fmt: skip
