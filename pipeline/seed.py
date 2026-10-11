"""Build and validate data/boards.csv.

python -m pipeline.seed build --rit PATH --ats PATH [--extra N]
    PATH to clones of remoteintech/remote-jobs and kalil0321/ats-scrapers.
    Writes data/candidates.csv.
python -m pipeline.seed validate
    Fetches every candidate once, keeps boards that answer and have jobs,
    writes data/boards.csv.
"""

import argparse
import asyncio
import csv
import random
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from pipeline import config, db
from pipeline.classify.prompt import ENTRY_LEVEL, OFFICE_FLAGS
from pipeline.http import FetchError, get_json, make_client
from pipeline.models import Board
from pipeline.run import fetch_all, load_boards

ATS = ["greenhouse", "lever", "ashby", "smartrecruiters"]
CANDIDATES = "data/candidates.csv"
FIELDS = ["ats", "slug", "company_name", "website", "source_of_entry"]
CAREERS_URL = {
    "greenhouse": r"greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)",
    "lever": r"jobs\.lever\.co/([\w-]+)",
    "ashby": r"jobs\.ashbyhq\.com/([\w.-]+)",
    "smartrecruiters": r"smartrecruiters\.com/([\w-]+)",
}
PROBE = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{s}", {}),
    "lever": ("https://api.lever.co/v0/postings/{s}", {"mode": "json", "limit": 1}),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{s}", {}),
    "smartrecruiters": ("https://api.smartrecruiters.com/v1/companies/{s}/postings", {"limit": 1}),
}
REMOTE = re.compile(r"remote|anywhere|worldwide|global|emea|africa|mena", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def read_remoteintech(root: Path) -> list[dict]:
    out = []
    for f in sorted((root / "src" / "companies").glob("*.md")):
        front = f.read_text(encoding="utf-8").split("---")[1]
        d = {}
        for line in front.splitlines():
            if m := re.match(r'^(\w+):\s*"?(.*?)"?\s*$', line):
                d[m[1]] = m[2]
        out.append(d)
    return out


def read_ats(root: Path) -> dict[str, dict[str, tuple[str, str]]]:
    """{ats: {normalized name or slug: (slug, name)}}"""
    idx: dict[str, dict] = {}
    for a in ATS:
        with open(root / "ats-companies" / f"{a}.csv", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("slug"):
                    idx.setdefault(a, {}).setdefault(norm(r["name"]), (r["slug"], r["name"]))
                    idx[a].setdefault(norm(r["slug"]), (r["slug"], r["name"]))
    return idx


async def probe(client, sem, ats: str, slug: str) -> bool:
    url, params = PROBE[ats]
    async with sem:
        try:
            data = await get_json(client, url.format(s=slug), params)
        except FetchError:
            return False
    if ats == "smartrecruiters":
        return bool(data.get("totalFound"))
    if ats == "lever":
        return isinstance(data, list) and bool(data)
    return isinstance(data, dict) and "error" not in data


async def build(rit: Path, ats_root: Path, extra: int) -> list[dict]:
    companies, idx = read_remoteintech(rit), read_ats(ats_root)
    rows, unmatched = [], []
    for c in companies:
        name, site = c.get("title", ""), c.get("website", "")
        hit = None
        for a, pat in CAREERS_URL.items():
            if m := re.search(pat, c.get("careers_url", "")):
                hit = (a, m[1], "remoteintech+careers_url")
                break
        if not hit:
            for a in ATS:
                for key in (norm(name), norm(c.get("slug", ""))):
                    if key and key in idx.get(a, {}):
                        hit = (a, idx[a][key][0], "remoteintech+ats-scrapers")
                        break
                if hit:
                    break
        if hit:
            rows.append(dict(zip(FIELDS, [hit[0], hit[1], name, site, hit[2]], strict=True)))
        else:
            unmatched.append(c)

    # Guess slugs for the rest with one cheap request per (ats, guess).
    sem = asyncio.Semaphore(config.MAX_CONCURRENCY)
    async with make_client() as client:

        async def guess(c):
            guesses = dict.fromkeys(g for g in (c.get("slug"), norm(c.get("title", ""))) if g)
            for a in ATS:
                for g in guesses:
                    if await probe(client, sem, a, g):
                        return dict(
                            zip(
                                FIELDS,
                                [a, g, c["title"], c.get("website", ""), "remoteintech+slug-probe"],
                                strict=True,
                            )
                        )
            return None

        found = await asyncio.gather(*(guess(c) for c in unmatched))
    rows += [r for r in found if r]
    print(f"remoteintech: {len(companies)} companies, {len(rows)} mapped", file=sys.stderr)

    # Optional top-up from the ats-scrapers inventories. validate keeps only
    # those with at least one remote-looking job.
    if extra:
        have = {(r["ats"], r["slug"]) for r in rows}
        rnd = random.Random(42)
        for a in ATS:
            pool = sorted({v for v in idx[a].values() if (a, v[0]) not in have})
            for slug, name in rnd.sample(pool, min(extra, len(pool))):
                rows.append(dict(zip(FIELDS, [a, slug, name, "", "ats-scrapers"], strict=True)))
    return rows


def entry_level(jobs: list) -> int:
    """Intern, junior and graduate openings not flagged office-only."""
    return sum(
        bool(ENTRY_LEVEL.search(j.title))
        and re.sub(r"[\s-]", "", (j.remote_flag_raw or "").lower()) not in OFFICE_FLAGS
        for j in jobs
    )


def noise(jobs: list) -> str | None:
    """Why a top-up board is not worth fetching, or None. Jobs need location_raw,
    remote_flag_raw and title. Only applied to ats-scrapers top-ups: remoteintech
    companies are curated, and their location text often omits "remote". A board with
    a few entry-level openings is kept even when few jobs say remote."""
    if not jobs:
        return "no open jobs"
    remote = sum(bool(REMOTE.search(f"{j.location_raw} {j.remote_flag_raw or ''}")) for j in jobs)
    if remote / len(jobs) < 0.05 and entry_level(jobs) < 2:
        return f"only {remote}/{len(jobs)} remote-looking jobs"
    if len(jobs) >= 50 and len({j.title for j in jobs}) / len(jobs) < 0.10:
        return f"template spam: {len({j.title for j in jobs})} titles for {len(jobs)} jobs"
    return None


async def validate(boards: list[Board]) -> list[Board]:
    keep, dropped = [], {}
    async for res in fetch_all(boards):
        b = res.board
        if not res.ok:
            dropped[f"{b.ats}/{b.slug}"] = res.error
        elif not res.jobs:
            dropped[f"{b.ats}/{b.slug}"] = "no open jobs"
        elif b.source_of_entry == "ats-scrapers" and (why := noise(res.jobs)):
            dropped[f"{b.ats}/{b.slug}"] = why
        else:
            keep.append(b)
    for k, v in sorted(dropped.items()):
        print(f"drop {k}: {v}", file=sys.stderr)
    print(f"kept {len(keep)} of {len(boards)}", file=sys.stderr)
    return sorted(keep, key=lambda b: (b.ats, b.slug))


def prune(db_path: str, path: str = config.BOARDS_CSV) -> None:
    """Apply noise() to the current seed list using jobs already in the database."""
    conn = db.connect(db_path)
    keep = []
    for b in load_boards(path):
        jobs = conn.execute(
            "SELECT title, location_raw, remote_flag_raw FROM jobs "
            "WHERE source = ? AND board_slug = ? AND expired_at IS NULL",
            (b.ats, b.slug),
        ).fetchall()
        why = noise([SimpleNamespace(**dict(j)) for j in jobs])
        if b.source_of_entry == "ats-scrapers" and why:
            print(f"prune {b.ats}/{b.slug} ({b.company_name}): {why}", file=sys.stderr)
        else:
            keep.append(b.model_dump())
    write(path, keep)
    print(f"kept {len(keep)} boards", file=sys.stderr)


def write(path: str, rows: list[dict]) -> None:
    seen, unique = set(), []
    for r in rows:
        if (r["ats"], r["slug"].lower()) not in seen:
            seen.add((r["ats"], r["slug"].lower()))
            unique.append(r)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(unique)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="pipeline.seed")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--rit", type=Path, required=True)
    b.add_argument("--ats", type=Path, required=True)
    b.add_argument("--extra", type=int, default=0, help="ats-scrapers boards to add per ATS")
    v = sub.add_parser("validate")
    v.add_argument("--input", default=CANDIDATES)
    v.add_argument("--output", default=config.BOARDS_CSV)
    pr = sub.add_parser("prune", help="drop noisy top-up boards using jobs already in the db")
    pr.add_argument("--db", default=config.DB_PATH)
    args = p.parse_args(argv)

    if args.cmd == "build":
        write(CANDIDATES, asyncio.run(build(args.rit, args.ats, args.extra)))
    elif args.cmd == "prune":
        prune(args.db)
    else:
        kept = asyncio.run(validate(load_boards(args.input)))
        write(args.output, [k.model_dump() for k in kept])


if __name__ == "__main__":
    main()
