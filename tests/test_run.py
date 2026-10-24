from pipeline.run import load_dotenv


def test_load_dotenv_quotes_export_and_real_env_wins(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        '# comment\nA="quoted value"\nexport B=plain\nC=\'single\'\nD=kept\nE="\n', "utf-8"
    )
    for k in "ABCDE":
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("D", "from-shell")
    load_dotenv(str(env))
    import os

    assert (os.environ["A"], os.environ["B"], os.environ["C"]) == (
        "quoted value",
        "plain",
        "single",
    )
    assert os.environ["D"] == "from-shell"
    assert os.environ["E"] == '"'
    load_dotenv(str(tmp_path / "missing"))
