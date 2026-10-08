# Decisions

Short log, newest last. Format: date, decision, why.

**2026-10-08. Plain asyncio + httpx, no framework.** One semaphore (5) caps concurrency. `pipeline/http.py` is the only place that talks to the network, so retries, timeout and User-Agent live in one spot.

**2026-10-08. Connectors split into `parse(data, board)` and `fetch(client, board)`.** Parsing is pure and tested against saved live responses in `tests/fixtures`. CI never touches the network.

**2026-10-08. HTML stripped with the stdlib `html.parser`.** No BeautifulSoup. Greenhouse `content` is entity-escaped HTML, so it is unescaped once before stripping.

**2026-10-08. Any connector exception means "fetch failed", never "board is empty".** `FetchError`, `KeyError`, `TypeError` and `ValueError` (unexpected shape) all go down the failure path, which expires nothing (rule 3).

**2026-10-08. Two extra columns on `boards`: `source_of_entry` and `last_error`.** Provenance of each seed entry, and why a board is failing, are visible in the database without digging through logs.

**2026-10-08. Re-seeding never resurrects a deactivated board.** `sync_boards` updates names but keeps `active` and the failure counter. To revive a board, set `active = 1` by hand.

**2026-10-08. SmartRecruiters: paginate, no description, cap at 1000 postings.** The list endpoint returns 100 postings per page and no description. Paging is the only way to get the full list (needed so expiry is correct), so this source breaks the "one request per board" rule by necessity. Boards above 10 pages are treated as failures and dropped by `seed validate`: they are large on-site corporates and a poor fit. Descriptions will be fetched per posting in Phase 2, only for candidates.

**2026-10-08. Ashby `isRemote` and `workplaceType` are often null.** `remote_flag_raw` stays null in that case; the location text ("Remote, Bay Area, CA") carries the signal. The classifier reads both.

**2026-10-08. Seed list sources and licenses.**
- `remoteintech/remote-jobs` is ISC licensed (the brief said CC0; the repo LICENSE says ISC). Permissive, we keep the notice in `data/CREDITS.md`. We take company name, website and careers URL.
- `kalil0321/ats-scrapers` is MIT; the root LICENSE covers `ats-companies/` and there is no separate data license. We take `name,slug` pairs.
- Mapping order per company: careers URL that points at a known ATS, then exact normalized name or slug match in ats-scrapers, then a cheap live probe of slug guesses. The match method is stored in `source_of_entry`.
- Top-up from ats-scrapers inventories (`source_of_entry = ats-scrapers`) is kept only when the board has at least one job whose location or remote flag looks remote.
- Name matches can be wrong when two companies share a name. Accepted for Phase 1; the classifier reads the posting itself, so a wrong company mapping cannot produce a wrong eligibility verdict, only an off-topic board.

**2026-10-08. GitHub Actions versions pinned to exact tags.** `astral-sh/setup-uv` no longer publishes floating major tags.

**2026-10-08. Release `data-latest` is created with `--latest=false`.** It holds data, not code, and should not show as the repo's latest release.
