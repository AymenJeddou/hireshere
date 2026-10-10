# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Astro static site in `/site`, reading JSON exported by the Python pipeline (`python -m pipeline.run export`). No client framework; search, cards and filtering are vanilla JS over a per-language search index. Job pages are rendered by a Pages Function from detail shards (the free plan allows 20,000 files per deployment). Hosted on Cloudflare Pages (Phase 4). Signups and error reports go to Cloudflare Pages Functions backed by a free D1 database (confirmed by the owner 2026-10-08; goes live with the Phase 4 deploy).

## Users

Job seekers anywhere in the world looking for remote work with foreign companies. The site started with Tunisia, Morocco, Algeria and Egypt, which stay featured (Telegram channels, getting-paid guide). Mostly engineers, designers, data, product, marketing, sales and support professionals. Many browse on phones, some on slow or metered connections. Their recurring frustration: "remote" jobs that turn out to be US-only or EU-only after they have already spent time applying.

## Product Purpose

Show each visitor only the remote jobs their country can actually apply to, with the evidence for every verdict, refreshed daily straight from company hiring systems. Success: a visitor finds roles they are genuinely eligible for and trusts the verdict enough to apply.

## Positioning

Country-first eligibility, not another generic remote board. Every job carries a verdict for the visitor's country (eligible, likely, unclear) and the verbatim sentence from the posting that justifies it. A wrong "eligible" is worse than an honest "unclear".

## Operating Context

- Data refreshes daily; jobs that disappear from the company feed expire the same day.
- Verdicts are automated estimates from an AI reading of the posting; the site must always say so and invite visitors to confirm with the employer.
- The site never republishes full job descriptions: title, company, structured fields, a short evidence quote and a link to the original posting only.
- Every data source is credited on a Sources page.

## Capabilities and Constraints

- Every country (243, `data/countries.json`) gets a verdict on every remote, hybrid or unclear job. Office-only jobs are not listed. Featured countries: TN, MA, DZ, EG (`config.COUNTRIES`).
- Filters: role family, seniority, language, engagement, verdict.
- Email alert signup per country and role family; "Report an error" per job. Both post to Cloudflare Pages Functions (Phase 4).
- English first, French second. French uses "vous".
- Free tiers only. No trackers beyond privacy-friendly analytics. No payments.
- Product name and domain come from config: HiresHere, hireshere.app (registered at Name.com, DNS on Cloudflare).

## Brand Commitments

Name: HiresHere. Plain, direct, honest voice. No hype about AI.

Visual commitment (owner, 2026-10-08): professional above all, with best-in-class UX and UI. Sit alongside Linear, Stripe and GOV.UK in craft and clarity; no themed or costume look. Distinctiveness comes from the product's own signature (verdict lamps with shape-coded states and the evidence quote shown in the row), not from decoration.

## Evidence on Hand

Real job data from 327 company boards (Greenhouse, Lever, Ashby, SmartRecruiters). A 200-job evaluation set with draft labels (AI-drafted, pending human review). No testimonials, user counts or press exist; do not fabricate any.

## Product Principles

1. Honesty over volume: show fewer jobs with clear evidence rather than more jobs with doubtful verdicts.
2. The evidence is the product: the quote from the posting is always visible, never hidden behind a click.
3. Respect the visitor's bandwidth: fast pages, no heavy scripts.
4. The employer has the last word: always link to the original posting and say verdicts are estimates.

## Accessibility & Inclusion

Mobile first, works on slow connections, readable at small sizes, WCAG AA contrast. French and English from launch; Arabic planned (RTL must remain possible).
