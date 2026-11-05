from pipeline.logos import Icons


def test_icons_ranked_by_kind_and_size():
    p = Icons()
    p.feed(
        '<link rel="icon" href="/favicon.ico">'
        '<link rel="icon" sizes="32x32 192x192" href="/i192.png">'
        '<link rel="Apple-Touch-Icon" href="/apple.png">'
        '<link rel="icon" href="/logo.svg">'
        '<link rel="icon" href="data:image/png;base64,AAAA">'
        '<link rel="stylesheet" href="/a.css"><a rel="icon" href="/no.png">'
    )
    assert sorted(p.found, reverse=True) == [
        (1000, "/apple.png"), (192, "/i192.png"), (64, "/logo.svg"), (16, "/favicon.ico")
    ]  # fmt: skip


def test_home_page_patterns_and_ats_hosts():
    import re

    from pipeline.logos import ATS_HOSTS, HOME

    pages = {
        "ashby": '{"name":"Acme","publicWebsite":"https://acme.io","x":1}',
        "lever": '<div class="main-footer-text"><p><a href="https://www.acme.com/">Acme home</a>',
        "teamtailor": '<span>Homepage</span>\n  <a class="x" href="https://acme.se">acme.se</a>',
        "smartrecruiters": '<li class="nav-item"><a href="https://acme.de" class="nav-link">',
    }
    found = {ats: re.search(HOME[ats][1], html)[1] for ats, html in pages.items()}
    assert found == {
        "ashby": "https://acme.io",
        "lever": "https://www.acme.com/",
        "teamtailor": "https://acme.se",
        "smartrecruiters": "https://acme.de",
    }
    assert re.search(ATS_HOSTS, "https://jobs.lever.co/acme", re.I)
    assert not re.search(ATS_HOSTS, "https://acme.io", re.I)
