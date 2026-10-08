"""Turn an Extraction into a per-country verdict. Pure Python, no AI.

A wrong "eligible" is worse than an honest "unclear", so every branch errs cautious.
"""

from typing import Literal

from pipeline.classify.schema import Extraction

Verdict = Literal["eligible", "likely", "unclear", "not_eligible"]


def verdict(e: Extraction, code: str, country: dict) -> tuple[Verdict, str]:
    name = country["name"]
    regions = set(country["regions"])

    if code in e.excluded_countries:
        return "not_eligible", f"{name} is explicitly excluded"

    if e.remote_type in ("onsite", "hybrid"):
        where = "office attendance" if e.remote_type == "onsite" else "hybrid office days"
        if code in e.allowed_countries:
            return "likely", f"Requires {where} in {name}"
        return "not_eligible", f"Requires {where} outside {name}"

    other_auth = [c for c in e.work_authorization_required if c != code]
    if other_auth and code not in e.work_authorization_required:
        return "not_eligible", f"Requires existing work authorization in {', '.join(other_auth)}"

    if code in e.allowed_countries:
        return _cap(e, "eligible", f"{name} is listed as an allowed country")

    if e.geo_scope == "countries" and e.allowed_countries:
        return "not_eligible", f"Limited to {', '.join(e.allowed_countries[:5])}"

    if e.geo_scope == "worldwide" or "Worldwide" in e.allowed_regions:
        if e.timezone_utc_min is not None and not _tz_ok(e, country):
            return "not_eligible", f"Open worldwide but time zone {_tz(e)} excludes {name}"
        return _cap(e, "eligible", "Open to candidates worldwide")

    if e.allowed_regions:
        match = sorted(regions.intersection(e.allowed_regions))
        if match:
            return "likely", f"Open to the {match[0]} region, which includes {name}"
        return "not_eligible", f"Limited to {', '.join(e.allowed_regions)}"

    if e.timezone_utc_min is not None:
        if _tz_ok(e, country):
            return "likely", f"Time zone window {_tz(e)} includes {name}"
        return "not_eligible", f"Time zone window {_tz(e)} excludes {name}"

    if e.remote_type == "fully_remote":
        return "unclear", "Remote, but the posting does not say where candidates may live"
    return "unclear", "The posting does not state where candidates may work from"


def _cap(e: Extraction, v: Verdict, reason: str) -> tuple[Verdict, str]:
    """Low-confidence extractions never produce a firm "eligible"."""
    if v == "eligible" and e.confidence == "low":
        return "likely", reason
    return v, reason


def _tz_ok(e: Extraction, country: dict) -> bool:
    lo = e.timezone_utc_min if e.timezone_utc_min is not None else -12
    hi = e.timezone_utc_max if e.timezone_utc_max is not None else 14
    return lo <= country["utc_offset"] <= hi


def _tz(e: Extraction) -> str:
    def fmt(x):
        return f"UTC{x:+g}" if x is not None else "?"

    return f"{fmt(e.timezone_utc_min)} to {fmt(e.timezone_utc_max)}"
