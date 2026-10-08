# Design

HiresHere is a working tool first: a job seeker should know where everything is before noticing any style. The look is a professional product at the craft level of Linear, Stripe and GOV.UK. Distinctiveness comes from one signature, never from decoration.

## Signature

- **Verdict lamps.** Eligible = filled circle, Likely = half-filled circle, Unclear = solid ring (`site/src/components/Lamp.astro`). The shape carries the state; colour only reinforces it, so verdicts survive grayscale and colour blindness.
- **Evidence in the row.** Every job shows the reason and the verbatim quote from the posting in a white inset, never behind a click. When there is no quote, the row says so and shows the location field instead.

## Tokens (`site/src/styles/global.css`)

| Role | Token | Value |
|---|---|---|
| Shell (header, hero) | `--navy-800` | #0E2A47 |
| Shell hover | `--navy-700` | #1B3B5F |
| Text on shell | `--navy-200` | #B9C7DA |
| Active marker, brand dot | `--signal` | #F2B705 |
| Ink / secondary / tertiary | `--ink`, `--ink-2`, `--ink-3` | #14223A, #44546B, #5F6E84 |
| Page ground / surfaces | `--ground`, `--surface` | #F4F6F9, #FFFFFF |
| Hairlines | `--line`, `--line-2` | #DCE2EA, #C9D2DE |
| Links, focus | `--link` | #1D5BC7 |
| Eligible | `--go`, `--go-bg` | #16794A, #E6F4EC |
| Likely | `--maybe`, `--maybe-bg` | #9A5800, #FDF1E1 |
| Unclear | `--unk`, `--unk-bg` | #5B6B82, #EDF0F4 |

All text pairs meet WCAG AA (checked: lowest is 4.75:1).

## Type

Public Sans Variable, self-hosted through `@fontsource-variable/public-sans`. One family for everything. Scale: `--step--1` 13px, `--step-0` 15px, `--step-1` 17px, `--step-2` 20px, `--step-3` fluid 24 to 34px, `--step-4` fluid 32 to 52px. Tabular numerals for counts and dates. Headings balance-wrapped with slight negative tracking.

## Layout and components

- Light theme only: people read on phones in daylight.
- Board: list of rows separated by hairlines (no cards), 320px side rail on desktop (alerts, legend), single column under 980px. Filters are standard controls: checkbox chips for verdicts (check mark + solid border when on, dashed and muted when off), search input, native selects. Under 760px the four selects collapse behind a "Filters (n)" button.
- Buttons: primary navy, secondary white with hairline border, 44px minimum touch target (40px compact for the Apply button).
- Focus: 3px `--link` outline with 2px offset; inputs get a soft focus ring. Selection colour is a pale signal yellow.
- Motion: colour and border transitions only, 0.2s ease-out; the country cards lift 2px on hover. Reduced motion is respected.

## Copy

Plain and direct. English first, French with "vous". Verdicts are always called automated estimates. No AI hype, no invented numbers or testimonials.
