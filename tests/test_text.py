from pipeline.text import html_to_text, iso_date


def test_strips_tags_and_keeps_structure():
    raw = "<h2>Role</h2><p>Work&nbsp;from <b>anywhere</b>.</p><ul><li>Python</li><li>SQL</li></ul>"
    assert html_to_text(raw) == "Role\n\nWork from anywhere.\n\n- Python\n\n- SQL"


def test_escaped_html():
    assert html_to_text("&lt;p&gt;Remote &amp;amp; EMEA&lt;/p&gt;", escaped=True) == "Remote & EMEA"


def test_drops_scripts_and_handles_empty():
    assert html_to_text("<script>x()</script><p>hi</p>") == "hi"
    assert html_to_text(None) == ""


def test_iso_date_formats():
    assert iso_date("2026-08-17T14:44:07-04:00") == "2026-08-17T18:44:07+00:00"
    assert iso_date("2026-10-07T20:21:47.045Z") == "2026-10-07T20:21:47+00:00"
    assert iso_date("2026-10-05 16:05:18 UTC") == "2026-10-05T16:05:18+00:00"
    assert iso_date("2026-07-28") == "2026-07-28T00:00:00+00:00"
    assert iso_date(1782214185805) == "2026-06-23T11:29:45+00:00"
    assert iso_date(None) is None and iso_date("soon") is None


def test_every_connector_reads_the_posting_date(fixture):
    from pipeline.connectors import CONNECTORS
    from pipeline.models import Board

    files = {
        "greenhouse": "greenhouse_doximity.json", "lever": "lever_spotify.json",
        "ashby": "ashby_supabase.json", "smartrecruiters": "smartrecruiters_boschgroup.json",
        "recruitee": "recruitee_bunq.json", "teamtailor": "teamtailor_teamtailor.json",
        "workable": "workable_1000heads.json", "remoteok": "remoteok.json",
    }  # fmt: skip
    for ats, name in files.items():
        jobs = CONNECTORS[ats].parse(fixture(name), Board(ats=ats, slug="x", company_name="X"))
        assert jobs and all(j.posted_at for j in jobs), ats
