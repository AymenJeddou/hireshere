# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo, docs, CI | done |
| 1 | Ingestion: seed list, 4 ATS connectors, SQLite diff, CLI, daily workflow | done (2026-10-08) |
| 2 | Classification (Gemini), verdict function, 200-job eval set | built and running daily; blocked on labelling the 200-job eval set |
| 3 | Astro site, country pages, filters, alerts signup | not started |
| 4 | Cloudflare Pages, custom domain, end to end automation, monitoring | not started |
| 5 | Hiring method and payment guidance, "hired here before", FR/AR UI, more countries | not started |

## Open items

- Secondary sources (Himalayas, RemoteOK, Remotive, spec 5b): read terms, record attribution, add connectors.
- SmartRecruiters descriptions: fetch posting detail for classification candidates.
- Domain `hireshere.app` not registered yet.
- "has hired in this country" signal: some postings list countries explicitly (DuckDuckGo, SearchApi list Egypt among 50+ countries), which the Phase 2 verdict function can use directly.
