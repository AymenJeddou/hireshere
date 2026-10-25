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
