"""Turn an Extraction into a per-country verdict. Pure Python, no AI.

A wrong "eligible" is worse than an honest "unclear", so every branch errs cautious.
Reasons are rendered in English or French from the same templates.
"""

import re
from typing import Literal

from pipeline.classify.schema import Extraction

Verdict = Literal["eligible", "likely", "unclear", "not_eligible"]
LANGS = ("en", "fr")

REASONS = {
    "excluded": ("{name} is explicitly excluded", "Ce poste exclut explicitement {fr_le}"),
    "office_here": (
        "Requires {where} in {name}",
        "Demande {where_fr} {fr_en}",
    ),
    "office_elsewhere": (
        "Requires {where} outside {name}",
        "Demande {where_fr} {fr_hors}",
    ),
    "auth": (
        "Requires existing work authorization in {places}",
        "Demande une autorisation de travail en {places}",
    ),
    "listed": (
        "{name} is listed as an allowed country",
        "L'annonce cite {fr_le} parmi les pays acceptés",
    ),
    "countries_only": ("Limited to {places}", "Limité à {places}"),
    "worldwide_tz": (
        "Open worldwide but time zone {tz} excludes {name}",
        "Ouvert partout, mais le fuseau {tz} exclut {fr_le}",
    ),
    "worldwide": ("Open to candidates worldwide", "Ouvert aux candidats du monde entier"),
    "company_remote": (
        "Remote company, but the posting does not say this role is open worldwide",
        "Entreprise en télétravail, mais l'annonce ne dit pas que ce poste est ouvert partout",
    ),
    "region": (
        "Open to the {region} region, which includes {name}",
        "Ouvert à la région {region}, qui inclut {fr_le}",
    ),
    "regions_only": ("Limited to {places}", "Limité à {places}"),
    "tz_ok": ("Time zone window {tz} includes {name}", "La plage horaire {tz} inclut {fr_le}"),
    "tz_no": ("Time zone window {tz} excludes {name}", "La plage horaire {tz} exclut {fr_le}"),
    "remote_unclear": (
        "Remote, but the posting does not say where candidates may live",
        "Télétravail, mais l'annonce ne précise pas d'où les candidats peuvent travailler",
    ),
    "unclear": (
        "The posting does not state where candidates may work from",
        "L'annonce ne précise pas d'où les candidats peuvent travailler",
    ),
}
WHERE = {
    "onsite": ("office attendance", "une présence au bureau"),
    "hybrid": ("hybrid office days", "des jours au bureau (hybride)"),
}

# A "worldwide" extraction needs evidence about this role, not a company slogan.
ROLE_WORLDWIDE_LOCATION = re.compile(r"worldwide|global|anywhere|any country|all countries", re.I)
ROLE_LEVEL_QUOTE = re.compile(
    r"\b(this|the) (role|position|job|opportunity)\b|located anywhere|based anywhere"
    r"|anywhere in the world|any country|every (time ?zone|region)|all time ?zones"
    r"|across the globe|globally remote|hiring worldwide|worldwide|location\s*:",
    re.I,
)
COMPANY_LEVEL_QUOTE = re.compile(
    r"\b(company|organi[sz]ation|workforce|team|we hire|our (staff|people|colleagues))\b", re.I
)


def verdict(
    e: Extraction, code: str, country: dict, lang: str = "en", location: str = ""
) -> tuple[Verdict, str]:
    """Verdict for one country plus a one-line reason in `lang`.

    `location` is the posting's raw location field; it decides whether a "worldwide"
    extraction rests on role-level evidence or on a company slogan.
    """
    v, key, params = _decide(e, code, country, location)
    i = LANGS.index(lang)
    fields = {"name": country["name"]} | {
        k: country.get(k, country["name"]) for k in ("fr_le", "fr_en", "fr_hors")
    }
    fields |= params
    if lang == "fr" and "tz" in fields:
        fields["tz"] = fields["tz"].replace(" to ", " à ")
    if "where" in params:
        fields["where"], fields["where_fr"] = WHERE[params["where"]]
    return v, REASONS[key][i].format(**fields)


def _decide(e: Extraction, code: str, country: dict, location: str):
    regions = set(country["regions"])

    if code in e.excluded_countries:
        return "not_eligible", "excluded", {}

    if e.remote_type in ("onsite", "hybrid"):
        key = "office_here" if code in e.allowed_countries else "office_elsewhere"
        return ("likely" if key == "office_here" else "not_eligible"), key, {"where": e.remote_type}

    other_auth = [c for c in e.work_authorization_required if c != code]
    if other_auth and code not in e.work_authorization_required:
        return "not_eligible", "auth", {"places": ", ".join(other_auth)}

    if code in e.allowed_countries:
        return _cap(e, "eligible"), "listed", {}

    if e.geo_scope == "countries" and e.allowed_countries:
        return "not_eligible", "countries_only", {"places": ", ".join(e.allowed_countries[:5])}

    if e.geo_scope == "worldwide" or "Worldwide" in e.allowed_regions:
        if e.timezone_utc_min is not None and not _tz_ok(e, country):
            return "not_eligible", "worldwide_tz", {"tz": _tz(e)}
        if not _role_level_worldwide(e, location):
            return "unclear", "company_remote", {}
        return _cap(e, "eligible"), "worldwide", {}

    if e.allowed_regions:
        match = sorted(regions.intersection(e.allowed_regions))
        if match:
            return "likely", "region", {"region": match[0]}
        return "not_eligible", "regions_only", {"places": ", ".join(e.allowed_regions)}

    if e.timezone_utc_min is not None:
        if _tz_ok(e, country):
            return "likely", "tz_ok", {"tz": _tz(e)}
        return "not_eligible", "tz_no", {"tz": _tz(e)}

    if e.remote_type == "fully_remote":
        return "unclear", "remote_unclear", {}
    return "unclear", "unclear", {}


def _role_level_worldwide(e: Extraction, location: str) -> bool:
    if ROLE_WORLDWIDE_LOCATION.search(location or ""):
        return True
    q = e.evidence_quote
    if ROLE_LEVEL_QUOTE.search(q):
        return True
    # Neither the location field nor a role-level sentence: a company slogan is not enough.
    return not COMPANY_LEVEL_QUOTE.search(q) and not location


def _cap(e: Extraction, v: Verdict) -> Verdict:
    """Low-confidence extractions never produce a firm "eligible"."""
    return "likely" if v == "eligible" and e.confidence == "low" else v


def _tz_ok(e: Extraction, country: dict) -> bool:
    lo = e.timezone_utc_min if e.timezone_utc_min is not None else -12
    hi = e.timezone_utc_max if e.timezone_utc_max is not None else 14
    return lo <= country["utc_offset"] <= hi


def _tz(e: Extraction) -> str:
    def fmt(x):
        return f"UTC{x:+g}" if x is not None else "?"

    return f"{fmt(e.timezone_utc_min)} to {fmt(e.timezone_utc_max)}"
