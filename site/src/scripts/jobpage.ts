// Job page body, rendered per request by the Pages Function (functions/_job.js) from a detail
// shard (public/data/j/<xx>.json). Same markup and classes as the rest of the site.
import { formatDate, href, labels, languageName, type Lang, tr } from "../i18n";
import {
  avatar,
  type Ctx,
  esc,
  excluded,
  groupFor,
  groupText,
  infoLine,
  isNew,
  lamp,
  nameList,
  reasonFor,
  salaryText,
  type SJob,
  SOURCES,
  STAR,
  type V,
} from "./cards";

type Related = [string, string, string, [V, string[] | "*"][]];
export interface Detail extends Omit<SJob, "groups"> {
  location: string;
  url: string;
  website: string;
  tz: [number | null, number | null, string | null] | null;
  department: string;
  contract: string;
  source: string;
  groups: { v: V; r: Record<Lang, string>; c: string[] | "*" }[];
  company_n: number;
  company_named: string[];
  more: Related[];
  similar: Related[];
}
interface Meta {
  updated: string;
  countries: Record<string, unknown>;
  world: Record<string, { name: string; name_fr: string; name_ar: string }>;
}

const nameOf = (c: { name: string; name_fr: string; name_ar: string }, lang: Lang) =>
  ({ en: c.name, fr: c.name_fr, ar: c.name_ar })[lang];

/** Page title and description for the shell's placeholders. */
export function jobMeta(job: Detail, lang: Lang, code: string, meta: Meta) {
  const names = Object.fromEntries(Object.entries(meta.world).map(([k, c]) => [k, nameOf(c, lang)]));
  const ctx: Ctx = { lang, code, names, updated: meta.updated };
  const gs = job.groups.map((g) => ({ ...g, r: g.r[lang] }));
  const open = gs.filter((g) => g.v !== "not_eligible").map((g) => groupText(gs, g, ctx));
  return { title: `${job.title}, ${job.company}`, description: `${job.company}: ${job.title}. ${open.join(" · ")}` };
}

export function jobPage(job: Detail, lang: Lang, code: string, meta: Meta): string {
  const names = Object.fromEntries(Object.entries(meta.world).map(([k, c]) => [k, nameOf(c, lang)]));
  const ctx: Ctx = { lang, code, names, updated: meta.updated };
  const gs = job.groups.map((g) => ({ ...g, r: g.r[lang] }));
  const place = job.scope || job.location.split(/;\s*/).slice(0, 2).join(", ");
  const card = { ...job, scope: place, groups: gs };
  const vname = (v: V) => (v === "not_eligible" ? tr(lang, "not_open") : labels.verdict[v][lang]);
  const lab = (kind: "seniority" | "engagement" | "family", v: string) =>
    (labels[kind] as Record<string, Record<Lang, string>>)[v]?.[lang] ?? "";

  // Who can apply: the visitor's country first, then every group.
  const mine = code ? groupFor(gs, code) : null;
  const first = code
    ? `<tr class="who-me"><th scope="row">${esc(names[code])}</th>${
        mine && mine.v !== "not_eligible"
          ? `<td class="v-${mine.v} wv">${lamp(mine.v)} ${esc(vname(mine.v))}</td><td>${esc(reasonFor(mine, ctx, code))}</td>`
          : `<td colspan="2" class="muted">${esc(tr(lang, "not_shown", { country: names[code] }))}</td>`
      }</tr>`
    : "";
  const where = (g: (typeof gs)[number]) => {
    if (g.c === "*") {
      const elsewhere = gs.some((x) => x !== g && x.v !== "not_eligible");
      const out = tr(lang, elsewhere ? "where_elsewhere" : "where_anywhere");
      const no = excluded(gs);
      return esc(no.length ? `${out} ${tr(lang, "except", { places: nameList(no, ctx, 8) })}` : out);
    }
    if (g.c.length <= 8) return esc(nameList(g.c, ctx, 8));
    const all = g.c.map((c) => names[c] ?? c).join(", ");
    return `<details><summary>${esc(nameList(g.c, ctx, 5))}</summary>${esc(all)}</details>`;
  };
  const rows = gs
    .filter((g) => !(g.c !== "*" && g.c.length === 1 && g.c[0] === code)) // already the first row
    .map(
      (g) =>
        `<tr><th scope="row">${where(g)}</th><td class="v-${g.v} wv">${lamp(g.v)} ${esc(vname(g.v))}</td><td>${esc(reasonFor(g, ctx))}</td></tr>`,
    )
    .join("");

  const tzText = job.tz
    ? job.tz[2] ||
      [job.tz[0], job.tz[1]]
        .filter((x) => x !== null)
        .map((x) => `UTC${x! >= 0 ? "+" : ""}${x}`)
        .join(" – ")
    : "";
  const details: [string, string][] = (
    [
      [tr(lang, "d_location"), job.location],
      [tr(lang, "d_workplace"), tr(lang, `workplace_${job.workplace}` as never)],
      [
        tr(lang, "d_contract"),
        [job.engagement !== "unclear" ? lab("engagement", job.engagement) : "", job.contract.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ")]
          .filter(Boolean)
          .join(" · "),
      ],
      [tr(lang, "d_level"), job.seniority !== "unclear" ? lab("seniority", job.seniority) : ""],
      [tr(lang, "d_field"), lab("family", job.family)],
      [tr(lang, "d_languages"), job.languages.map((l) => languageName(l, lang)).join(", ")],
      [tr(lang, "d_salary"), salaryText(job.salary, lang)],
      [tr(lang, "d_timezone"), tzText],
      [tr(lang, "d_department"), job.department],
      [tr(lang, "d_source"), SOURCES[job.source]?.name ?? job.source],
      [tr(lang, "d_first_seen"), formatDate(job.seen_at, lang, true)],
    ] as [string, string][]
  ).filter(([, v]) => v);

  // Side lists: jobs open (or likely open) where the visitor lives, else anywhere.
  const verdictOf = (gsMini: Related[3]): V | null => {
    if (!code) return gsMini[0]?.[0] ?? null;
    const g = groupFor(gsMini.map(([v, c]) => ({ v, c })), code);
    return g ? g.v : null;
  };
  const related = (items: Related[], withCompany: boolean) =>
    items
      .map((r) => [r, verdictOf(r[3])] as const)
      .filter(([, v]) => v && v !== "not_eligible")
      .slice(0, 5)
      .map(
        ([[slug, title, company], v]) =>
          `<li><a href="${esc(href(lang, "job", slug))}">${esc(title)}</a><span class="v-${v}">${withCompany ? `${esc(company)} · ` : ""}${lamp(v!)} ${esc(vname(v!))}</span></li>`,
      )
      .join("");
  const more = related(job.more, false);
  const similar = related(job.similar, true);
  const website = job.website ? new URL(job.website).hostname.replace(/^www\./, "") : "";
  const named = job.company_named.filter((c) => names[c]).map((c) => names[c]);
  const reportOptions = Object.entries(names)
    .sort((a, b) => a[1].localeCompare(b[1], lang))
    .map(([c, n]) => `<option value="${c}"${c === code ? " selected" : ""}>${esc(n)}</option>`)
    .join("");
  const mini = gs.map((g) => [g.v, g.c]);
  const searchHref = href(lang, "search") + (code ? `?c=${code}` : "");

  return `<div class="wrap job-page">
  <nav class="crumbs" aria-label="Breadcrumb">
    <a href="${esc(href(lang, "search"))}">${esc(tr(lang, "nav_find"))}</a>
    <span aria-hidden="true"> <span class="flip">›</span> </span>
    ${code ? `<a href="${esc(searchHref)}">${esc(names[code])}</a><span aria-hidden="true"> <span class="flip">›</span> </span>` : ""}
    <span aria-current="page">${esc(job.title)}</span>
  </nav>
  <div class="jp-grid">
    <div class="jp-main">
      <header class="panel jp-head">
        ${avatar(job.company, job.company_key, job.logo, 64)}
        <div>
          <p class="jp-company"><a href="${esc(href(lang, "company", job.company_key))}">${esc(job.company)}</a></p>
          <h1>${esc(job.title)}${isNew(job.seen_at, meta.updated) ? ` <span class="new-badge">${esc(tr(lang, "new_badge"))}</span>` : ""}</h1>
          ${infoLine(card, lang, meta.updated, true)}
          <div class="jp-actions">
            <a class="btn btn-primary" href="${esc(job.url)}" target="_blank" rel="noopener">${esc(tr(lang, "apply"))}<span class="sr-only">${esc(tr(lang, "apply_sr"))}</span><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"></path></svg></a>
            <button type="button" class="btn btn-secondary save-btn" data-save="${esc(job.id)}" aria-pressed="false">${STAR}<span data-save-label data-on="${esc(tr(lang, "saved"))}" data-off="${esc(tr(lang, "save"))}">${esc(tr(lang, "save"))}</span></button>
          </div>
        </div>
      </header>
      <section class="panel" aria-labelledby="who">
        <h2 id="who">${esc(tr(lang, "who_can_apply"))}</h2>
        <table class="who">
          <thead><tr><th scope="col">${esc(tr(lang, "country_col"))}</th><th scope="col">${esc(tr(lang, "verdict_col"))}</th><th scope="col">${esc(tr(lang, "why"))}</th></tr></thead>
          <tbody>${first}${rows}</tbody>
        </table>
      </section>
      ${
        job.quote
          ? `<section class="panel quote" aria-labelledby="says"><h2 id="says">${esc(tr(lang, "posting_says"))}</h2><blockquote lang="und"><p>${esc(job.quote)}</p></blockquote><p class="fine jp-note">${esc(tr(lang, "quote_note"))}</p></section>`
          : ""
      }
      <section class="panel" aria-labelledby="det">
        <h2 id="det">${esc(tr(lang, "details"))}</h2>
        <dl class="jp-details">${details.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>
      </section>
      <details class="panel report">
        <summary>${esc(tr(lang, "report"))}</summary>
        <form class="report-form" method="post" action="/api/report" data-g="${esc(JSON.stringify(mini))}">
          <input type="hidden" name="job" value="${esc(job.id)}">
          <input type="hidden" name="verdict" value="${esc(mine?.v ?? "")}">
          <label class="field"><span>${esc(tr(lang, "alerts_country"))}</span><select name="country">${reportOptions}</select></label>
          <fieldset>
            <legend class="legend-label">${esc(tr(lang, "report_q"))}</legend>
            <label class="radio"><input type="radio" name="kind" value="wrong_verdict" required>${esc(tr(lang, "report_wrong"))}</label>
            <label class="radio"><input type="radio" name="kind" value="closed">${esc(tr(lang, "report_closed"))}</label>
            <label class="radio"><input type="radio" name="kind" value="other">${esc(tr(lang, "report_info"))}</label>
          </fieldset>
          <label class="field"><span>${esc(tr(lang, "report_note"))}</span><textarea name="note" maxlength="500" rows="2"></textarea></label>
          <div><button class="btn btn-secondary" type="submit" data-sending="${esc(tr(lang, "sending"))}" data-ok="${esc(tr(lang, "report_sent"))}" data-err="${esc(tr(lang, "report_failed"))}">${esc(tr(lang, "report_send"))}</button></div>
          <p class="form-msg" role="status" aria-live="polite"></p>
        </form>
      </details>
    </div>
    <aside class="jp-side">
      <section class="panel">
        <div class="jp-co">
          ${avatar(job.company, job.company_key, job.logo, 44)}
          <div><b>${esc(job.company)}</b><span class="fine">${esc(tr(lang, "open_jobs_n", { n: job.company_n }))}${website ? ` · ${esc(website)}` : ""}</span></div>
        </div>
        ${named.length ? `<p class="jp-hires">${esc(tr(lang, "hires_here", { countries: named.join(", ") }))}</p>` : ""}
        <a href="${esc(href(lang, "company", job.company_key))}">${esc(tr(lang, "see_company"))}</a>
      </section>
      ${more ? `<section class="panel"><h2>${esc(tr(lang, "more_at", { company: job.company }))}</h2><ul class="jp-links">${more}</ul></section>` : ""}
      ${similar ? `<section class="panel"><h2>${esc(tr(lang, "similar"))}</h2><ul class="jp-links">${similar}</ul></section>` : ""}
      ${
        code in meta.countries
          ? `<section class="panel jp-guide"><h2>${esc(tr(lang, "guide_cta", { country: names[code] }))}</h2><a href="${esc(href(lang, "guide"))}#${code.toLowerCase()}">${esc(tr(lang, "nav_guide"))} <span class="flip">→</span></a></section>`
          : ""
      }
    </aside>
  </div>
</div>`;
}

