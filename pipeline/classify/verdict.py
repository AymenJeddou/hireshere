"""Turn an Extraction into a per-country verdict. Pure Python, no AI.

A wrong "eligible" is worse than an honest "unclear", so every branch errs cautious.
Reasons are rendered in English, French or Arabic.
"""

import re
from typing import Literal

from pipeline.classify.schema import Extraction

Verdict = Literal["eligible", "likely", "unclear", "not_eligible"]
LANGS = ("en", "fr", "ar")

# French templates never put an article or preposition before a country name, so they work
# for every country: "{name_fr} figure parmi les pays acceptés".
REASONS = {
    "excluded": ("{name} is explicitly excluded", "Pays exclu explicitement : {name_fr}"),
    "office_here": (
        "Requires {where} in {name}",
        "Demande {where_fr} sur place ({name_fr})",
    ),
    "office_elsewhere": (
        "Requires {where} outside {name}",
        "Demande {where_fr} hors de ce pays ({name_fr})",
    ),
    "auth": (
        "Requires existing work authorization in {places}",
        "Demande une autorisation de travail en {places}",
    ),
    "listed": (
        "{name} is listed as an allowed country",
        "{name_fr} figure parmi les pays acceptés",
    ),
    "countries_only": ("Limited to {places}", "Limité à {places}"),
    "worldwide_tz": (
        "Open worldwide but time zone {tz} excludes {name}",
        "Ouvert partout, mais le fuseau {tz} exclut {name_fr}",
    ),
    "worldwide": ("Open to candidates worldwide", "Ouvert aux candidats du monde entier"),
    "conflict": (
        "The text says anywhere, but the posting is listed for {places}",
        "Le texte dit « partout », mais l'annonce est publiée pour {places}",
    ),
    "company_remote": (
        "Remote company, but the posting does not say this role is open worldwide",
        "Entreprise en télétravail, mais l'annonce ne dit pas que ce poste est ouvert partout",
    ),
    "region": (
        "Open to the {region} region, which includes {name}",
        "Ouvert à la région {region}, qui inclut {name_fr}",
    ),
    "regions_only": ("Limited to {places}", "Limité à {places}"),
    "tz_ok": ("Time zone window {tz} includes {name}", "La plage horaire {tz} inclut {name_fr}"),
    "tz_no": ("Time zone window {tz} excludes {name}", "La plage horaire {tz} exclut {name_fr}"),
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

# Arabic templates (draft, needs a native review). Country names come from config "name_ar".
REASONS_AR = {
    "excluded": "يستثني هذا الإعلان {name_ar} صراحةً",
    "office_here": "يتطلب {where_ar} في {name_ar}",
    "office_elsewhere": "يتطلب {where_ar} خارج {name_ar}",
    "auth": "يتطلب تصريح عمل ساريًا في {places}",
    "listed": "يذكر الإعلان {name_ar} ضمن الدول المقبولة",
    "countries_only": "مقصور على {places}",
    "worldwide_tz": "مفتوح عالميًا، لكن المنطقة الزمنية {tz} تستثني {name_ar}",
    "worldwide": "مفتوح للمرشحين من كل أنحاء العالم",
    "conflict": "يقول النص «من أي مكان»، لكن الإعلان منشور لـ{places}",
    "company_remote": "شركة تعمل عن بُعد، لكن الإعلان لا يذكر أن هذه الوظيفة مفتوحة عالميًا",
    "region": "مفتوح لمنطقة {region} التي تشمل {name_ar}",
    "regions_only": "مقصور على {places}",
    "tz_ok": "النطاق الزمني {tz} يشمل {name_ar}",
    "tz_no": "النطاق الزمني {tz} يستثني {name_ar}",
    "remote_unclear": "عن بُعد، لكن الإعلان لا يذكر أين يمكن للمرشحين الإقامة",
    "unclear": "لا يذكر الإعلان من أين يمكن للمرشحين العمل",
}
WHERE_AR = {"onsite": "الحضور إلى المكتب", "hybrid": "أيام حضور إلى المكتب (عمل هجين)"}

# A "worldwide" extraction needs evidence about this role, not a company slogan.
ROLE_WORLDWIDE_LOCATION = re.compile(r"worldwide|global|anywhere|any country|all countries", re.I)
ROLE_LEVEL_QUOTE = re.compile(
    r"\b(this|the) (role|position|job|opportunity)\b|located anywhere|based anywhere"
    r"|anywhere in the world|any country|every (time ?zone|region)|all time ?zones"
    r"|across the globe|globally remote|hiring worldwide|worldwide|location\s*:",
    re.I,
)
# Region names that can restrict a posting through its title or location field.
LISTED_REGIONS = {
    "americas": "Americas", "amer": "Americas", "latam": "LATAM", "north america": "North America",
    "emea": "EMEA", "europe": "Europe", "apac": "APAC", "asia": "Asia", "africa": "Africa",
    "mena": "MENA", "middle east": "Middle East", "oceania": "Oceania",
}  # fmt: skip
LISTED_REGION_RE = re.compile(r"\b(" + "|".join(LISTED_REGIONS) + r")\b", re.I)
COMPANY_LEVEL_QUOTE = re.compile(
    r"\b(company|organi[sz]ation|workforce|team|we hire|our (staff|people|colleagues))\b", re.I
)


def verdict(
    e: Extraction, code: str, country: dict, lang: str = "en", location: str = "", title: str = ""
) -> tuple[Verdict, str]:
    """Verdict for one country plus a one-line reason in `lang`.

    `location` is the posting's raw location field; it decides whether a "worldwide"
    extraction rests on role-level evidence or on a company slogan.
    """
    v, key, params = decide(e, code, country, location, title)
    return v, reason(key, params, country, lang)


def reason(key: str, params: dict, country: dict, lang: str) -> str:
    """Render a decided reason. Country names come from name, name_fr and name_ar."""
    fields = {k: country.get(k, country["name"]) for k in ("name", "name_fr", "name_ar")}
    fields |= params
    if lang == "fr" and "tz" in fields:
        fields["tz"] = fields["tz"].replace(" to ", " à ")
    if lang == "ar" and "tz" in fields:
        fields["tz"] = fields["tz"].replace(" to ", " إلى ")
    if "where" in params:
        fields["where"], fields["where_fr"] = WHERE[params["where"]]
        fields["where_ar"] = WHERE_AR[params["where"]]
    template = REASONS_AR[key] if lang == "ar" else REASONS[key][LANGS.index(lang)]
    return template.format(**fields)


def decide(e: Extraction, code: str, country: dict, location: str = "", title: str = ""):
    """(verdict, reason key, reason params) for one country. Params never name the country."""
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
        # "Anywhere" in the text, but the title or location lists regions: those regions win.
        if not ROLE_WORLDWIDE_LOCATION.search(location or ""):
            listed = sorted(
                {LISTED_REGIONS[m.lower()] for m in LISTED_REGION_RE.findall(f"{title} {location}")}
            )
            if listed:
                if regions.intersection(listed):
                    match = sorted(regions.intersection(listed))[0]
                    return "likely", "region", {"region": match}
                return "unclear", "conflict", {"places": ", ".join(listed)}
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
    """The window fits when it overlaps the country's offset range (or its one utc_offset)."""
    lo = e.timezone_utc_min if e.timezone_utc_min is not None else -12
    hi = e.timezone_utc_max if e.timezone_utc_max is not None else 14
    off = country.get("utc_offset")
    cmin, cmax = (off, off) if off is not None else country["tz"]
    return cmin <= hi and lo <= cmax


def _tz(e: Extraction) -> str:
    def fmt(x):
        return f"UTC{x:+g}" if x is not None else "?"

    return f"{fmt(e.timezone_utc_min)} to {fmt(e.timezone_utc_max)}"
