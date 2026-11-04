from types import SimpleNamespace as J

from pipeline.seed import entry_level, noise, norm


def _j(title="Engineer", loc="Paris", flag=None):
    return J(title=title, location_raw=loc, remote_flag_raw=flag)


def test_norm():
    assert norm("Acme, Inc.") == "acmeinc"


def test_entry_level_counts_junior_roles_not_office_only():
    jobs = [_j("Junior Developer"), _j("Software Intern", flag="On-site"), _j("Graduate Analyst"),
            _j("Senior Engineer")]  # fmt: skip
    assert entry_level(jobs) == 2


def test_noise():
    assert noise([]) == "no open jobs"
    office = [_j(f"Role {i}") for i in range(40)]
    assert noise(office) == "only 0/40 remote-looking jobs"
    assert noise(office + [_j("Junior Dev"), _j("Intern")]) is None
    assert noise(office[:38] + [_j(loc="Remote - EMEA")] * 2) is None  # 5% is enough
    spam = [_j("Driver", loc="Remote") for _ in range(60)]
    assert noise(spam).startswith("template spam: 1 titles")


def test_prune_drops_noisy_top_ups_only(tmp_path):
    import csv

    from pipeline import db
    from pipeline.models import Board, FetchResult, Job
    from pipeline.seed import FIELDS, prune

    boards = [
        Board(ats="lever", slug="curated", company_name="C", source_of_entry="remoteintech"),
        Board(ats="lever", slug="topup", company_name="T", source_of_entry="ats-scrapers"),
        Board(ats="lever", slug="junior", company_name="J", source_of_entry="ats-scrapers+entry"),
        Board(ats="lever", slug="good", company_name="G", source_of_entry="ats-scrapers"),
    ]
    path = tmp_path / "boards.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(b.model_dump() for b in boards)
    conn = db.connect(str(tmp_path / "jobs.db"))
    db.sync_boards(conn, boards)
    for b in boards:
        loc = "Remote" if b.slug == "good" else "Paris"
        jobs = [
            Job(source="lever", board_slug=b.slug, source_job_id=str(i), company_name="x",
                title=f"Engineer {i}", location_raw=loc, apply_url="u")
            for i in range(30)
        ]  # fmt: skip
        db.apply_result(conn, FetchResult(board=b, ok=True, jobs=jobs), "2026-11-04")
    conn.close()
    prune(str(tmp_path / "jobs.db"), str(path))
    with open(path, encoding="utf-8") as f:
        assert [r["slug"] for r in csv.DictReader(f)] == ["curated", "good"]
