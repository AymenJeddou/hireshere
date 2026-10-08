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

**2026-10-08. `stats` keyword counts use substring LIKE.** "mena" was dropped because it matched "Blumenau". Phase 2 uses word-boundary regex and Claude, not these counts.

**2026-10-08. Pruned 16 noisy top-up boards (343 to 327).** Rule, in `seed.noise()`, applied only to `ats-scrapers` top-ups: under 5% remote-looking jobs, or 50+ jobs with under 10% unique titles (template spam such as AO Garcia Agency, 3503 jobs and 254 titles). remoteintech boards are exempt because their location text often omits "remote" even when the posting is remote. `seed prune` re-applies the rule from the database without network.

**2026-10-08. Boards removed from the seed list are retired and their jobs expired.** Unlike a fetch failure, removal is deliberate, so expiring is correct.

**2026-10-08. Phase 2 on Gemini instead of Claude.** The Anthropic account has no credit; Google AI Studio has $5. `gemini-2.5-flash-lite` is closed to new users, so the default is `gemini-3.1-flash-lite` ($0.25 in, $1.50 out per million tokens; Batch half). Plain REST through httpx, no SDK. Everything except `gemini.py` is provider-agnostic.

**2026-10-08. No prompt caching.** The system prompt (about 1k tokens) is below the implicit caching minimum, and explicit caching adds storage fees for no gain at this size.

**2026-10-08. Excerpts instead of full descriptions.** Full descriptions would have cost about $3.70 for the backfill in Batch mode. The excerpt keeps the opening (role, seniority) and every paragraph with eligibility keywords. Real usage in the trial: about 1,130 input and 170 output tokens per posting.

**2026-10-08. Extraction schema additions.** `timezone_utc_min` and `timezone_utc_max` (numbers) next to the free-text `timezone_requirement`, so the verdict function never parses text. Regions are a fixed enum.

**2026-10-08. Verdicts are computed, not stored.** Only extractions are stored (one per `content_hash`). The verdict function runs at export time, so tuning it or adding a country costs nothing.

**2026-10-08. Verdict rules, cautious by design.** Explicit exclusion, on-site or hybrid elsewhere, required work authorization elsewhere, a country list without ours, a region list without ours, or a time zone window that misses our offset: not_eligible. Our country listed: eligible. Worldwide: eligible. A region that contains ours, or a time zone window that contains our offset: likely. Remote with no location rule: unclear. A low-confidence extraction is capped at likely, and an evidence quote that is not verbatim in the posting forces low confidence.

**2026-10-08. Daily classification uses the Batch API.** Half price; the workflow waits up to 30 minutes for results, otherwise the next run collects them. The live API reports `BATCH_STATE_*` states while the docs say `JOB_STATE_*`; the code matches on the suffix.

**2026-10-08. Eval set labelling is blind.** `evalset sample` writes labels and predictions to separate files, so whoever labels does not see the model's answer. The sample oversamples eligible and likely predictions, because their precision is what users feel.
