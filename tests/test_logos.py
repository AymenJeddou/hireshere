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
