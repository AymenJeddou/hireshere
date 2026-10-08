# HiresHere specification

This is the founding brief, kept up to date. Corrections found while building are marked **Update**.

## 1. Product in one paragraph

Product name: **HiresHere**. Planned domain: `hireshere.app` (not registered yet, so the name and the domain live in one config constant each, `pipeline/config.py`, and are never hardcoded elsewhere).

A website that shows people in underserved countries the remote jobs they can ACTUALLY get. Most remote job boards list roles as "remote" that are really US-only or EU-only. We pull job postings directly from company hiring systems every day, use Claude to read each posting and extract who is allowed to apply (countries, regions, time zones, contract type, language), then show each visitor only the jobs open to their country, with the evidence for that verdict.

Launch countries: **Tunisia (TN), Morocco (MA), Algeria (DZ), Egypt (EG)**. The engine must be country-agnostic so other countries are added by configuration, not code.

## 2. Why this can win

- Generic remote boards are crowded. Our edge is being country-first for a region nobody serves well.
- The verdict must be trustworthy: always show the evidence sentence from the posting and a confidence level. A wrong "eligible" is worse than an honest "unclear".
- Freshness is automatic: a job that disappears from the company feed is expired the same day.
- Later differentiators (not Phase 1): how the company would hire you (contractor vs employer of record), whether it has hired in your country before, how you would get paid, French-language roles.

## 3. Working preferences

- Minimal code. Prefer the standard library and a few well-known packages over frameworks.
- Pragmatic choices over architectural purity. If two options work, pick the simpler one and note it in the docs.
- Everything must run on free tiers. Ask before using anything that costs money.
- Never commit secrets. Use environment variables and a `.env.example`.
- Small commits with clear messages. Tests for anything that parses or decides.
- If something is ambiguous or risky, ask before doing it.
- Do not use em-dashes in any text written for the owner.
- Use Context7 for current library docs, Playwright for checking the site in Phase 3, and the frontend-design skill for the UI in Phase 3, when available.

## 4. Architecture

```
GitHub Actions (daily cron)
  1. fetch   -> pull public job feeds for every board in the seed list
  2. diff    -> insert new jobs, update last_seen, expire missing ones
  3. classify (Phase 2) -> Claude extracts eligibility fields for NEW jobs only
  4. export  (Phase 3) -> write compact JSON per country
  5. deploy  (Phase 4) -> static site rebuilt and published

Storage: one SQLite file (jobs.db)
  - persisted between runs as a gzip asset on a rolling GitHub Release
    tagged `data-latest` (gh release download / gh release upload --clobber)
  - never committed to git

Site (Phase 3): static site (Astro), reads the exported JSON,
  hosted on Cloudflare Pages (free, works with a private repo)
```

Stack: Python 3.12, `uv`, `httpx`, `pydantic`, `sqlite3` (stdlib), `pytest`, `ruff`. Anthropic Python SDK (Phase 2 only). Astro (Phase 3 only). GitHub Actions for scheduling and CI.

Repo layout:

```
/pipeline
  /connectors      one file per source (greenhouse.py, lever.py, ashby.py, ...)
  models.py        pydantic models (Job, Board, FetchResult)
  db.py            SQLite schema + upsert/expire functions
  seed.py          build and validate the board seed list
  run.py           CLI: fetch | stats | export
  /classify        (Phase 2)
/data
  boards.csv       seed list: ats, slug, company_name, website, source_of_entry
/site              (Phase 3)
/tests
/docs
  SPEC.md          this brief, kept up to date
  ROADMAP.md       phases and status
  DECISIONS.md     short log of choices and why
CLAUDE.md          project memory for future sessions
.github/workflows  ci.yml, daily.yml
```

## 5. Data sources

### 5a. Company hiring systems (primary, public JSON, no auth)

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/{slug}?mode=json`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true`
- SmartRecruiters: `https://api.smartrecruiters.com/v1/companies/{id}/postings`

Shapes verified live on 2026-10-08: Greenhouse wraps in `jobs` + `meta` and its `content` is entity-escaped HTML. Lever returns a bare array. Ashby wraps in `jobs` + `apiVersion`. SmartRecruiters wraps in `offset`, `limit`, `totalFound`, `content`, is paginated (100 per page) and has **no description** in the list endpoint.

### 5b. Remote job boards with free feeds (secondary, add after 5a works)

- Himalayas (free API, paginated, link back required)
- RemoteOK (free API, first array element is a legal notice not a job, credit and link back required)
- Remotive (free feed, delayed 24h, max about 4 calls per day, link back required)

Read each one's current API terms before using it and record the attribution rule in `docs/DECISIONS.md`. Store `source` and the original URL for every job so attribution is always possible.

### 5c. Never do this

- No scraping of LinkedIn, Indeed, Glassdoor or any site that blocks bots or forbids it in its terms. No JobSpy-style scrapers.
- No republishing of full job descriptions on the site. Descriptions are stored privately for classification. The site shows only title, company, structured fields, a short evidence quote, and a link to the original posting.

### 5d. GitHub repos to study or reuse

- `remoteintech/remote-jobs`: list of remote-friendly companies with region notes. Main source of company names for the seed list. **Update:** the repo LICENSE is ISC (plus MIT and SIL for site components), not CC0. ISC is permissive; we keep the notice in `data/CREDITS.md`.
- `kalil0321/ats-scrapers` (MIT, the root LICENSE covers the `ats-companies/` CSVs; no separate data license): company inventories per hiring system. Used to map companies to `ats` + `slug`. We write our own connectors.
- `Feashliaa/job-board-aggregator`: architecture reference only. Its datasets require permission for commercial use, so its data is not imported.

## 6. Data model (SQLite)

`boards`: ats, slug, company_name, website, source_of_entry, active, last_ok_at, consecutive_failures, last_error

`jobs`: id (`{source}:{board_slug}:{source_job_id}`), source, board_slug, company_name, title, location_raw, remote_flag_raw, department, employment_type_raw, salary_min, salary_max, salary_currency, description_text, apply_url, content_hash (title + location_raw + description_text), first_seen_at, last_seen_at, expired_at, classify_status (`pending | done | skipped | error`)

`runs`: id, started_at, finished_at, boards_ok, boards_failed, jobs_new, jobs_updated, jobs_expired

Rules (tested in `tests/test_db.py`):

1. A job present in a successful fetch: upsert, set `last_seen_at`, clear `expired_at`.
2. A job absent from a SUCCESSFUL fetch of its board: set `expired_at`.
3. If a board fetch FAILS (timeout, 4xx, 5xx, bad JSON): expire nothing for that board, increment `consecutive_failures`. Never mass-expire because of a network error.
4. If `content_hash` changes, set `classify_status` back to `pending`.
5. A board with 5 consecutive failures is set `active = 0` and listed in the run report.

Fetching etiquette: clear User-Agent, max 5 concurrent requests, 2 retries with backoff, 20s timeout, one request per board per run (SmartRecruiters needs one per 100 postings, see DECISIONS.md).

## 7. Classification (Phase 2)

For each `pending` job, Claude returns structured JSON:

```
remote_type: fully_remote | hybrid | onsite | unclear
geo_scope: worldwide | regions | countries | timezone_only | unclear
allowed_countries: [ISO-2]        excluded_countries: [ISO-2]
allowed_regions: [EMEA, Europe, Africa, MENA, Americas, APAC, ...]
timezone_requirement: text or null (example "UTC-1 to UTC+3")
work_authorization_required: [ISO-2]   (example ["US"])
engagement: employee | contractor | either | unclear
languages_required: [ISO 639-1]
seniority: intern | junior | mid | senior | lead | unclear
role_family: engineering | data | design | product | marketing | sales | support | ops | other
evidence_quote: short verbatim sentence from the posting (max 200 chars)
confidence: high | medium | low
```

A pure Python function (no AI) turns those fields into a per-country verdict `eligible | likely | unclear | not_eligible` plus a one-line reason. Examples: worldwide with no exclusions = eligible. EMEA/Africa/MENA region = likely. Time zone window that includes UTC+1 = likely. Explicit country list without ours, or "must be authorized to work in the US" = not_eligible.

Implementation notes:

- Use the current cheapest Claude Haiku model. Look up the exact model ID in the official Anthropic docs at build time and read it from env var `CLASSIFIER_MODEL`.
- Structured outputs / tool use for strict JSON. Cache the system prompt. Batch API for the first backfill. Classify each job once, keyed by `content_hash`.
- Cheap pre-filter: skip jobs that are clearly on-site.
- 200-job hand-checked evaluation set; report precision for "eligible" and "not_eligible" before anything goes public.
- Reference price (October 2026): Haiku 5.5 at $0.10 per million input tokens and $0.50 per million output tokens. Print an estimated cost before every batch and ask for confirmation above $5.
- SmartRecruiters jobs have no description from the list endpoint; fetch the posting detail for candidates before classifying.

## 8. Site (Phase 3)

- Static Astro site. Home page: pick your country. Country pages: `/tn`, `/ma`, `/dz`, `/eg`.
- Filters: role family, seniority, language, engagement, verdict.
- Job card: title, company, verdict badge, reason, evidence quote, date first seen, "Apply on company site" link, "Report an error" link.
- "How it works" page and a "Sources" page that credits every data source.
- Disclaimer: verdicts are automated estimates, always confirm with the employer.
- English first, French second. Mobile first. Fast. No trackers beyond privacy-friendly analytics.
- Email alert signup (per country + role family).

## 9. Later phases

- Phase 4: Cloudflare Pages deploy, custom domain, daily automation end to end, monitoring of the daily run.
- Phase 5: hiring method and payment guidance per country, "has hired here before" signal, French and Arabic UI, more countries, saved searches.
- Monetization is not a goal yet. No payments.
