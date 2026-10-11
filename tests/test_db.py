import asyncio

import pytest

from pipeline import config, db, run
from pipeline.http import FetchError
from pipeline.models import Board, FetchResult, Job

B = Board(ats="lever", slug="acme", company_name="Acme")
OTHER = Board(ats="lever", slug="other", company_name="Other")


def job(n, board=B, desc="desc"):
    return Job(
        source=board.ats,
        board_slug=board.slug,
        source_job_id=str(n),
        company_name=board.company_name,
        title=f"Job {n}",
        location_raw="Remote",
        description_text=desc,
        apply_url=f"https://x/{n}",
    )


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.sync_boards(c, [B, OTHER])
    return c


def ok(*jobs, board=B):
    return FetchResult(board=board, ok=True, jobs=list(jobs))


def fail(board=B):
    return FetchResult(board=board, ok=False, error="HTTP 503")


def row(c, id_):
    return c.execute("SELECT * FROM jobs WHERE id = ?", (id_,)).fetchone()


def brd(c, board=B):
    return c.execute("SELECT * FROM boards WHERE slug = ?", (board.slug,)).fetchone()


def test_rule1_insert_and_refresh(conn):
    assert db.apply_result(conn, ok(job(1)), "t1").new == 1
    r = row(conn, "lever:acme:1")
    assert (r["first_seen_at"], r["last_seen_at"], r["classify_status"]) == ("t1", "t1", "pending")
    d = db.apply_result(conn, ok(job(1)), "t2")
    assert (d.new, d.updated, d.expired) == (0, 0, 0)
    r = row(conn, "lever:acme:1")
    assert (r["first_seen_at"], r["last_seen_at"]) == ("t1", "t2")


def test_rule1_reappearing_job_clears_expired_at(conn):
    db.apply_result(conn, ok(job(1)), "t1")
    db.apply_result(conn, ok(), "t2")
    assert row(conn, "lever:acme:1")["expired_at"] == "t2"
    db.apply_result(conn, ok(job(1)), "t3")
    assert row(conn, "lever:acme:1")["expired_at"] is None


def test_rule2_missing_job_expires(conn):
    db.apply_result(conn, ok(job(1), job(2)), "t1")
    assert db.apply_result(conn, ok(job(1)), "t2").expired == 1
    assert row(conn, "lever:acme:2")["expired_at"] == "t2"
    assert row(conn, "lever:acme:1")["expired_at"] is None
    # An already expired job keeps its original expiry date.
    assert db.apply_result(conn, ok(job(1)), "t3").expired == 0
    assert row(conn, "lever:acme:2")["expired_at"] == "t2"


def test_rule2_only_touches_its_own_board(conn):
    db.apply_result(conn, ok(job(9, OTHER), board=OTHER), "t1")
    db.apply_result(conn, ok(job(1)), "t1")
    db.apply_result(conn, ok(), "t2")
    assert row(conn, "lever:other:9")["expired_at"] is None


def test_rule3_failed_fetch_expires_nothing(conn):
    db.apply_result(conn, ok(job(1), job(2)), "t1")
    d = db.apply_result(conn, fail(), "t2")
    assert (d.new, d.updated, d.expired) == (0, 0, 0)
    for i in (1, 2):
        r = row(conn, f"lever:acme:{i}")
        assert r["expired_at"] is None and r["last_seen_at"] == "t1"
    b = brd(conn)
    assert b["consecutive_failures"] == 1 and b["last_error"] == "HTTP 503"
    assert b["last_ok_at"] == "t1"


def test_rule3_end_to_end_network_failure(conn, monkeypatch):
    """A connector that raises (timeout, 5xx, bad JSON) is a failure, never empty."""
    db.apply_result(conn, ok(job(1)), "t1")

    async def boom(client, board):
        raise FetchError("ReadTimeout")

    monkeypatch.setitem(run.CONNECTORS, "lever", type("C", (), {"fetch": staticmethod(boom)}))
    res = asyncio.run(run.fetch_board(None, B, asyncio.Semaphore(1)))
    assert not res.ok and "ReadTimeout" in res.error
    assert db.apply_result(conn, res, "t2").expired == 0
    assert row(conn, "lever:acme:1")["expired_at"] is None


def test_rule3_success_resets_failures(conn):
    db.apply_result(conn, fail(), "t1")
    db.apply_result(conn, fail(), "t2")
    db.apply_result(conn, ok(job(1)), "t3")
    assert brd(conn)["consecutive_failures"] == 0


def test_rule4_content_change_resets_classify_status(conn):
    db.apply_result(conn, ok(job(1)), "t1")
    conn.execute("UPDATE jobs SET classify_status = 'done'")
    assert db.apply_result(conn, ok(job(1)), "t2").updated == 0
    assert row(conn, "lever:acme:1")["classify_status"] == "done"
    assert db.apply_result(conn, ok(job(1, desc="new text")), "t3").updated == 1
    r = row(conn, "lever:acme:1")
    assert r["classify_status"] == "pending" and r["description_text"] == "new text"


def test_rule5_deactivate_after_five_failures(conn):
    for i in range(config.MAX_CONSECUTIVE_FAILURES - 1):
        assert not db.apply_result(conn, fail(), f"t{i}").deactivated
    assert brd(conn)["active"] == 1
    assert db.apply_result(conn, fail(), "t9").deactivated
    assert brd(conn)["active"] == 0
    assert "acme" not in [b.slug for b in db.active_boards(conn)]
    # Re-syncing the seed list does not resurrect it.
    db.sync_boards(conn, [B])
    assert brd(conn)["active"] == 0


def test_idempotent_second_run(conn):
    jobs = [job(i) for i in range(5)]
    assert db.apply_result(conn, ok(*jobs), "t1").new == 5
    second = db.apply_result(conn, ok(*jobs), "t2")
    assert (second.new, second.updated, second.expired) == (0, 0, 0)


def test_board_removed_from_seed_list_is_retired(conn):
    db.apply_result(conn, ok(job(1)), "t1")
    db.apply_result(conn, ok(job(9, OTHER), board=OTHER), "t1")
    assert db.sync_boards(conn, [OTHER], "t2") == 1
    assert brd(conn)["active"] == 0
    assert row(conn, "lever:acme:1")["expired_at"] == "t2"
    assert row(conn, "lever:other:9")["expired_at"] is None
    assert db.sync_boards(conn, [OTHER], "t3") == 0


def test_rolling_feed_expires_by_age_not_absence(conn, monkeypatch):
    monkeypatch.setitem(config.ROLLING_DAYS, "lever", 30)
    old, new = job(1), job(2)
    old.posted_at, new.posted_at = "2026-08-01T00:00:00+00:00", "2026-10-05T00:00:00+00:00"
    db.apply_result(
        conn, FetchResult(board=B, ok=True, jobs=[old, new]), "2026-10-06T00:00:00+00:00"
    )
    diff = db.apply_result(
        conn, FetchResult(board=B, ok=True, jobs=[]), "2026-10-11T00:00:00+00:00"
    )
    assert diff.expired == 1
    open_ = [r[0] for r in conn.execute("SELECT id FROM jobs WHERE expired_at IS NULL")]
    assert open_ == [new.id]
