"""Single source of truth for names, endpoints etiquette and launch countries."""

import os

PRODUCT_NAME = "HiresHere"
DOMAIN = "hireshere.app"

USER_AGENT = f"{PRODUCT_NAME}-bot/0.1 (+https://{DOMAIN}; job eligibility index)"
MAX_CONCURRENCY = 5
RETRIES = 2
TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT", "20"))
MAX_CONSECUTIVE_FAILURES = 5

DB_PATH = os.environ.get("JOBS_DB", "jobs.db")
BOARDS_CSV = "data/boards.csv"

# Countries are configuration, not code. Add a row to support a new country.
# utc_offset is the standard offset used to match time zone windows.
# regions are the region names (pipeline/classify/schema.py REGIONS) that include it.
_NORTH_AFRICA = ["Africa", "North Africa", "MENA", "EMEA"]
COUNTRIES = {
    "TN": {"name": "Tunisia", "utc_offset": 1, "regions": _NORTH_AFRICA},
    "MA": {"name": "Morocco", "utc_offset": 1, "regions": _NORTH_AFRICA},
    "DZ": {"name": "Algeria", "utc_offset": 1, "regions": _NORTH_AFRICA},
    "EG": {"name": "Egypt", "utc_offset": 2, "regions": [*_NORTH_AFRICA, "Middle East"]},
}

# Phase 2 classifier. Prices are USD per million tokens for standard (non-batch) calls,
# from https://ai.google.dev/gemini-api/docs/pricing on 2026-10-08. Batch is half.
CLASSIFIER_MODEL = os.environ.get("CLASSIFIER_MODEL", "gemini-3.1-flash-lite")
PRICE_IN = float(os.environ.get("CLASSIFIER_PRICE_IN", "0.25"))
PRICE_OUT = float(os.environ.get("CLASSIFIER_PRICE_OUT", "1.50"))
MAX_USD_WITHOUT_CONFIRM = 5.0
