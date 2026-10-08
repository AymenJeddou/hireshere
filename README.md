# HiresHere

Remote jobs you can actually get, country by country. Launch countries: Tunisia, Morocco, Algeria, Egypt.

Every day the pipeline pulls public job feeds straight from company hiring systems (Greenhouse, Lever, Ashby, SmartRecruiters), keeps a SQLite database in sync, and expires jobs that disappear. From Phase 2, Claude reads each posting to work out who can apply, and the site shows each visitor only the jobs open to their country, with the evidence.

See `docs/SPEC.md` for the full brief and `docs/ROADMAP.md` for status.

## Quick start

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run pytest -q
uv run python -m pipeline.run fetch --limit 20   # quick test against 20 boards
uv run python -m pipeline.run fetch              # full run
uv run python -m pipeline.run stats
```

Copy `.env.example` to `.env` to override defaults.

## Data

- `data/boards.csv`: the validated list of company job boards, with where each entry came from.
- `jobs.db`: never committed. The daily workflow stores it as `jobs.db.gz` on the `data-latest` release.
- Credits for third-party data: `data/CREDITS.md`.
