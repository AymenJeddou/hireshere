"""Write compact per-country JSON for the site. Never exports descriptions (spec 5c)."""

import json
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pipeline import config
from pipeline.classify.schema import Extraction
from pipeline.classify.verdict import COMPANY_LEVEL_QUOTE, ROLE_LEVEL_QUOTE, verdict

SHOWN = ("eligible", "likely", "unclear")  # not_eligible is never shown
RANK = {v: i for i, v in enumerate(SHOWN)}


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


def rows(conn: sqlite3.Connection):
    q = """SELECT j.id, j.title, j.company_name, j.location_raw, j.apply_url, j.first_seen_at,
                  j.source, e.data
           FROM jobs j JOIN extractions e ON e.content_hash = j.content_hash
           WHERE j.expired_at IS NULL"""
    for r in conn.execute(q):
        data = json.loads(r[7])
        verified = data.pop("evidence_verified", False)
        yield r, Extraction(**data), verified


def build(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {c: [] for c in config.COUNTRIES}
    for (jid, title, company, location, url, seen, source, _), e, verified in rows(conn):
        base = None
        for code, country in config.COUNTRIES.items():
            v, reason_en = verdict(e, code, country, "en", location or "", title)
            if v not in SHOWN:
                continue
            _, reason_fr = verdict(e, code, country, "fr", location or "", title)
            if base is None:
                base = {
                    "id": jid,
                    "title": title,
                    "company": company,
                    "location": location or "",
                    "url": url,
                    "seen": seen[:10],
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
                }
            out[code].append(base | {"verdict": v, "reason": {"en": reason_en, "fr": reason_fr}})
    for jobs in out.values():
        jobs.sort(key=lambda j: j["seen"], reverse=True)  # newest first...
        jobs.sort(key=lambda j: RANK[j["verdict"]])  # ...within each verdict (stable sort)
    return out


def export(conn: sqlite3.Connection, out_dir: str | Path) -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = build(conn)
    for code, jobs in data.items():
        (out_dir / f"{code.lower()}.json").write_text(
            json.dumps(jobs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
    boards = conn.execute(
        "SELECT ats, COUNT(*) FROM boards WHERE active = 1 GROUP BY ats ORDER BY 2 DESC"
    ).fetchall()
    meta = {
        "updated": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "product": config.PRODUCT_NAME,
        "domain": config.DOMAIN,
        "contact": config.CONTACT_EMAIL,
        "open_jobs": conn.execute("SELECT COUNT(*) FROM jobs WHERE expired_at IS NULL").fetchone()[
            0
        ],
        "boards": {a: n for a, n in boards},
        "countries": {
            code: {
                "name": c["name"],
                "name_fr": c["name_fr"],
                "fr_le": c["fr_le"],
                "fr_en": c["fr_en"],
                "counts": dict(Counter(j["verdict"] for j in data[code])),
            }
            for code, c in config.COUNTRIES.items()
        },
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    lines = [f"## {config.PRODUCT_NAME} export", ""]
    for code, m in meta["countries"].items():
        lines.append(f"- {code}: {m['counts']}")
    return "\n".join(lines)
