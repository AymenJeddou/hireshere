// Job page body, rendered per request by the Pages Function (functions/_job.js) from a detail
// shard (public/data/j/<xx>.json). Same markup and classes as the rest of the site.
import { formatDate, href, labels, languageName, type Lang, tr, type Verdict } from "../i18n";
import {
  avatar,
  type Ctx,
  esc,
  excluded,
  groupFor,
  groupText,
  isNew,
  when,
  lamp,
  nameList,
  pill,
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
      [tr(lang, "d_posted"), job.posted_at ? formatDate(job.posted_at, lang, true) : ""],
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
          `<li><a href="${esc(href(lang, "job", slug))}">${esc(title)}</a>${withCompany ? `<small>${esc(company)}</small>` : ""}${pill(v as Verdict, vname(v!))}</li>`,
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

  const v = mine && mine.v !== "not_eligible" ? (mine.v as Verdict) : null;
  const statusClass = v ?? "unclear";
  const statusTitle = !code
    ? tr(lang, "status_pick")
    : v
      ? tr(lang, `status_${v}` as never, { country: names[code] })
      : tr(lang, "status_not", { country: names[code] });
  const others = gs.filter((g) => g.v !== "not_eligible" && g !== mine);
  const alsoText = others.length
    ? tr(lang, "also_open", {
        places: others.map((g) => (g.c === "*" ? tr(lang, "where_anywhere").toLowerCase() : nameList(g.c, ctx, 4))).join(", "),
      })
    : "";
  const why = v ? reasonFor(mine!, ctx, code) : "";
  const STATUS_ICON: Record<string, string> = {
    eligible: '<path d="M7 12.5l3.3 3.3L17 9" stroke="#fff" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"></path>',
    likely: '<path d="M12 6a6 6 0 0 1 0 12z" fill="#fff"></path><circle cx="12" cy="12" r="6" fill="none" stroke="#fff" stroke-width="2"></circle>',
    unclear: '<path d="M12 7v6M12 16.5v.5" stroke="#fff" stroke-width="2.6" stroke-linecap="round"></path>',
  };
  const tzFact = job.tz && (job.tz[0] !== null || job.tz[1] !== null) ? tzText : tr(lang, "any_tz");
  const facts: [string, string][] = [
    [tr(lang, "d_salary"), salaryText(job.salary, lang) || tr(lang, "not_stated")],
    [tr(lang, "d_level"), job.seniority !== "unclear" ? lab("seniority", job.seniority) : tr(lang, "not_stated")],
    [tr(lang, "d_contract"), job.engagement !== "unclear" ? lab("engagement", job.engagement) : tr(lang, "not_stated")],
    [tr(lang, "d_field"), lab("family", job.family) || tr(lang, "not_stated")],
    [tr(lang, "working_hours"), tzFact],
    [tr(lang, "d_posted"), job.posted_at ? formatDate(job.posted_at, lang, true) : tr(lang, "not_stated")],
    [tr(lang, "d_first_seen"), formatDate(job.seen_at, lang, true)],
  ];
  const site = website || job.company;
  const applyBtn = (cls: string) =>
    `<a class="btn btn-accent ${cls}" href="${esc(job.url)}" target="_blank" rel="noopener">${esc(tr(lang, "apply_on", { site }))}<span class="sr-only">${esc(tr(lang, "apply_sr"))}</span><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"></path></svg></a>`;
  const metaLine = [
    `<a href="${esc(href(lang, "company", job.company_key))}">${esc(job.company)}</a>`,
    esc(tr(lang, `workplace_${job.workplace === "hybrid" ? "hybrid" : "fully_remote"}` as never)),
    job.engagement !== "unclear" ? esc(lab("engagement", job.engagement)) : "",
    esc(salaryText(job.salary, lang)),
  ]
    .filter(Boolean)
    .join(" · ");

  return `<section class="jtop"><div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb">
    <a href="${esc(href(lang, "search"))}">${esc(tr(lang, "nav_find"))}</a><span aria-hidden="true"> <span class="flip">›</span> </span>
    ${code ? `<a href="${esc(searchHref)}">${esc(names[code])}</a><span aria-hidden="true"> <span class="flip">›</span> </span>` : ""}
    <span aria-current="page">${esc(job.company)}</span>
  </nav>
  <div class="jhead">
    ${avatar(job.company, job.company_key, job.logo, 76)}
    <div>
      <h1>${esc(job.title)}${isNew(when(job), meta.updated) ? ` <span class="new-badge">${esc(tr(lang, "new_badge"))}</span>` : ""}</h1>
      <p class="jmeta">${metaLine}</p>
    </div>
    ${applyBtn("jhead-apply")}
  </div>
</div></section>
<div class="wrap job-page">
  <div class="jp-grid">
    <div class="jp-main">
      <section class="status ${statusClass}" aria-labelledby="status">
        <div class="status-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="26" height="26">${STATUS_ICON[statusClass]}</svg></div>
        <div>
          <h2 id="status">${esc(statusTitle)}</h2>
          ${why || alsoText ? `<p>${esc([why ? `${why}.` : "", alsoText].filter(Boolean).join(" "))}</p>` : ""}
        </div>
        ${job.quote ? `<blockquote lang="und"><p>${esc(job.quote)}</p><small>${esc(tr(lang, "status_quote_note"))}</small></blockquote>` : ""}
      </section>
      <section class="panel" aria-labelledby="glance">
        <h2 id="glance">${esc(tr(lang, "at_a_glance"))}</h2>
        <dl class="facts">${facts.map(([k, val]) => `<div class="fact"><dt>${esc(k)}</dt><dd>${esc(val)}</dd></div>`).join("")}</dl>
      </section>
      <section class="panel" aria-labelledby="who">
        <h2 id="who">${esc(tr(lang, "who_can_apply"))}</h2>
        <div class="whomap" data-whomap data-g="${esc(JSON.stringify(mini))}" data-you="${esc(code)}"></div>
        <p class="map-legend dark">
          <span><i style="background:#ff7a59"></i>${esc(tr(lang, "map_you"))}</span>
          <span><i style="background:#157a43"></i>${esc(tr(lang, "map_can"))}</span>
          <span><i style="background:#e0a85a"></i>${esc(tr(lang, "map_likely"))}</span>
          <span><i style="background:#e4e0d8"></i>${esc(tr(lang, "map_not"))}</span>
        </p>
        <details class="who-list">
          <summary>${esc(tr(lang, "more_details"))}</summary>
          <table class="who"><tbody>${first}${rows}</tbody></table>
        </details>
      </section>
      <details class="panel more-details">
        <summary>${esc(tr(lang, "details"))}</summary>
        <dl class="jp-details">${details.map(([k, val]) => `<div><dt>${esc(k)}</dt><dd>${esc(val)}</dd></div>`).join("")}</dl>
      </details>
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
      <section class="panel applybox">
        <div class="jp-co">
          ${avatar(job.company, job.company_key, job.logo, 48)}
          <div><b>${esc(job.company)}</b><span class="fine">${website ? `${esc(website)} · ` : ""}${esc(tr(lang, "open_jobs_n", { n: job.company_n }))}</span></div>
        </div>
        ${named.length ? `<p class="jp-hires">${esc(tr(lang, "hires_here", { countries: named.join(", ") }))}</p>` : ""}
        ${applyBtn("wide")}
        <button type="button" class="btn btn-secondary save-btn wide" data-save="${esc(job.id)}" aria-pressed="false">${STAR}<span data-save-label data-on="${esc(tr(lang, "saved"))}" data-off="${esc(tr(lang, "save_job"))}">${esc(tr(lang, "save_job"))}</span></button>
        <p class="fine">${esc(tr(lang, "apply_note", { company: job.company }))}</p>
        <a class="see-co" href="${esc(href(lang, "company", job.company_key))}">${esc(tr(lang, "see_company"))}</a>
      </section>
      ${similar ? `<section class="panel"><h2>${esc(tr(lang, "similar_for_you"))}</h2><ul class="jp-links">${similar}</ul></section>` : ""}
      ${more ? `<section class="panel"><h2>${esc(tr(lang, "more_at", { company: job.company }))}</h2><ul class="jp-links">${more}</ul></section>` : ""}
      ${
        code in meta.countries
          ? `<section class="panel jp-guide"><h2>${esc(tr(lang, "guide_cta", { country: names[code] }))}</h2><a href="${esc(href(lang, "guide"))}#${code.toLowerCase()}">${esc(tr(lang, "nav_guide"))} <span class="flip">→</span></a></section>`
          : ""
      }
    </aside>
  </div>
</div>`;
}

