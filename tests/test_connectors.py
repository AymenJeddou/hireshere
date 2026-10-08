import asyncio

import httpx
import pytest

from pipeline.connectors import ashby, greenhouse, lever, smartrecruiters
from pipeline.http import FetchError, get_json
from pipeline.models import Board


def board(ats, slug):
    return Board(ats=ats, slug=slug, company_name=slug.title())


def test_greenhouse(fixture):
    jobs = greenhouse.parse(fixture("greenhouse_doximity.json"), board("greenhouse", "doximity"))
    assert len(jobs) == 2
    j = jobs[0]
    assert j.id == "greenhouse:doximity:8132424"
    assert j.title == "Client Success Manager, Pharma"
    assert j.location_raw == "San Francisco, CA or Remote (U.S.)"
    assert j.department == "Sales & Client Success"
    assert j.apply_url.startswith("https://job-boards.greenhouse.io/doximity/")
    assert "<" not in j.description_text and "&lt;" not in j.description_text
    assert "About Doximity" in j.description_text


def test_lever(fixture):
    jobs = lever.parse(fixture("lever_spotify.json"), board("lever", "spotify"))
    assert len(jobs) == 2
    j = jobs[0]
    assert j.id == "lever:spotify:2193db3f-77c5-43b8-b030-8f92c9882bf1"
    assert j.location_raw == "London; Stockholm"
    assert j.remote_flag_raw == "hybrid"
    assert j.employment_type_raw == "Permanent"
    assert "What You'll Do" in j.description_text
    assert "<div>" not in j.description_text


def test_ashby(fixture):
    jobs = ashby.parse(fixture("ashby_supabase.json"), board("ashby", "supabase"))
    assert len(jobs) == 2
    paid = jobs[0]
    assert (paid.salary_min, paid.salary_max, paid.salary_currency) == (200000, 270000, "USD")
    assert paid.remote_flag_raw is None  # Ashby leaves isRemote and workplaceType null here
    assert paid.location_raw == "Remote, Bay Area, CA"
    assert paid.apply_url.startswith("https://jobs.ashbyhq.com/supabase/")
    assert paid.description_text
    assert jobs[1].salary_min is None


def test_ashby_skips_unlisted(fixture):
    data = fixture("ashby_supabase.json")
    data["jobs"][0]["isListed"] = False
    assert len(ashby.parse(data, board("ashby", "supabase"))) == 1


def test_smartrecruiters(fixture):
    data = fixture("smartrecruiters_boschgroup.json")
    jobs = smartrecruiters.parse(data, board("smartrecruiters", "BoschGroup"))
    assert len(jobs) == 2
    assert jobs[0].remote_flag_raw == "remote"
    assert jobs[1].remote_flag_raw == "onsite"
    assert jobs[0].location_raw == "Pleasanton, CA, United States"
    sid = jobs[0].source_job_id
    assert jobs[0].apply_url == f"https://jobs.smartrecruiters.com/BoschGroup/{sid}"


def test_content_hash_tracks_content(fixture):
    data = fixture("lever_spotify.json")
    a = lever.parse(data, board("lever", "spotify"))[0]
    data[0]["descriptionPlain"] += " Changed."
    b = lever.parse(data, board("lever", "spotify"))[0]
    assert a.id == b.id and a.content_hash != b.content_hash


def _get(handler):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await get_json(c, "https://example.test/")

    return asyncio.run(go())


def test_http_errors_raise_fetch_error():
    with pytest.raises(FetchError, match="HTTP 404"):
        _get(lambda r: httpx.Response(404))
    with pytest.raises(FetchError, match="HTTP 503"):
        _get(lambda r: httpx.Response(503))
    with pytest.raises(FetchError, match="bad JSON"):
        _get(lambda r: httpx.Response(200, text="<html>not json"))


def test_http_retries_then_succeeds():
    calls = []

    def handler(r):
        calls.append(1)
        return httpx.Response(500) if len(calls) < 3 else httpx.Response(200, json={"ok": 1})

    assert _get(handler) == {"ok": 1}
    assert len(calls) == 3


def test_http_timeout_is_a_fetch_error():
    def handler(r):
        raise httpx.ReadTimeout("slow", request=r)

    with pytest.raises(FetchError, match="ReadTimeout"):
        _get(handler)
