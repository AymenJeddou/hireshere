"""Prompt, pre-filter and excerpt. Pure functions, no network."""

import re

SYSTEM = """You read one job posting and extract who is allowed to apply for it.
Report only what the posting states or clearly implies. Never guess. When the posting is silent, use "unclear", an empty list or null.

Fields:
- remote_type: fully_remote (no office attendance), hybrid (some office days), onsite, unclear.
- geo_scope: where the candidate may live and work from.
  worldwide = this role is explicitly open to candidates in any country ("Remote - Worldwide", "we hire in any country", "you can be located anywhere in the world").
  regions = limited to named regions (EMEA, Europe, LATAM...).
  countries = limited to named countries ("Remote - US", "US-based", "Remote, Canada", "Germany or Poland").
  timezone_only = only a time zone or working-hours constraint.
  unclear = remote but no location rule stated.
  The location field is authoritative. If it names a city, country or region ("Boston", "Poland", "Remote, EMEA", "Remote, AMER", "Iceland (Remote)"), use that scope even when the text contains company culture slogans such as "Work Anywhere company", "we hire globally", "work from anywhere", "fully distributed team" or "remote-first". Those slogans describe the company, not who may apply for this role. Only a statement about this specific role overrides the location field.
  This applies to remote roles too: "Massachusetts - Boston" with a remote flag means a remote role in the US (geo_scope countries, allowed_countries ["US"]); "Sofia, Bulgaria" means ["BG"]; a list of named countries means exactly those countries. A region mentioned only as a sales territory or customer base ("supporting EMEA customers", "Sales Director, EMEA") or as "open internally" is not a hiring region.
- allowed_countries: ISO 3166-1 alpha-2 codes of countries where the candidate may be located. "Remote (US)" or "US-based" means ["US"]. A city location for an onsite or hybrid role means that city's country. Empty if none named.
- excluded_countries: ISO-2 codes explicitly excluded ("except", "not available in").
- allowed_regions: named regions only, from the allowed list. "Worldwide" if the posting says so.
- timezone_requirement: the constraint as written, or null.
- timezone_utc_min, timezone_utc_max: the range of candidate UTC offsets that satisfies the constraint, in hours. "CET +/- 2 hours" means 1-2=-1 to 1+2=3. "US time zones" means -10 to -5. "Must work EST hours" means -6 to -4. Null if no time zone constraint.
- work_authorization_required: ISO-2 codes where the candidate must already hold the right to work. Only when the posting explicitly mentions work authorization, visas, sponsorship, citizenship, security clearance or E-Verify ("must be authorized to work in the US", "we cannot sponsor visas" for a US role means ["US"]). Never infer it from the location alone. Empty if not stated.
- engagement: employee, contractor (freelance, contract, B2B, via Deel or similar as contractor), either, unclear.
- languages_required: ISO 639-1 codes of languages required (not "nice to have").
- seniority: from the title and requirements.
- role_family: the closest family.
- evidence_quote: the single most decisive sentence for where the candidate may work from, copied verbatim from the posting text, or the location field value itself. Prefer an explicit location or eligibility sentence over hashtags or boilerplate. Do not include input labels such as "Location field:". Max 200 characters.
- confidence: high when the posting states the location rule for this role explicitly, medium when it is implied, low when you are inferring or relying on general company statements."""


def user_message(job: dict) -> str:
    return (
        f"Company: {job['company_name']}\n"
        f"Title: {job['title']}\n"
        f"Location field: {job['location_raw'] or '(empty)'}\n"
        f"Workplace flag: {job['remote_flag_raw'] or '(none)'}\n"
        f"Employment type: {job['employment_type_raw'] or '(none)'}\n\n"
        f"Posting excerpt:\n{excerpt(job['description_text'] or '')}"
    )


REMOTE_SIGNAL = re.compile(
    r"remote|anywhere|worldwide|global|emea|africa|\bmena\b|distributed|home[- ]based"
    r"|work from home|telecommut",
    re.I,
)
DESC_REMOTE = re.compile(r"\bremote\b|work from anywhere|fully distributed", re.I)
# Entry-level postings often name only a city; let the model read them like any other level.
ENTRY_LEVEL = re.compile(
    r"\b(intern(ship)?s?|stage|stagiaire|trainee|graduate|new grad|junior|jr|entry[- ]level"
    r"|werkstudent|working student|apprentice(ship)?|alternan(ce|t)|student)\b",
    re.I,
)
OFFICE_FLAGS = {"onsite", "inoffice"}


def prefilter(job: dict) -> str | None:
    """Reason to skip without calling the model, or None to classify.

    Conservative: skip only when nothing in the structured fields or text hints at remote.
    """
    head = f"{job['location_raw'] or ''} {job['title']}"
    flag = re.sub(r"[\s-]", "", (job["remote_flag_raw"] or "").lower())
    if flag in ("remote", "hybrid") or REMOTE_SIGNAL.search(head):
        return None
    if flag in OFFICE_FLAGS:
        return f"workplace flag {flag}"
    if ENTRY_LEVEL.search(job["title"]) or DESC_REMOTE.search(job["description_text"] or ""):
        return None
    return "no remote signal"


KEYWORDS = re.compile(
    r"remote|anywhere|worldwide|global|located|location|based in|based out|reside|relocat"
    r"|countr|region|emea|europe|africa|mena|middle east|americas|latam|apac|asia"
    r"|time ?zone|utc|gmt|cet|cest|\best\b|\bpst\b|\bet\b|\bpt\b|hours|overlap"
    r"|authori[sz]|visa|sponsor|eligib|citizen|right to work|legally"
    r"|contract|freelanc|employ|full[- ]time|part[- ]time|deel|remote\.com|b2b"
    r"|english|french|arabic|german|spanish|fluen|language|travel|office|hybrid|on-?site",
    re.I,
)


def excerpt(text: str, head: int = 1200, limit: int = 4000) -> str:
    """Opening of the posting plus every paragraph that mentions eligibility keywords."""
    if len(text) <= limit:
        return text
    out, size = [text[:head]], head
    for para in re.split(r"\n+", text[head:]):
        para = para.strip()
        if para and KEYWORDS.search(para) and size + len(para) <= limit:
            out.append(para)
            size += len(para) + 1
    return "\n".join(out)
