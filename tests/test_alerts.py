from datetime import UTC, datetime

from pipeline.alerts import due

NOW = datetime(2026, 10, 23, 4, 30, tzinfo=UTC)


def test_due_once_per_utc_day():
    assert due(None, NOW)
    assert due("", NOW)
    assert due("2026-10-22T23:59:00Z", NOW)
    assert not due("2026-10-23T00:01:00Z", NOW)
    assert not due("2026-10-23T03:00:00+00:00", NOW)


def test_due_reads_offsets_as_utc():
    # 01:00 on the 23rd in UTC+2 is still the 22nd in UTC
    assert due("2026-10-23T01:00:00+02:00", NOW)


def _job(id, verdict="eligible", family="engineering", days_ago=1, **kw):
    from datetime import timedelta

    seen = (datetime.now(UTC) - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
    return {"id": id, "verdict": verdict, "family": family, "seen_at": seen, "posted_at": None} | kw


def test_pick_new_shown_jobs_eligible_first_then_newest():
    from pipeline.alerts import pick

    jobs = [
        _job("a", "likely"),
        _job("b", "eligible"),
        _job("c", "unclear"),
        _job("d", "eligible"),
        _job("old", "eligible"),
    ]
    seen = {"a": "2026-10-23T05", "b": "2026-10-23T01", "c": "2026-10-23T09", "d": "2026-10-23T02",
            "old": "2026-10-20T00"}  # fmt: skip
    assert [j["id"] for j in pick(jobs, seen, "2026-10-22", "")] == ["d", "b", "a"]


def test_pick_filters_field_and_stale_postings():
    from pipeline.alerts import pick

    jobs = [_job("a", family="data"), _job("b"), _job("stale", days_ago=40)]
    seen = {"a": "2026-10-23", "b": "2026-10-23", "stale": "2026-10-23"}
    assert [j["id"] for j in pick(jobs, seen, "2026-10-22", "data")] == ["a"]
    assert [j["id"] for j in pick(jobs, seen, "2026-10-22", "")] == ["a", "b"]
