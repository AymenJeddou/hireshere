# HiresHere: notes for Claude Code

Read `docs/SPEC.md` (the brief), `docs/ROADMAP.md` (status) and `docs/DECISIONS.md` (why things are the way they are) before changing anything.

## Rules from the owner

- Minimal code: stdlib plus httpx and pydantic. No frameworks. Pick the simpler option and log it in `docs/DECISIONS.md`.
- Free tiers only. Ask before anything that costs money.
- No secrets in git. Env vars, `.env.example`.
- Tests for anything that parses or decides. No network in tests.
- Small commits. No em-dashes in any text written for the owner.
- Product name and domain only come from `pipeline/config.py` (`PRODUCT_NAME`, `DOMAIN`).
- Countries are configuration (`config.WORLD` from `data/countries.json`, featured `config.COUNTRIES`), never code branches.
- Never scrape sites that forbid it. Never republish full descriptions on the site.
- Do not start a phase until the owner says so.

## Commands

```
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run python -m pipeline.run fetch [--limit 20]
uv run python -m pipeline.run stats
uv run python -m pipeline.run classify [--limit N] [--batch] [--yes]   # needs GEMINI_API_KEY
uv run python -m pipeline.run classify-collect                         # store finished batches
uv run python -m pipeline.classify.evalset sample|score [--country TN]
uv run python -m pipeline.run export            # site/src/data/{meta,companies}.json, site/public/data/
cd site && npm install && npx astro build       # static site in site/dist
uv run python -m pipeline.seed build --rit <remote-jobs clone> --ats <ats-scrapers clone> [--extra N]
uv run python -m pipeline.seed validate
```

## Layout

- `pipeline/connectors/<ats>.py`: `parse(data, board)` (pure, tested) and `fetch(client, board)`.
- `pipeline/db.py`: schema and the five diff rules. `apply_result` is the heart of it.
- `pipeline/run.py`: CLI and the concurrent fetcher. Loads `.env` for local runs.
- `pipeline/classify/`: `schema.py` (what the model extracts), `prompt.py` (prompt, pre-filter,
  excerpt), `verdict.py` (pure per-country verdict), `gemini.py` (the only provider-specific
  file), `runner.py` (triage, cost estimate, storage), `evalset.py` (hand-checked eval).
- Extractions are stored once per `content_hash` in `extractions`. Verdicts are computed from
  them at export time, never stored, so changing `verdict.py` or `COUNTRIES` needs no model calls.
- `site/`: Astro site. Design system in `DESIGN.md`, product truth in `PRODUCT.md`.
  `site/functions/api/` are Cloudflare Pages Functions (signups, reports) using D1 (`site/schema.sql`).
- `data/boards.csv`: validated seed list, committed. `data/candidates.csv` is a build artifact, ignored.
- `jobs.db` lives on the `data-latest` GitHub Release as `jobs.db.gz`, never in git.
  Local copy: `gh release download data-latest -p jobs.db.gz && gunzip jobs.db.gz`. Download before
  working locally and upload (`gh release upload data-latest jobs.db.gz --clobber`) after, or CI and
  local diverge.
- Live site: https://hireshere.app (Cloudflare Pages project `hireshere`, D1 `hireshere`; www and
  hireshere.pages.dev 301 to it via `site/functions/_middleware.js`).
  Deploy by hand: `cd site && npx wrangler pages deploy --branch main` with CLOUDFLARE_* from `.env`.

## Git

Commit as Aymen Jeddou (repo-local config). No AI co-author trailers.
