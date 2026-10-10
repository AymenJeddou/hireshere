# Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repo, docs, CI | done |
| 1 | Ingestion: seed list, 4 ATS connectors, SQLite diff, CLI, daily workflow | done (2026-10-08) |
| 2 | Classification (Gemini), verdict function, 200-job eval set | done; eval labels are AI drafts awaiting human review |
| 3 | Astro site, country pages, filters, alerts signup | done, live at https://hireshere.app |
| 4 | Cloudflare Pages, custom domain, end to end automation, monitoring | live on hireshere.app with daily deploy; analytics and monitoring pending |
| 5 | Job, company and field pages, saved jobs and applied tracker, profile, employer page, getting-paid guide, AR (RTL) UI, Workable/Recruitee/Teamtailor/Remote OK | done (2026-10-10) except Telegram channels |

## Open items

- Telegram channel per country: needs a bot token from @BotFather and the four channels (owner).
- Native review of the Arabic interface and verdict reasons.
- Getting-paid guide: recheck sources every few months (date on the page).
- SmartRecruiters descriptions: fetch posting detail for classification candidates.
- Human review of the 200 draft eval labels in `data/eval/eval.csv`, then a fresh labelled sample to measure precision without tuning bias.
- Web Analytics: enable in the Pages project (token lacks the analytics permission).
- Monitoring: the daily job fails (GitHub emails the owner) if the export is empty. Watch whether the cron fires; the first scheduled run (2026-10-09 04:17 UTC) never started. If it keeps missing, trigger it from a Cloudflare cron instead.
- Email alerts: live since 2026-10-09 (Resend, hireshere.app verified, test digest delivered). No double opt-in yet: add a confirmation email if spam signups appear.
