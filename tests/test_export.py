from datetime import UTC, datetime

from pipeline.classify.schema import Extraction
from pipeline.export import fresh, job_slug, scope_label, search_record, shard, slugify


def _e(**kw):
    base = {"remote_type": "fully_remote", "geo_scope": "unclear", "engagement": "employee",
            "seniority": "mid", "role_family": "engineering", "evidence_quote": "q",
            "confidence": "high"}  # fmt: skip
    return Extraction(**base | kw)


def test_scope_label():
    assert scope_label(_e(geo_scope="worldwide")) == "Worldwide"
    assert scope_label(_e(allowed_regions=["Worldwide"])) == "Worldwide"
    assert scope_label(_e(allowed_countries=["TN", "MA", "DZ", "EG", "FR", "DE"])) == (
        "TN · MA · DZ · EG +2"
    )
    assert scope_label(_e(timezone_utc_min=-1, timezone_utc_max=3)) == "UTC-1 to UTC+3"
    assert scope_label(_e(timezone_utc_min=1, timezone_utc_max=1)) == "UTC+1"
    assert scope_label(_e(timezone_utc_min=5.5)) == "UTC+5.5"
    assert scope_label(_e()) == ""


def test_slugs_are_stable_and_shardable():
    assert slugify("  Senior C++ / Rust Engineer (EMEA)!  ") == "senior-c-rust-engineer-emea"
    assert len(slugify("x" * 100)) == 60
    assert job_slug("a:b:1", "Ça", "Développeur (Télétravail)").startswith(
        "ca-developpeur-teletravail-"
    )
    assert job_slug("a:b:1", "", "مطور برمجيات").startswith("job-")
    slug = job_slug("greenhouse:acme:123", "Acme", "Backend Engineer")
    assert slug.startswith("acme-backend-engineer-") and slug == job_slug(
        "greenhouse:acme:123", "Acme", "Backend Engineer"
    )
    assert shard(slug) == slug[-6:-4] and len(shard(slug)) == 2


def test_fresh_uses_posting_date_before_first_seen():
    now = datetime(2026, 10, 25, tzinfo=UTC)
    assert fresh({"posted_at": None, "seen_at": "2026-10-20T08:00:00+00:00"}, now)
    assert not fresh(
        {"posted_at": "2026-09-01T00:00:00+00:00", "seen_at": "2026-10-24T00:00:00+00:00"}, now
    )
    assert fresh({"posted_at": "2026-10-11T00:00:00+00:00", "seen_at": "x"}, now)


def test_posting_dates_after_first_seen_are_ignored():
    from pipeline.export import when

    seen = "2026-11-01T08:00:00+00:00"
    assert when({"posted_at": "2026-10-30T00:00:00+00:00", "seen_at": seen}).startswith(
        "2026-10-30"
    )
    assert when({"posted_at": "2026-11-01T20:00:00+00:00", "seen_at": seen}).startswith(
        "2026-11-01T20"
    )
    assert when({"posted_at": "2027-10-30T00:00:00+00:00", "seen_at": seen}) == seen
    assert when({"posted_at": None, "seen_at": seen}) == seen


def test_search_record_trims_quote_and_picks_language():
    j = {"id": "1", "slug": "s", "title": "T", "company": "C", "company_key": "c", "family": "data",
         "seniority": "mid", "engagement": "employee", "languages": [], "seen_at": "2026-10-20",
         "salary": None, "scope": "", "location": "Remote; Tunis; Paris",
         "workplace": "fully_remote",
         "quote": "w" * 300, "posted_at": "2026-10-19T10:00:00+00:00", "logo": "",
         "groups": [{"v": "eligible", "r": {"en": "Open", "fr": "Ouvert"}, "c": "*"}]}  # fmt: skip
    rec = search_record(j, "fr")
    assert rec["scope"] == "Remote, Tunis"
    assert len(rec["quote"]) == 160 and rec["quote"].endswith("…")
    assert rec["posted_at"] == "2026-10-19" and "logo" not in rec
    assert rec["groups"] == [{"v": "eligible", "r": "Ouvert", "c": "*"}]


def test_shards_hold_related_and_similar_jobs(tmp_path, monkeypatch):
    import json

    from pipeline import export

    monkeypatch.setattr(export, "RELATED", 2)

    def j(n, co, fam="data"):
        slug = f"{co}-role-{n:06x}"
        return {"id": str(n), "slug": slug, "title": f"Role {n}", "company": co.title(),
                "company_key": co, "family": fam, "named": ["TN", "XX"],
                "groups": [{"v": "eligible", "r": {}, "c": "*"}]}  # fmt: skip

    jobs = [
        j(1, "acme"),
        j(2, "acme"),
        j(3, "acme"),
        j(4, "beta"),
        j(5, "gamma"),
        j(6, "delta", "ops"),
    ]
    (tmp_path / "stale.json").write_text("{}")
    export.write_shards(jobs, tmp_path)
    assert not (tmp_path / "stale.json").exists()
    rec = json.loads((tmp_path / f"{export.shard(jobs[0]['slug'])}.json").read_text("utf-8"))[
        jobs[0]["slug"]
    ]
    assert rec["company_n"] == 3 and rec["company_named"] == ["TN"]
    assert [m[0] for m in rec["more"]] == [jobs[1]["slug"], jobs[2]["slug"]]
    assert [s[0] for s in rec["similar"]] == [
        jobs[3]["slug"],
        jobs[4]["slug"],
    ]  # same field, other companies


def test_company_slogans_are_not_shown_as_evidence():
    from pipeline.export import _slogan

    assert _slogan("We are a fully remote company with team members in 30 countries")
    assert not _slogan("This role is open to candidates located anywhere in EMEA")
    assert not _slogan("Our team is remote, and this position is open worldwide")
    assert not _slogan("Location: Remote (Africa)")
