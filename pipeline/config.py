"""Single source of truth for names, endpoints etiquette and launch countries."""

import json
import os
from pathlib import Path

PRODUCT_NAME = "HiresHere"
DOMAIN = "hireshere.app"
CONTACT_EMAIL = f"contact@{DOMAIN}"  # Cloudflare Email Routing forwards it to the owner

USER_AGENT = f"{PRODUCT_NAME}-bot/0.1 (+https://{DOMAIN}; job eligibility index)"
MAX_CONCURRENCY = 5
RETRIES = 2
TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT", "20"))
MAX_CONSECUTIVE_FAILURES = 5

DB_PATH = os.environ.get("JOBS_DB", "jobs.db")
BOARDS_CSV = "data/boards.csv"

# Featured countries (Telegram channels, getting-paid guide). Configuration, not code.
# utc_offset is the standard offset used to match time zone windows.
# regions are the region names (pipeline/classify/schema.py REGIONS) that include it.
_NORTH_AFRICA = ["Africa", "North Africa", "MENA", "EMEA"]
COUNTRIES = {
    "TN": {
        "name": "Tunisia",
        "name_fr": "Tunisie",
        "name_ar": "تونس",
        "utc_offset": 1,
        "regions": _NORTH_AFRICA,
    },
    "MA": {
        "name": "Morocco",
        "name_fr": "Maroc",
        "name_ar": "المغرب",
        "utc_offset": 1,
        "regions": _NORTH_AFRICA,
    },
    "DZ": {
        "name": "Algeria",
        "name_fr": "Algérie",
        "name_ar": "الجزائر",
        "utc_offset": 1,
        "regions": _NORTH_AFRICA,
    },
    "EG": {
        "name": "Egypt",
        "name_fr": "Égypte",
        "name_ar": "مصر",
        "utc_offset": 2,
        "regions": [*_NORTH_AFRICA, "Middle East"],
    },
}

# Every country a visitor can pick (data/countries.json): names, regions and the UTC offset
# range [min, max] from the IANA tz database. Featured countries keep their own entries above
# (single utc_offset, regions), so their verdicts do not change.
WORLD = {
    code: c | COUNTRIES.get(code, {})
    for code, c in json.loads(
        (Path(__file__).parent.parent / "data/countries.json").read_text("utf-8")
    ).items()
}

# Phase 2 classifier. Prices are USD per million tokens for standard (non-batch) calls,
# from https://ai.google.dev/gemini-api/docs/pricing on 2026-10-08. Batch is half.
CLASSIFIER_MODEL = os.environ.get("CLASSIFIER_MODEL", "gemini-3.1-flash-lite")
PRICE_IN = float(os.environ.get("CLASSIFIER_PRICE_IN", "0.25"))
PRICE_OUT = float(os.environ.get("CLASSIFIER_PRICE_OUT", "1.50"))
MAX_USD_WITHOUT_CONFIRM = 5.0
