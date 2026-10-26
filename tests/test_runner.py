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
