# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo, docs, CI | done |
| 1 | Ingestion: seed list, 4 ATS connectors, SQLite diff, CLI, daily workflow | done (2026-10-08) |
| 2 | Classification (Gemini), verdict function, 200-job eval set | done; eval labels are AI drafts awaiting human review |
| 3 | Astro site, country pages, filters, alerts signup | built locally; goes live with Phase 4 |
| 4 | Cloudflare Pages, custom domain, end to end automation, monitoring | not started |
| 5 | Hiring method and payment guidance, "hired here before", FR/AR UI, more countries | not started |

## Open items

- Secondary sources (Himalayas, RemoteOK, Remotive, spec 5b): read terms, record attribution, add connectors.
- SmartRecruiters descriptions: fetch posting detail for classification candidates.
- Domain `hireshere.app` not registered yet.
- "has hired in this country" signal: some postings list countries explicitly (DuckDuckGo, SearchApi list Egypt among 50+ countries), which the Phase 2 verdict function can use directly.
- Human review of the 200 draft eval labels in `data/eval/eval.csv`, then a fresh labelled sample to measure precision without tuning bias.
- Phase 4 wiring: Cloudflare Pages project (build `site/`, output `site/dist`), D1 database from `site/schema.sql` bound as `DB`, daily workflow runs export + deploy, Cloudflare Web Analytics token, CI step that builds the site.
- Sending the email alerts (needs an email provider; free tier to pick in Phase 4).
