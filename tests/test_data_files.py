"""The committed data files that every verdict and page depends on."""

import csv
import json
import re
from pathlib import Path

from pipeline import config
from pipeline.classify.schema import REGIONS
from pipeline.connectors import CONNECTORS

DATA = Path(__file__).parent.parent / "data"


def test_countries_json_is_complete():
    world = json.loads((DATA / "countries.json").read_text("utf-8"))
    assert len(world) >= 240
    for code, c in world.items():
        assert re.fullmatch(r"[A-Z]{2}", code), code
        assert c["name"] and c["name_fr"] and c["name_ar"], code
        assert set(c["regions"]) <= set(REGIONS), (code, c["regions"])
        lo, hi = c["tz"]
        assert -12 <= lo <= hi <= 14, (code, c["tz"])
    assert set(config.COUNTRIES) <= set(world)


def test_boards_csv_is_clean():
    with open(DATA / "boards.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 400
    keys = [(r["ats"], r["slug"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate board"
    for r in rows:
        assert r["ats"] in CONNECTORS, r
        assert r["slug"].strip() == r["slug"] and r["slug"], r
        assert r["company_name"].strip(), r
        assert not r["website"] or re.match(r"https?://[^\s/]+\.[^\s]+", r["website"]), r
