// The one job card renderer, plus the verdict lookups it rests on. Pure string rendering with
// no DOM access, so the browser (search, home, company pages) and the job page Function share it.
import { href, labels, type Lang, LOCALE, tr, type Verdict } from "../i18n";

export type V = Verdict | "not_eligible";
/** Countries that share one outcome. "*" = every country not listed in another group. */
export interface Group {
  v: V;
  r: string;
  c: string[] | "*";
}
/** One record of /data/search-<lang>.json (pipeline/export.py search_record). */
export interface SJob {
  id: string;
  slug: string;
  title: string;
  company: string;
  company_key: string;
  family: string;
  seniority: string;
  engagement: string;
  languages: string[];
  seen_at: string;
  salary: [number | null, number | null, string | null] | null;
  scope: string;
  workplace: string;
  quote: string;
  logo?: string;
  groups: Group[];
}
export interface Ctx {
  lang: Lang;
  /** Selected country code, "" for all countries. */
  code: string;
  /** Localized country names by code. */
  names: Record<string, string>;
  /** Export time (meta.updated): "found n days ago" and "new" are relative to it. */
  updated: string;
}

export const SHOWN: Verdict[] = ["eligible", "likely", "unclear"];

// Where jobs come from. Remote OK's API terms: name them and link back to their job page.
export const SOURCES: Record<string, { name: string; url: string }> = {
  greenhouse: { name: "Greenhouse", url: "https://www.greenhouse.com" },
  lever: { name: "Lever", url: "https://www.lever.co" },
  ashby: { name: "Ashby", url: "https://www.ashbyhq.com" },
  smartrecruiters: { name: "SmartRecruiters", url: "https://www.smartrecruiters.com" },
  workable: { name: "Workable", url: "https://www.workable.com" },
  recruitee: { name: "Recruitee", url: "https://recruitee.com" },
  teamtailor: { name: "Teamtailor", url: "https://www.teamtailor.com" },
  remoteok: { name: "Remote OK", url: "https://remoteok.com" },
};

/** The group that holds `code`, else the "*" group, else null (not eligible). */
export function groupFor<T extends { c: string[] | "*" }>(gs: T[], code: string): T | null {
  let star: T | null = null;
  for (const g of gs) {
    if (g.c === "*") star = g;
    else if (g.c.includes(code)) return g;
  }
  return star;
}

/** Shown verdict for one country, or for "" the shown verdicts anywhere. */
export function verdictsFor(gs: { v: V; c: string[] | "*" }[], code: string): Verdict[] {
  if (!code) return SHOWN.filter((v) => gs.some((g) => g.v === v));
  const g = groupFor(gs, code);
  return g && g.v !== "not_eligible" ? [g.v] : [];
}

export const esc = (s: unknown) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
export const fill = (s: string, vars: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));

export function lamp(v: V): string {
  const inner =
    v === "eligible"
      ? '<circle cx="6" cy="6" r="5.25" fill="currentColor"></circle>'
      : v === "likely"
        ? '<circle cx="6" cy="6" r="4.75" fill="none" stroke="currentColor" stroke-width="1.5"></circle><path d="M6 1.25a4.75 4.75 0 0 1 0 9.5z" fill="currentColor"></path>'
        : v === "unclear"
          ? '<circle cx="6" cy="6" r="4.6" fill="none" stroke="currentColor" stroke-width="1.8"></circle>'
          : "";
  return `<svg class="lamp" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" focusable="false">${inner}</svg>`;
}

/** Company mark: the logo file when the export found one, else initials on a stable hue. */
export function avatar(company: string, key: string, logo: string | undefined, size: number): string {
  if (logo)
    return `<img class="avatar" src="/logos/${esc(logo)}" alt="" width="${size}" height="${size}" loading="lazy" decoding="async">`;
  const initials = company
    .replace(/[^A-Za-z0-9 ]/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
  const hue = [...key].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);
  return `<span class="avatar avatar-initials" aria-hidden="true" style="--size:${size}px;--hue:${hue}">${esc(initials)}</span>`;
}

export function salaryText(s: SJob["salary"], lang: Lang): string {
  if (!s) return "";
  const [lo, hi, cur] = s;
  const fmt = (n: number) =>
    new Intl.NumberFormat(lang === "en" ? "en-US" : LOCALE[lang], {
      style: cur ? "currency" : "decimal",
      currency: cur ?? undefined,
      maximumFractionDigits: 0,
      notation: n >= 10000 ? "compact" : "standard",
    }).format(n);
  if (lo && hi && lo !== hi) return `${fmt(lo)} – ${fmt(hi)}`;
  return fmt((lo ?? hi) as number);
}

export const daysSince = (seenAt: string, updated: string) =>
  Math.max(0, Math.floor((Date.parse(updated) - Date.parse(seenAt)) / 86400000));
/** First seen in the last 36 hours before the export: "new today" for a daily site. */
export const isNew = (seenAt: string, updated: string) => Date.parse(updated) - Date.parse(seenAt) < 36 * 3600 * 1000;

export function foundText(seenAt: string, updated: string, lang: Lang): string {
  const d = daysSince(seenAt, updated);
  return d === 0 ? tr(lang, "found_today") : d === 1 ? tr(lang, "found_1") : tr(lang, "found_ago", { n: d });
}

const ICON = {
  place: "M12 21s-7-6.1-7-11a7 7 0 0 1 14 0c0 4.9-7 11-7 11zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  contract: "M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM9 8h6M9 12h6M9 16h4",
  level: "M4 20V14M10 20V9M16 20V4",
  salary: "M5 6h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2zM12 14.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  when: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
};
export const STAR =
  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8L3.5 9.7l5.9-.9z"></path></svg>';

const label = <K extends "engagement" | "seniority" | "family">(kind: K, v: string, lang: Lang) =>
  (labels[kind] as Record<string, Record<Lang, string>>)[v]?.[lang] ?? "";

/** The icon line under a job title: place, contract, level, salary (and when it was found). */
export function infoLine(j: SJob, lang: Lang, updated: string, found = false): string {
  const items: [keyof typeof ICON, string][] = [
    ["place", esc(j.scope)],
    ["contract", j.engagement !== "unclear" ? esc(label("engagement", j.engagement, lang)) : ""],
    ["level", j.seniority !== "unclear" ? esc(label("seniority", j.seniority, lang)) : ""],
    ["salary", esc(salaryText(j.salary, lang))],
  ];
  if (found)
    items.push(["when", `<time datetime="${esc(j.seen_at.slice(0, 10))}">${esc(foundText(j.seen_at, updated, lang))}</time>`]);
  return `<ul class="card-info">${items
    .filter(([, v]) => v)
    .map(([k, v]) => `<li><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICON[k]}"></path></svg>${v}</li>`)
    .join("")}</ul>`;
}

/** "Brazil, Chile, Peru +4 more". */
export function nameList(codes: string[], ctx: Ctx, max = 3): string {
  const ns = codes.map((c) => ctx.names[c] ?? c);
  return ns.slice(0, max).join(", ") + (ns.length > max ? ` ${tr(ctx.lang, "n_more", { n: ns.length - max })}` : "");
}

/** Countries excluded while "*" is used: the not_eligible groups. */
export const excluded = (gs: Group[]) => gs.filter((x) => x.v === "not_eligible").flatMap((x) => x.c as string[]);

/** "Eligible in Brazil, Chile", or for "*": "Eligible anywhere (else) except Russia". */
export function groupText(gs: Group[], g: Group, ctx: Ctx): string {
  const { lang } = ctx;
  const verdict = labels.verdict[g.v as Verdict][lang];
  if (g.c !== "*") return tr(lang, "verdict_in", { verdict, places: nameList(g.c, ctx) });
  const elsewhere = gs.some((x) => x !== g && x.v !== "not_eligible");
  const out = tr(lang, elsewhere ? "verdict_elsewhere" : "verdict_anywhere", { verdict });
  const no = excluded(gs);
  return no.length ? `${out} ${tr(lang, "except", { places: nameList(no, ctx) })}` : out;
}

/** Reason for a group, with the country filled in; "" when it would name several countries. */
export function reasonFor(g: Group, ctx: Ctx, code = ""): string {
  if (!g.r.includes("{c}")) return g.r;
  const one = code || (g.c !== "*" && g.c.length === 1 ? g.c[0] : "");
  return one ? g.r.replaceAll("{c}", ctx.names[one] ?? one) : "";
}

const PILL_ICON: Record<Verdict, string> = {
  eligible: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="7" fill="currentColor"></circle><path d="M4 7.2l2 2 4-4.4" stroke="#fff" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"></path></svg>',
  likely: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="6" fill="none" stroke="currentColor" stroke-width="1.8"></circle><path d="M7 1a6 6 0 0 1 0 12z" fill="currentColor"></path></svg>',
  unclear: '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.8" fill="none" stroke="currentColor" stroke-width="2"></circle></svg>',
};
export const pill = (v: Verdict, text: string) => `<span class="vp ${v}">${PILL_ICON[v]}${esc(text)}</span>`;

/** The verdict pill: for the visitor's country, or a neutral summary for "All countries". */
export function cardPill(j: SJob, ctx: Ctx, shown: Verdict[] = SHOWN): string {
  const { lang, code } = ctx;
  const mine = code ? groupFor(j.groups, code) : null;
  if (mine && mine.v !== "not_eligible") return pill(mine.v, labels.verdict[mine.v][lang]);
  const g = j.groups.find((x) => x.v !== "not_eligible" && shown.includes(x.v as Verdict));
  if (!g) return "";
  const v = g.v as Verdict;
  const word = labels.open[v][lang];
  const text =
    g.c === "*"
      ? tr(lang, excluded(j.groups).length ? "verdict_elsewhere" : "verdict_anywhere", { verdict: word })
      : tr(lang, "verdict_in", { verdict: word, places: nameList(g.c, ctx, 2) });
  return pill(v, text);
}

/** Tags under the title: new, workplace, level, contract, field. */
function tags(j: SJob, lang: Lang, updated: string): string {
  const t = [
    isNew(j.seen_at, updated) ? `<li class="tag new">${esc(tr(lang, "new_badge"))}</li>` : "",
    `<li class="tag">${esc(tr(lang, `workplace_${j.workplace === "hybrid" ? "hybrid" : "fully_remote"}` as never))}</li>`,
    j.seniority !== "unclear" ? `<li class="tag">${esc(label("seniority", j.seniority, lang))}</li>` : "",
    j.engagement !== "unclear" ? `<li class="tag">${esc(label("engagement", j.engagement, lang))}</li>` : "",
    j.family !== "other" ? `<li class="tag">${esc(label("family", j.family, lang))}</li>` : "",
  ];
  return `<ul class="tags">${t.join("")}</ul>`;
}

export function card(j: SJob, ctx: Ctx, shown: Verdict[] = SHOWN): string {
  const { lang, updated } = ctx;
  const titleId = `t-${j.id.replace(/[^a-zA-Z0-9]/g, "-")}`;
  const salary = salaryText(j.salary, lang);
  const jobHref = esc(href(lang, "job", j.slug) + (ctx.code ? `?c=${ctx.code}` : ""));
  return `<li class="card" data-id="${esc(j.id)}">${avatar(j.company, j.company_key, j.logo, 52)}<div class="card-body">
<h3 class="card-title" id="${titleId}"><a href="${jobHref}">${esc(j.title)}</a></h3>
<p class="card-meta"><a href="${esc(href(lang, "company", j.company_key))}">${esc(j.company)}</a>${salary ? ` · ${esc(salary)}` : ""}</p>
${tags(j, lang, updated)}</div>
<div class="card-side">${cardPill(j, ctx, shown)}<time class="card-date" datetime="${esc(j.seen_at.slice(0, 10))}">${esc(foundText(j.seen_at, updated, lang))}</time>
<button type="button" class="icon-btn save-btn" data-save="${esc(j.id)}" aria-pressed="false" aria-label="${esc(`${tr(lang, "save")}: ${j.title}`)}" aria-describedby="${titleId}">${STAR}</button></div></li>`;
}

/** Search index for one language, fetched once per page. */
export function loadJobs(lang: Lang): Promise<SJob[]> {
  return fetch(`/data/search-${lang}.json`).then((r) => (r.ok ? r.json() : []));
}
