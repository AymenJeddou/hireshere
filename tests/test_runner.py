from pipeline.classify.runner import estimate, verify_evidence
from pipeline.classify.schema import Extraction

JOB = {
    "title": "Backend Engineer (Remote, EMEA)",
    "location_raw": "Remote - Europe",
    "description_text": "We hire anywhere in EMEA.\nYou must overlap with CET hours.",
}


def _e(quote):
    return Extraction(remote_type="fully_remote", geo_scope="regions", engagement="employee",
                      seniority="mid", role_family="engineering", evidence_quote=quote,
                      confidence="high")  # fmt: skip


def test_evidence_found_with_field_prefix_and_case():
    e = _e("Location field: remote - EUROPE")
    assert verify_evidence(e, JOB) and e.confidence == "high"
    assert verify_evidence(_e("we hire anywhere in emea"), JOB)


def test_shortened_quote_matches_its_pieces_in_order():
    assert verify_evidence(_e("We hire anywhere … overlap with CET hours"), JOB)
    assert verify_evidence(_e("We hire...in EMEA"), JOB)
    assert not verify_evidence(_e("overlap with CET … We hire anywhere"), JOB)
    assert not verify_evidence(_e("..."), JOB)


def test_missing_or_invented_evidence_lowers_confidence():
    e = _e("Open to candidates worldwide")
    assert not verify_evidence(e, JOB) and e.confidence == "low"
    assert not verify_evidence(_e(""), JOB)


def test_estimate_batch_is_half_price():
    jobs = [{"title": "T", "company_name": "C", "location_raw": "", "description_text": "x" * 4000,
             "remote_flag_raw": None, "employment_type_raw": None}]  # fmt: skip
    tin, tout, usd = estimate(jobs, batch=False)
    tin2, tout2, usd2 = estimate(jobs, batch=True)
    assert (tin, tout) == (tin2, tout2) and tin > 1000 and usd2 == usd / 2
    assert estimate([], batch=True) == (0, 0, 0)


def test_triage_skips_reuses_dedupes_newest_first():
    import json

    from pipeline import db
    from pipeline.classify.runner import triage
    from pipeline.models import Board, FetchResult, Job

    b = Board(ats="lever", slug="acme", company_name="Acme")
    conn = db.connect(":memory:")
    db.sync_boards(conn, [b])

    def j(n, location="Remote", desc="d"):
        return Job(source="lever", board_slug="acme", source_job_id=str(n), company_name="Acme",
                   title="Engineer", location_raw=location, description_text=desc,
                   apply_url=f"https://x/{n}")  # fmt: skip

    office, known, twin_a, twin_b, newest = (
        j(1, "Paris"), j(2, desc="old"), j(3, desc="same"), j(4, desc="same"), j(5, desc="new"),
    )  # fmt: skip
    order = [office, known, twin_a, twin_b, newest]  # each fetch lists every open job so far
    for n in range(len(order)):
        db.apply_result(
            conn, FetchResult(board=b, ok=True, jobs=order[: n + 1]), f"2026-11-0{n + 1}"
        )
    conn.execute(
        "INSERT INTO extractions VALUES (?, 'm', ?, 0, 0, '')", (known.content_hash, json.dumps({}))
    )

    jobs, counts = triage(conn)
    assert counts == {"skipped": 1, "reused": 1}
    assert [x["content_hash"] for x in jobs] == [newest.content_hash, twin_a.content_hash]
    assert [x["content_hash"] for x in triage(conn, limit=1)[0]] == [newest.content_hash]
    status = {k[-1]: v for k, v in conn.execute("SELECT id, classify_status FROM jobs")}
    assert status["1"] == "skipped" and status["2"] == "done" and status["3"] == "pending"
