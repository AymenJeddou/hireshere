# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo, docs, CI | done |
| 1 | Ingestion: seed list, 4 ATS connectors, SQLite diff, CLI, daily workflow | done (2026-10-08) |
| 2 | Classification with Claude Haiku, verdict function, 200-job eval set | not started |
| 3 | Astro site, country pages, filters, alerts signup | not started |
| 4 | Cloudflare Pages, custom domain, end to end automation, monitoring | not started |
| 5 | Hiring method and payment guidance, "hired here before", FR/AR UI, more countries | not started |

## Open items

- Secondary sources (Himalayas, RemoteOK, Remotive, spec 5b): read terms, record attribution, add connectors.
- SmartRecruiters descriptions: fetch posting detail for classification candidates (Phase 2).
- Domain `hireshere.app` not registered yet.
- Noisy boards from the ats-scrapers top-up (for example AO Garcia Agency with 3500 insurance agent listings, Siloam Hospitals with 700 on-site hospital roles) passed validation on a single remote-looking job. Prune them or rely on the Phase 2 on-site pre-filter.
- "has hired in this country" signal: some postings list countries explicitly (DuckDuckGo, SearchApi list Egypt among 50+ countries), which the Phase 2 verdict function can use directly.
