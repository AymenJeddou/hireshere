from pipeline.telegram import channels, message


def test_channels_parse_codes_chats_and_languages():
    spec = " TN=@hh_tn:fr , eg=@hh_eg:ar,MA=@hh_ma,DZ=,XX=@nope:fr,DZ=@hh_dz:de,"
    assert channels(spec) == {
        "TN": ("@hh_tn", "fr"),
        "EG": ("@hh_eg", "ar"),
        "MA": ("@hh_ma", "en"),
        "DZ": ("@hh_dz", "en"),
    }
    assert channels("") == {}


def test_message_escapes_and_links_the_language_page():
    job = {"title": "C++ <Dev>", "company": "A&B", "scope": "", "verdict": "likely",
           "reason": {"fr": "Probablement ouvert"}, "slug": "a-b-dev-1a2b3c"}  # fmt: skip
    lines = message(job, "fr").split("\n")
    assert lines[0] == "<b>C++ &lt;Dev&gt;</b>"
    assert lines[1] == "A&amp;B"
    assert lines[2] == "🟠 Probable: Probablement ouvert"
    assert lines[3].endswith("/fr/jobs/a-b-dev-1a2b3c")
