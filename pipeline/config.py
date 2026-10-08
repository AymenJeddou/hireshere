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
# utc_offset is the standard offset, used later to match time zone windows.
COUNTRIES = {
    "TN": {"name": "Tunisia", "utc_offset": 1, "regions": ["Africa", "MENA", "EMEA"]},
    "MA": {"name": "Morocco", "utc_offset": 1, "regions": ["Africa", "MENA", "EMEA"]},
    "DZ": {"name": "Algeria", "utc_offset": 1, "regions": ["Africa", "MENA", "EMEA"]},
    "EG": {"name": "Egypt", "utc_offset": 2, "regions": ["Africa", "MENA", "EMEA"]},
}
