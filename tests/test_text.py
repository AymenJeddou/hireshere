from pipeline.text import html_to_text


def test_strips_tags_and_keeps_structure():
    raw = "<h2>Role</h2><p>Work&nbsp;from <b>anywhere</b>.</p><ul><li>Python</li><li>SQL</li></ul>"
    assert html_to_text(raw) == "Role\n\nWork from anywhere.\n\n- Python\n\n- SQL"


def test_escaped_html():
    assert html_to_text("&lt;p&gt;Remote &amp;amp; EMEA&lt;/p&gt;", escaped=True) == "Remote & EMEA"


def test_drops_scripts_and_handles_empty():
    assert html_to_text("<script>x()</script><p>hi</p>") == "hi"
    assert html_to_text(None) == ""
