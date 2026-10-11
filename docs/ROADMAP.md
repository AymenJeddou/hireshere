# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo, docs, CI | done |
| 1 | Ingestion: seed list, 4 ATS connectors, SQLite diff, CLI, daily workflow | done (2026-10-08) |
| 2 | Classification (Gemini), verdict function, 200-job eval set | done; eval labels are AI drafts awaiting human review |
| 3 | Astro site, job search with filters, alerts signup | done, live at https://hireshere.app (redesigned 2026-10-10) |
| 4 | Cloudflare Pages, custom domain, end to end automation, monitoring | live on hireshere.app with daily deploy; analytics and monitoring pending |
| 5 | Job, company and field pages, saved jobs and applied tracker, profile, employer page, getting-paid guide, AR (RTL) UI, Workable/Recruitee/Teamtailor/Remote OK | done (2026-10-10) |
| 6 | Worldwide: verdicts for every country, visitor country by default, job pages from Pages Functions | done (2026-10-11) |
| 7 | Data quality: employer posting dates, hybrid and entry-level jobs classified, Jobicy, 162 junior-friendly companies, levels on company pages | done (2026-10-11) |

## Open items

- Entry-level coverage: watch how many of the new intern/junior postings come out remote or hybrid after the first classify run; drop added boards whose jobs all turn out office-only (`seed prune` style).

- Telegram: live since 2026-10-10 (@hireshere_bot posts to 4 private channels by id, secret TELEGRAM_CHANNELS). Make the channels public to be findable.
- Native review of the Arabic interface and verdict reasons.
- Getting-paid guide: recheck sources every few months (date on the page).
- SmartRecruiters descriptions: fetch posting detail for classification candidates.
- Human review of the 200 draft eval labels in `data/eval/eval.csv`, then a fresh labelled sample to measure precision without tuning bias.
- Web Analytics: enable in the Pages project (token lacks the analytics permission).
- Monitoring: the daily job fails (GitHub emails the owner) if the export is empty. Watch whether the cron fires; the first scheduled run (2026-10-09 04:17 UTC) never started. If it keeps missing, trigger it from a Cloudflare cron instead.
- Email alerts: live since 2026-10-09 (Resend, hireshere.app verified, test digest delivered). No double opt-in yet: add a confirmation email if spam signups appear.
- Worldwide: country names and region membership come from data/countries.json; a native check of the Arabic and French country names is welcome. The search index is about 500 KB gzipped per language: split it (by country or by page) if it grows much further.
