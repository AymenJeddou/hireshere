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
