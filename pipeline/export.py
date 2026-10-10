"""Write the site's JSON: search indexes, job detail shards, meta. Never exports descriptions.

Every job carries a verdict for every country in config.WORLD, stored compactly as groups:
[{"v": verdict, "r": {lang: reason}, "c": [codes] or "*"}]. Reasons hold a "{c}" placeholder
where the country name goes. "*" means every country not listed in another group; it is used
when the most common outcome is a shown verdict, and only then are exclusions listed.
"""

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from pipeline import config
from pipeline.classify.schema import Extraction
from pipeline.classify.verdict import COMPANY_LEVEL_QUOTE, LANGS, ROLE_LEVEL_QUOTE, decide, reason

SHOWN = ("eligible", "likely", "unclear")  # not_eligible is never shown
RANK = {v: i for i, v in enumerate((*SHOWN, "not_eligible"))}
WORKPLACES = ("fully_remote", "hybrid", "unclear")  # office-only jobs stay out
PLACEHOLDER = {"name": "{c}", "name_fr": "{c}", "name_ar": "{c}"}
LOGOS = Path("site/public/logos")
QUOTE_MAX = 160
RELATED = 10  # similar and same-company jobs kept per shard record


def scope_label(e: Extraction) -> str:
    """Short, language-neutral summary of who may apply."""
    if e.geo_scope == "worldwide" or "Worldwide" in e.allowed_regions:
        return "Worldwide"
    if e.allowed_regions:
        return " · ".join(e.allowed_regions[:3])
    if e.allowed_countries:
        more = len(e.allowed_countries) - 4
        return " · ".join(e.allowed_countries[:4]) + (f" +{more}" if more > 0 else "")
    if e.timezone_utc_min is not None:
        lo, hi = e.timezone_utc_min, e.timezone_utc_max
        return f"UTC{lo:+g}" + (f" to UTC{hi:+g}" if hi is not None and hi != lo else "")
    return ""


def _slogan(q: str) -> bool:
    return bool(COMPANY_LEVEL_QUOTE.search(q)) and not ROLE_LEVEL_QUOTE.search(q)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")


def job_slug(jid: str, company: str, title: str) -> str:
    return f"{slugify(f'{company} {title}')}-{hashlib.sha1(jid.encode()).hexdigest()[:6]}"


def shard(slug: str) -> str:
    """Detail shard of a job: the first two hex chars of the slug's 6-char hash."""
    return slug[-6:-4]


def websites() -> dict[tuple[str, str], str]:
    with open(config.BOARDS_CSV, encoding="utf-8") as f:
        return {(r["ats"], r["slug"]): r["website"] for r in csv.DictReader(f) if r["website"]}


def rows(conn: sqlite3.Connection):
    q = """SELECT j.id, j.title, j.company_name, j.location_raw, j.apply_url, j.first_seen_at,
                  j.source, e.data, j.board_slug, j.salary_min, j.salary_max, j.salary_currency,
                  j.department, j.employment_type_raw, j.remote_flag_raw
           FROM jobs j JOIN extractions e ON e.content_hash = j.content_hash
           WHERE j.expired_at IS NULL"""
    for r in conn.execute(q):
        data = json.loads(r[7])
        verified = data.pop("evidence_verified", False)
        yield r, Extraction(**data), verified


def groups(e: Extraction, location: str = "", title: str = "") -> list[dict]:
    """Verdicts for every WORLD country, grouped by outcome. [] when no country may see it."""
    by: dict[tuple, list[str]] = {}
    for code, country in config.WORLD.items():
        v, key, params = decide(e, code, country, location, title)
        by.setdefault((v, key, tuple(sorted(params.items()))), []).append(code)
    if not any(k[0] in SHOWN for k in by):
        return []
    common = max(by, key=lambda k: len(by[k]))
    star = common[0] in SHOWN
    out = [
        {
            "v": v,
            "r": {lang: reason(key, dict(params), PLACEHOLDER, lang) for lang in LANGS},
            "c": "*" if star and k == common else codes,
        }
        for k, codes in by.items()
        for v, key, params in [k]
        if star or v in SHOWN
    ]
    return sorted(out, key=lambda g: RANK[g["v"]])


def for_country(gs: list[dict], code: str) -> dict | None:
    """The group that holds `code`, else the "*" group, else None (not eligible)."""
    star = None
    for g in gs:
        if g["c"] == "*":
            star = g
        elif code in g["c"]:
            return g
    return star


def country_view(jobs: list[dict], code: str) -> list[dict]:
    """Jobs shown in one country, each with "verdict" and "reason" (country name filled in)."""
    c = config.WORLD[code]
    names = {"en": c["name"], "fr": c["name_fr"], "ar": c["name_ar"]}
    out = []
    for j in jobs:
        g = for_country(j["groups"], code)
        if g and g["v"] in SHOWN:
            r = {lang: g["r"][lang].replace("{c}", names[lang]) for lang in LANGS}
            out.append(j | {"verdict": g["v"], "reason": r})
    return out


def build(conn: sqlite3.Connection) -> list[dict]:
    """Every remote, hybrid or unclear job open to at least one country, newest first."""
    sites = websites()
    logos = {p.stem: p.name for p in LOGOS.glob("*")} if LOGOS.is_dir() else {}
    out = []
    for r, e, verified in rows(conn):
        jid, title, company, location, url, seen, source, _, board = r[:9]
        smin, smax, scur, dept, emp, _flag = r[9:]
        if e.remote_type not in WORKPLACES:
            continue
        gs = groups(e, location or "", title)
        if not gs:
            continue
        key = slugify(company)
        out.append(
            {
                "id": jid,
                "title": title,
                "company": company,
                "location": location or "",
                "url": url,
                "seen_at": seen,
                "slug": job_slug(jid, company, title),
                "company_key": key,
                "logo": logos.get(key, ""),
                "website": sites.get((source, board), ""),
                "salary": [smin, smax, scur] if smin or smax else None,
                "tz": [e.timezone_utc_min, e.timezone_utc_max, e.timezone_requirement]
                if e.timezone_utc_min is not None or e.timezone_requirement
                else None,
                "department": dept or "",
                "contract": emp or "",
                "workplace": e.remote_type,
                "named": e.allowed_countries,
                "source": source,
                "scope": scope_label(e),
                "family": e.role_family,
                "seniority": e.seniority,
                "engagement": e.engagement,
                "languages": e.languages_required,
                "confidence": e.confidence,
                # Only quote what really appears in the posting, and never a company
                # slogan: then the location field is the evidence.
                "quote": e.evidence_quote if verified and not _slogan(e.evidence_quote) else "",
                "groups": gs,
            }
        )
    out.sort(key=lambda j: j["seen_at"], reverse=True)
    return out


def _trim(q: str) -> str:
    return q if len(q) <= QUOTE_MAX else q[: QUOTE_MAX - 1].rstrip() + "…"


def search_record(j: dict, lang: str) -> dict:
    """Compact card record for one language's search index."""
    place = j["scope"] or ", ".join(p.strip() for p in j["location"].split(";")[:2])
    rec = {k: j[k] for k in ("id", "slug", "title", "company", "company_key", "family")}
    rec |= {k: j[k] for k in ("seniority", "engagement", "languages", "seen_at", "salary")}
    rec |= {"scope": place, "workplace": j["workplace"], "quote": _trim(j["quote"])}
    if j["logo"]:
        rec["logo"] = j["logo"]
    rec["groups"] = [{"v": g["v"], "r": g["r"][lang], "c": g["c"]} for g in j["groups"]]
    return rec


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), "utf-8")


def _related(j: dict) -> list:
    """[slug, title, company, [[verdict, codes or "*"], ...]] for side lists on job pages."""
    return [j["slug"], j["title"], j["company"], [[g["v"], g["c"]] for g in j["groups"]]]


def write_shards(jobs: list[dict], out: Path) -> None:
    by_company: dict[str, list[dict]] = defaultdict(list)
    by_family: dict[str, list[dict]] = defaultdict(list)
    for j in jobs:  # newest first
        by_company[j["company_key"]].append(j)
        by_family[j["family"]].append(j)
    shards: dict[str, dict] = defaultdict(dict)
    for j in jobs:
        co = by_company[j["company_key"]]
        similar = []
        for s in by_family[j["family"]]:
            if s["company_key"] != j["company_key"]:
                similar.append(_related(s))
                if len(similar) == RELATED:
                    break
        shards[shard(j["slug"])][j["slug"]] = j | {
            "company_n": len(co),
            "company_named": sorted({c for x in co for c in x["named"] if c in config.WORLD}),
            "more": [_related(x) for x in co if x["id"] != j["id"]][:RELATED],
            "similar": similar,
        }
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    for name, recs in shards.items():
        _dump(out / f"{name}.json", recs)


def export(
    conn: sqlite3.Connection, out_dir: str | Path, public_dir: str | Path = "site/public/data"
) -> str:
    out_dir, public_dir = Path(out_dir), Path(public_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    jobs = build(conn)
    for lang in LANGS:
        _dump(public_dir / f"search-{lang}.json", [search_record(j, lang) for j in jobs])
    write_shards(jobs, public_dir / "j")
    boards = conn.execute(
        "SELECT ats, COUNT(*) FROM boards WHERE active = 1 GROUP BY ats ORDER BY 2 DESC"
    ).fetchall()
    open_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE expired_at IS NULL").fetchone()[0]
    meta = {
        "updated": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "product": config.PRODUCT_NAME,
        "domain": config.DOMAIN,
        "contact": config.CONTACT_EMAIL,
        "open_jobs": open_jobs,
        "jobs": len(jobs),
        "companies": len({j["company_key"] for j in jobs}),
        "boards": {a: n for a, n in boards},
        # Featured countries: Telegram channels and the getting-paid guide.
        "countries": {
            code: {
                "name": c["name"],
                "name_fr": c["name_fr"],
                "name_ar": c["name_ar"],
                "counts": dict(Counter(j["verdict"] for j in country_view(jobs, code))),
            }
            for code, c in config.COUNTRIES.items()
        },
        "world": {
            code: {k: c[k] for k in ("name", "name_fr", "name_ar", "regions")}
            for code, c in config.WORLD.items()
        },
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    lines = [f"## {config.PRODUCT_NAME} export", "", f"- {len(jobs)} jobs shown somewhere"]
    for code, m in meta["countries"].items():
        lines.append(f"- {code}: {m['counts']}")
    return "\n".join(lines)
