# Design

HiresHere is a job board first: a job seeker should know where everything is before noticing any style. The model is the classic French job search (APEC and similar): a search band, a filter sidebar with counts, job cards on a light grey ground. Chosen by the owner on 2026-10-10 over editorial, dark-map and decorative directions.

## Signature

- **Verdict lamps.** Eligible = filled circle, Likely = half-filled circle, Unclear = solid ring (`site/src/components/Lamp.astro`). The shape carries the state; colour only reinforces it, so verdicts survive grayscale and colour blindness. Any element with `.v-eligible`, `.v-likely` or `.v-unclear` colours the lamps inside it.
- **Verdict line on every card.** "Eligible in Tunisia" (or "in all 4 countries" when no country is picked), the reason, then the verbatim quote from the posting. The line follows the selected countries and verdicts (`site/src/verdictline.ts`, shared by the build and the browser).

## Palette: Ocean (`site/src/styles/global.css`)

| Role | Token | Value |
|---|---|---|
| Brand: search band, primary buttons, footer, logo tile | `--brand` | #0B3A53 |
| Brand hover, links, focus | `--brand-2` | #155F80 |
| Text on brand / lines on brand | `--band-sub`, `--band-line` | #B9D3E0, #3A6C85 |
| Accent: Search button, logo dot, New tag, quote bar | `--accent`, `--accent-ink`, `--accent-soft` | #FF7A59, #2A0D05, #FFF1EC |
| Ink / secondary / tertiary | `--ink`, `--ink-2`, `--ink-3` | #1B2330, #4A5362, #677080 |
| Page ground / surfaces | `--ground`, `--surface` | #F4F5F7, #FFFFFF |
| Hairlines | `--line`, `--line-2` | #E2E5EA, #CDD2DA |
| Eligible | `--go` | #157A43 |
| Likely | `--maybe` | #A85D00 |
| Unclear | `--unk` | #6B7280 |

The verdict colours are never used for anything else, and the accent is never used for a verdict. Older names (`--navy-800`, `--signal`, `--link`) are aliases of the palette.

## Type

Roboto 400/500/700, self-hosted through `@fontsource/roboto`. Arabic falls back to the system Arabic font. Scale: `--step--1` 13px, `--step-0` 15px, `--step-1` 17px, `--step-2` 20px, `--step-3` 22 to 28px, `--step-4` 26 to 36px. Tabular numerals for counts and dates.

## Layout and components (`site/src/styles/components.css`)

- One search page (`/jobs`, `/fr/jobs`, `/ar/jobs`). Country is a filter (search band select + checkboxes), never a tab. Filters: country, can I apply, field, level, contract, language, found, salary, each with live counts that add up to the result total. State lives in the URL (`?c=TN,EG&f=engineering&v=eligible`). 20 jobs per page.
- Old addresses `/tn`, `/tn/engineering` (and FR/AR) 301 to the search with those filters (`site/public/_redirects`).
- Job card (`JobCard.astro`) is the only job component: search, home, company pages. Icon line (`JobInfo.astro`): place, contract, level, salary.
- Job page: panels (header with Apply and Save, who can apply table, what the posting says, details, report an error) and a side column (company, more at the company, similar jobs, getting-paid guide).
- Buttons: primary brand, accent only for Search, secondary white with hairline border. 44px minimum touch target.
- No stock photos on the search, home or companies pages.

## Copy

Plain and direct. English first, French with "vous", Arabic (draft, needs a native review). "Found 2 days ago", never "posted": we only know when we first saw a job. Quotes are exact excerpts. Verdicts are always called automated estimates. No invented numbers.
