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
    assert (
        v == "likely"
        and reason == "Les horaires demandés (UTC-1 à UTC+3) conviennent depuis Tunisie"
    )
    v, reason = verdict(ex(geo_scope="regions", allowed_regions=["EMEA"]), "EG", EG, lang="fr")
    assert reason == "Ouvert dans la région EMEA, qui inclut Égypte"


def test_export_shows_open_verdicts_only_and_never_descriptions(tmp_path):
    from pipeline import db
    from pipeline.export import export
    from pipeline.models import Board, FetchResult, Job

    conn = db.connect(":memory:")
    b = Board(ats="lever", slug="acme", company_name="Acme")
    db.sync_boards(conn, [b])
    jobs = [
        Job(source="lever", board_slug="acme", source_job_id=str(i), company_name="Acme",
            title=f"Job {i}", location_raw=loc, description_text="SECRET full text " + q,
            apply_url=f"https://x/{i}")
        for i, (loc, q) in enumerate([("Remote - Worldwide", "Work from anywhere."),
                                      ("Remote (US)", "US only.")])
    ]  # fmt: skip
    db.apply_result(conn, FetchResult(board=b, ok=True, jobs=jobs), "2026-10-08T00:00:00")
    for j, scope, quote in [(jobs[0], "worldwide", "Work from anywhere."),
                            (jobs[1], "countries", "US only.")]:  # fmt: skip
        e = ex(geo_scope=scope, evidence_quote=quote,
               allowed_countries=["US"] if scope == "countries" else [])  # fmt: skip
        runner.save(conn, dict(conn.execute("SELECT * FROM jobs WHERE id=?", (j.id,)).fetchone()),
                    e, 1, 1)  # fmt: skip
    export(conn, tmp_path, tmp_path / "pub")
    fr = json.loads((tmp_path / "pub/search-fr.json").read_text(encoding="utf-8"))
    fr.sort(key=lambda j: j["title"], reverse=True)
    assert [j["title"] for j in fr] == ["Job 1", "Job 0"]
    assert fr[0]["groups"] == [{"v": "eligible", "r": "L’annonce cite {c} parmi les pays possibles",
                                "c": ["US"]}]  # fmt: skip
    assert fr[1]["groups"] == [{"v": "eligible", "r": "Ouvert aux candidats du monde entier",
                                "c": "*"}]  # fmt: skip
    assert fr[1]["quote"] == "Work from anywhere."
    shards = list((tmp_path / "pub/j").glob("*.json"))
    text = "".join(p.read_text(encoding="utf-8") for p in [*shards, *tmp_path.glob("pub/*.json")])
    assert "SECRET" not in text
    detail = json.loads(shards[0].read_text(encoding="utf-8"))
    rec = next(iter(detail.values()))
    assert rec["company_n"] == 2 and len(rec["more"]) == 1 and rec["url"].startswith("https://x/")
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert meta["countries"]["TN"]["counts"] == {"eligible": 1} and meta["jobs"] == 2
    assert meta["world"]["BR"]["name_fr"] == "Brésil"


def test_groups_encoding_and_lookup():
    from pipeline.export import country_view, for_country, groups

    # Open worldwide except one country: "*" is the common outcome, the exclusion is listed.
    gs = groups(ex(geo_scope="worldwide", excluded_countries=["RU"]), "Remote - Worldwide")
    assert [(g["v"], g["c"]) for g in gs] == [("eligible", "*"), ("not_eligible", ["RU"])]
    assert gs[1]["r"]["en"] == "The posting rules out {c}"
    assert for_country(gs, "BR")["v"] == "eligible" and for_country(gs, "RU")["v"] == "not_eligible"
    # Mostly closed: no "*", exclusions are left out, shown countries are listed.
    gs = groups(ex(geo_scope="countries", allowed_countries=["US", "CA"]))
    assert [(g["v"], g["c"]) for g in gs] == [("eligible", ["CA", "US"])]
    assert for_country(gs, "TN") is None
    # Hybrid with no country named: office days elsewhere for everyone, nothing to show.
    assert groups(ex(remote_type="hybrid")) == []
    # Regions differ per country, so they split into groups; names are filled in per country.
    gs = groups(ex(geo_scope="regions", allowed_regions=["Middle East", "Africa"]))
    view = country_view([{"id": "x", "groups": gs}], "EG")
    assert view[0]["verdict"] == "likely" and "Egypt" in view[0]["reason"]["en"]
    assert "{c}" not in view[0]["reason"]["ar"] and country_view([{"groups": gs}], "FR") == []


def test_timezone_range_overlaps():
    us = config.WORLD["US"]  # UTC-10 to UTC-4
    e = ex(geo_scope="timezone_only", timezone_utc_min=-5, timezone_utc_max=-3)
    assert verdict(e, "US", us)[0] == "likely"
    assert verdict(e, "IN", config.WORLD["IN"])[0] == "not_eligible"
    # A featured country's single utc_offset still decides.
    assert verdict(ex(geo_scope="timezone_only", timezone_utc_min=2, timezone_utc_max=3), "TN",
                   config.WORLD["TN"])[0] == "not_eligible"  # fmt: skip


def test_listed_region_beats_anywhere_text():
    e = ex(
        geo_scope="worldwide",
        evidence_quote="This is a remote role, so you can be located anywhere in the world.",
    )
    loc = "Americas; Sao Paulo; Buenos Aires"
    v, reason = verdict(e, "TN", TN, location=loc, title="Support Engineer (AMERICAS - Remote)")
    assert v == "unclear" and "Americas" in reason
    assert verdict(e, "TN", TN, location="EMEA; Rome", title="Engineer")[0] == "likely"
    # A country in the location field does not override an explicit "anywhere" sentence.
    assert (
        verdict(e, "TN", TN, location="Remote (United States)", title="Engineer")[0] == "eligible"
    )


def test_alert_pick_and_token():
    from pipeline.alerts import pick, render, unsubscribe_token

    def job(id_, verdict, family, scope=""):
        r = {"en": "r", "fr": "r", "ar": "r"}
        return {"id": id_, "verdict": verdict, "family": family, "title": id_.upper(),
                "company": "X", "scope": scope, "url": f"https://x/{id_}", "reason": r}  # fmt: skip

    jobs = [job("a", "eligible", "data"), job("b", "likely", "engineering", "EMEA"),
            job("c", "unclear", "data"), job("d", "eligible", "data")]  # fmt: skip
    seen = {"a": "2026-10-09T08:00:00+00:00", "b": "2026-10-09T09:00:00+00:00",
            "c": "2026-10-09T09:00:00+00:00", "d": "2026-10-07T08:00:00+00:00"}  # fmt: skip
    since = "2026-10-08T00:00:00.000Z"
    assert [j["id"] for j in pick(jobs, seen, since, "")] == [
        "a",
        "b",
    ]  # eligible first, no unclear, d is old
    assert [j["id"] for j in pick(jobs, seen, since, "data")] == ["a"]
    tok = unsubscribe_token("me@x.com", "s3cret")
    assert (
        tok == unsubscribe_token("me@x.com", "s3cret") != unsubscribe_token("you@x.com", "s3cret")
    )
    subject, body, text = render(
        {"lang": "fr", "country": "MA", "family": "data"}, jobs[:1], "https://u"
    )
    assert subject == "Maroc : 1 nouvelle offre en télétravail ouverte" and "https://u" in text
    subject, _, _ = render({"lang": "en", "country": "BR", "family": ""}, jobs[:2], "https://u")
    assert subject == "2 new remote jobs open to Brazil"
    subject, body, _ = render(
        {"lang": "ar", "country": "EG", "family": "data"}, jobs[:2], "https://u"
    )
    assert "مصر" in subject and 'dir="rtl"' in body and "hireshere.app/ar/jobs?c=EG" in body


def test_every_reason_has_arabic():
    from pipeline.classify.verdict import REASONS, REASONS_AR, WHERE, WHERE_AR

    assert REASONS.keys() == REASONS_AR.keys() and WHERE.keys() == WHERE_AR.keys()


def test_arabic_reason_names_country():
    from pipeline.classify.verdict import verdict

    v, reason = verdict(ex(geo_scope="regions", allowed_regions=["EMEA"]), "TN", TN, lang="ar")
    assert v == "likely" and "تونس" in reason and "EMEA" in reason


def test_telegram_channels_and_message():
    from pipeline.telegram import channels, message

    assert channels("TN=@a:fr, eg=@b,XX=@c,MA=") == {"TN": ("@a", "fr"), "EG": ("@b", "en")}
    job = {"title": "Dev <Go>", "company": "X", "scope": "EMEA", "verdict": "likely",
           "reason": {"en": "r", "fr": "r", "ar": "سبب"}, "slug": "dev-x-abc123"}  # fmt: skip
    m = message(job, "ar")
    assert "Dev &lt;Go&gt;" in m and "سبب" in m and m.endswith("hireshere.app/ar/jobs/dev-x-abc123")
