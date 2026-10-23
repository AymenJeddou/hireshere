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


def _card(i, verdict="eligible"):
    reason = {"en": "Open to <you>", "fr": "Ouvert", "ar": "مفتوح"}
    return {"title": f"Dev & Ops {i}", "company": "Acme", "scope": "EMEA", "verdict": verdict,
            "url": f"https://x.test/{i}?a=1&b=2", "reason": reason}  # fmt: skip


def test_render_subject_language_and_escaping():
    from pipeline.alerts import render

    sub = {"lang": "en", "country": "TN", "family": "data"}
    subject, body, text = render(sub, [_card(1)], "https://u.test/x")
    assert subject == "1 new remote job open to Tunisia"
    assert "Dev &amp; Ops 1" in body and "Open to &lt;you&gt;" in body and "?a=1&amp;b=2" in body
    assert " in data" in text and "https://u.test/x" in text

    subject, body, _ = render(sub | {"lang": "xx"}, [_card(1), _card(2)], "u")
    assert subject.startswith("2 new") and 'dir="ltr"' in body

    _, body, _ = render(sub | {"lang": "ar"}, [_card(1)], "u")
    assert 'dir="rtl"' in body and "/ar/jobs?c=TN" in body


def test_render_caps_the_list_but_counts_everything():
    from pipeline.alerts import MAX_JOBS, render

    jobs = [_card(i) for i in range(MAX_JOBS + 5)]
    subject, body, _ = render({"lang": "en", "country": "TN", "family": ""}, jobs, "u")
    assert subject.startswith(f"{MAX_JOBS + 5} new")
    assert body.count("<tr>") == MAX_JOBS


def test_unsubscribe_token_is_hex_hmac_sha256_like_the_function():
    from pipeline.alerts import unsubscribe_token

    # RFC 4231 test case 2; site/functions/api/unsubscribe.js must produce the same hex
    token = unsubscribe_token("what do ya want for nothing?", "Jefe")
    assert token == "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
