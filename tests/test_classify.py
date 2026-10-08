import json

import pytest

from pipeline import config
from pipeline.classify import gemini, runner
from pipeline.classify.prompt import excerpt, prefilter
from pipeline.classify.schema import JSON_SCHEMA, Extraction
from pipeline.classify.verdict import verdict

TN, EG = config.COUNTRIES["TN"], config.COUNTRIES["EG"]


def ex(**kw) -> Extraction:
    base = dict(
        remote_type="fully_remote",
        geo_scope="unclear",
        engagement="employee",
        seniority="mid",
        role_family="engineering",
        evidence_quote="Remote",
        confidence="high",
    )
    return Extraction(**(base | kw))


@pytest.mark.parametrize(
    ("kw", "expected"),
    [
        ({"geo_scope": "worldwide"}, "eligible"),
        ({"geo_scope": "worldwide", "confidence": "low"}, "likely"),
        ({"geo_scope": "worldwide", "excluded_countries": ["TN"]}, "not_eligible"),
        ({"geo_scope": "regions", "allowed_regions": ["EMEA"]}, "likely"),
        ({"geo_scope": "regions", "allowed_regions": ["Africa"]}, "likely"),
        ({"geo_scope": "regions", "allowed_regions": ["Europe"]}, "not_eligible"),
        ({"geo_scope": "regions", "allowed_regions": ["LATAM", "APAC"]}, "not_eligible"),
        ({"geo_scope": "countries", "allowed_countries": ["TN", "MA"]}, "eligible"),
        ({"geo_scope": "countries", "allowed_countries": ["US"]}, "not_eligible"),
        ({"geo_scope": "worldwide", "work_authorization_required": ["US"]}, "not_eligible"),
        ({"geo_scope": "timezone_only", "timezone_utc_min": -1, "timezone_utc_max": 3}, "likely"),
        (
            {"geo_scope": "timezone_only", "timezone_utc_min": -8, "timezone_utc_max": -5},
            "not_eligible",
        ),
        (
            {"geo_scope": "worldwide", "timezone_utc_min": -8, "timezone_utc_max": -5},
            "not_eligible",
        ),
        ({"geo_scope": "unclear"}, "unclear"),
        ({"remote_type": "unclear"}, "unclear"),
        ({"remote_type": "onsite", "allowed_countries": ["US"]}, "not_eligible"),
        ({"remote_type": "hybrid", "allowed_countries": ["TN"]}, "likely"),
        # Countries listed alongside a region: the explicit list wins.
        (
            {
                "geo_scope": "countries",
                "allowed_countries": ["GB", "IE"],
                "allowed_regions": ["EMEA"],
            },
            "not_eligible",
        ),
    ],
)
def test_verdict_tunisia(kw, expected):
    v, reason = verdict(ex(**kw), "TN", TN)
    assert v == expected
    assert reason


def test_verdict_is_country_aware():
    e = ex(geo_scope="regions", allowed_regions=["Middle East"])
    assert verdict(e, "EG", EG)[0] == "likely"
    assert verdict(e, "TN", TN)[0] == "not_eligible"
    e = ex(geo_scope="timezone_only", timezone_utc_min=2, timezone_utc_max=4)
    assert verdict(e, "EG", EG)[0] == "likely"
    assert verdict(e, "TN", TN)[0] == "not_eligible"


def test_extraction_cleans_codes():
    e = ex(
        allowed_countries=["uk", "US", "USA", "us"],
        allowed_regions=["EMEA", "Mars"],
        languages_required=["EN", "French"],
        evidence_quote="x" * 300,
        timezone_requirement="  ",
    )
    assert e.allowed_countries == ["GB", "US"]
    assert e.allowed_regions == ["EMEA"]
    assert e.languages_required == ["en"]
    assert len(e.evidence_quote) == 200
    assert e.timezone_requirement is None


def test_schema_requires_every_field():
    assert set(JSON_SCHEMA["required"]) == set(Extraction.model_fields)


def job(**kw):
    base = dict(
        id="x:y:1",
        content_hash="h1",
        company_name="Acme",
        title="Engineer",
        location_raw="Berlin",
        remote_flag_raw=None,
        employment_type_raw=None,
        description_text="Join our office.",
    )
    return base | kw


def test_prefilter():
    assert prefilter(job()) == "no remote signal"
    assert prefilter(job(remote_flag_raw="OnSite")) == "workplace flag onsite"
    assert prefilter(job(remote_flag_raw="Hybrid")) == "workplace flag hybrid"
    assert prefilter(job(remote_flag_raw="remote")) is None
    assert prefilter(job(location_raw="Remote, EMEA", remote_flag_raw="hybrid")) is None
    assert prefilter(job(description_text="This is a remote role.")) is None
    assert prefilter(job(title="Engineer (Worldwide)")) is None


def test_excerpt_keeps_eligibility_paragraphs():
    filler = "\n".join(f"We love building great products, paragraph {i}." for i in range(200))
    text = filler + "\nYou must be located in the EU and authorized to work there.\n" + filler
    out = excerpt(text)
    assert len(out) <= 4000
    assert "located in the EU" in out
    assert excerpt("short") == "short"


def test_parse_response_and_usage():
    payload = ex(geo_scope="worldwide").model_dump()
    data = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
        "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 150},
    }
    e, tin, tout = gemini.parse_response(data)
    assert e.geo_scope == "worldwide" and (tin, tout) == (1000, 150)
    with pytest.raises(gemini.ModelError):
        gemini.parse_response({"candidates": []})
    with pytest.raises(gemini.ModelError):
        gemini.parse_response({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})


def test_evidence_must_be_verbatim():
    j = job(location_raw="Remote (EMEA)", description_text="You can work from anywhere in EMEA.")
    e = ex(evidence_quote="You can work from anywhere in EMEA.")
    assert runner.verify_evidence(e, j) and e.confidence == "high"
    e = ex(evidence_quote="Location field: Remote (EMEA)")
    assert runner.verify_evidence(e, j)
    e = ex(evidence_quote="Open to candidates in Africa.")
    assert not runner.verify_evidence(e, j) and e.confidence == "low"


def test_eval_score(tmp_path, monkeypatch):
    from pipeline.classify import evalset

    preds = tmp_path / "p.csv"
    labels = tmp_path / "l.csv"
    preds.write_text(
        "job_id,country,predicted,reason,evidence\n"
        "a,TN,eligible,r,e\nb,TN,eligible,r,e\nc,TN,not_eligible,r,e\nd,TN,unclear,r,e\n",
        encoding="utf-8",
    )
    labels.write_text(
        "job_id,company,title,location,apply_url,label,notes\n"
        "a,,,,,eligible,\nb,,,,,likely,\nc,,,,,not_eligible,\nd,,,,,,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(evalset, "PREDICTIONS", preds)
    monkeypatch.setattr(evalset, "LABELS", labels)
    out = evalset.score("TN")
    assert "Labelled: 3 of 4" in out
    assert "precision(eligible) = 50% over 2" in out
    assert "precision(not_eligible) = 100% over 1" in out
    assert "at least likely: 100%" in out


def test_worldwide_needs_role_level_evidence():
    slogan = ex(geo_scope="worldwide", evidence_quote="We're a natively remote company.")
    assert verdict(slogan, "TN", TN, location="Remote")[0] == "unclear"
    assert verdict(slogan, "TN", TN, location="Remote, Global")[0] == "eligible"
    role = ex(geo_scope="worldwide", evidence_quote="This role can be based anywhere in the world.")
    assert verdict(role, "TN", TN, location="Remote")[0] == "eligible"


def test_reasons_in_french():
    e = ex(geo_scope="timezone_only", timezone_utc_min=-1, timezone_utc_max=3)
    v, reason = verdict(e, "TN", TN, lang="fr")
    assert v == "likely" and reason == "La plage horaire UTC-1 à UTC+3 inclut la Tunisie"
    v, reason = verdict(ex(geo_scope="regions", allowed_regions=["EMEA"]), "EG", EG, lang="fr")
    assert reason == "Ouvert à la région EMEA, qui inclut l'Égypte"
