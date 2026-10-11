import type { Lang } from "../i18n";
import { card, type Ctx, loadJobs, type SJob, verdictsFor, when } from "./cards";
import { remember, visitorCountry } from "./country";
import { languagesFit, loadProfile } from "./profile";
import { initSaveButtons } from "./saved";
// Job search: one country select, facets with live counts, URL state, pagination.
const PAGE = 20;
const MULTI = ["f", "s", "e", "l"] as const;
type V = "eligible" | "likely" | "unclear";
const DEFAULT_V: V[] = ["eligible", "likely"];
const RANK: Record<V, number> = { eligible: 0, likely: 1, unclear: 2 };

type Strings = Record<string, string | Record<string, string>>;
type State = {
  q: string;
  c: string;
  v: V[];
  f: string[];
  s: string[];
  e: string[];
  l: string[];
  d: string;
  sal: boolean;
  sort: string;
};
type Card = {
  job: SJob;
  vs: V[]; // shown verdicts for the selected country (any country when none is selected)
  q: string;
  days: number;
};
const fill = (s: string, vars: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));

export async function initSearch(): Promise<void> {
  const root = document.querySelector<HTMLElement>("[data-search]");
  if (!root) return;
  const t = JSON.parse(root.dataset.i18n ?? "{}") as Strings;
  const lang = root.dataset.lang as Lang;
  const updated = root.dataset.updated ?? "";
  const form = root.querySelector<HTMLFormElement>("[data-filters]")!;
  const band = root.querySelector<HTMLFormElement>("[data-searchbar]")!;
  const bandQ = band.elements.namedItem("q") as HTMLInputElement;
  // The country lives in the site header ("Your country"), shared by every page.
  const bandC = document.querySelector<HTMLSelectElement>("[data-country]")!;
  const sortSel = root.querySelector<HTMLSelectElement>("[data-sort]")!;
  const list = root.querySelector<HTMLOListElement>("[data-cards]")!;
  const pager = root.querySelector<HTMLElement>("[data-pager]")!;
  const chips = root.querySelector<HTMLElement>("[data-chips]")!;
  const aside = root.querySelector<HTMLElement>(".filters")!;
  const counts = new Map([...root.querySelectorAll<HTMLElement>("[data-n]")].map((n) => [n.dataset.n!, n]));
  const names = Object.fromEntries([...bandC.options].filter((o) => o.value).map((o) => [o.value, o.text]));
  const ctx: Ctx = { lang, code: "", names, updated };

  const [jobs, country] = await Promise.all([loadJobs(lang), visitorCountry((c) => c in names)]);
  const now = Date.parse(updated);
  const cards: Card[] = jobs.map((job) => ({
    job,
    vs: [],
    q: `${job.title} ${job.company}`.toLowerCase(),
    days: Math.max(0, Math.floor((now - Date.parse(when(job))) / 86400000)),
  }));
  let scored = "-";
  const score = (code: string) => {
    if (code === scored) return;
    for (const k of cards) k.vs = verdictsFor(k.job.groups, code) as V[];
    scored = code;
  };
  root.querySelector("[data-fallback]")?.remove();
  list.classList.remove("plain-links");
  root.classList.add("enhanced");

  // ---- state <-> form <-> URL
  const boxes = (name: string) => [...form.querySelectorAll<HTMLInputElement>(`input[name="${name}"]`)];
  let page = 1;
  function read(): State {
    const fd = new FormData(form);
    return {
      q: bandQ.value.trim().toLowerCase(),
      c: bandC.value,
      v: fd.getAll("v").map(String) as V[],
      f: fd.getAll("f").map(String),
      s: fd.getAll("s").map(String),
      e: fd.getAll("e").map(String),
      l: fd.getAll("l").map(String),
      d: String(fd.get("d") ?? ""),
      sal: fd.has("sal"),
      sort: sortSel.value,
    };
  }
  function write(st: Partial<State>) {
    for (const k of [...MULTI, "v"] as const) {
      const vals = (st[k] as string[] | undefined) ?? (k === "v" ? DEFAULT_V : []);
      boxes(k).forEach((b) => (b.checked = vals.includes(b.value)));
    }
    boxes("d").forEach((b) => (b.checked = b.value === (st.d ?? "")));
    boxes("sal").forEach((b) => (b.checked = !!st.sal));
    bandQ.value = st.q ?? "";
    sortSel.value = st.sort ?? "";
  }
  const params = new URLSearchParams(location.search);
  const split = (k: string) => (params.get(k) ?? "").split(",").filter(Boolean);
  page = Math.max(1, Number(params.get("p")) || 1);
  write({
    q: params.get("q") ?? "",
    v: params.has("v") ? (split("v") as V[]) : DEFAULT_V,
    f: split("f"),
    s: split("s"),
    e: split("e"),
    l: split("l"),
    d: params.get("d") ?? "",
    sal: params.get("sal") === "1",
    sort: params.get("sort") ?? "",
  });
  bandC.value = country;

  // Light profile: default filters when the URL carries none.
  const profile = loadProfile();
  const banner = root.querySelector<HTMLElement>("[data-profile-banner]")!;
  const filtered = [...params.keys()].some((k) => k !== "c");
  let useProfile = !!profile && !filtered;
  if (useProfile && profile) {
    write({ f: profile.f ? [profile.f] : [], s: profile.s ? [profile.s] : [], e: profile.e ? [profile.e] : [] });
  }
  banner.hidden = !useProfile;
  root.querySelector("[data-profile-off]")?.addEventListener("click", () => {
    useProfile = false;
    banner.hidden = true;
    write({});
    apply();
  });

  // ---- filtering
  type Group = "v" | "f" | "s" | "e" | "l" | "d" | "sal";
  function passes(k: Card, st: State, skip?: Group): boolean {
    const j = k.job;
    const words = st.q.split(/\s+/).filter(Boolean);
    return (
      k.vs.length > 0 &&
      (skip === "v" || k.vs.some((v) => st.v.includes(v))) &&
      (skip === "f" || !st.f.length || st.f.includes(j.family)) &&
      (skip === "s" || !st.s.length || st.s.includes(j.seniority)) &&
      (skip === "e" || !st.e.length || st.e.includes(j.engagement)) &&
      (skip === "l" || !st.l.length || st.l.every((l) => j.languages.includes(l))) &&
      (skip === "d" || !st.d || k.days < Number(st.d)) &&
      (skip === "sal" || !st.sal || !!j.salary) &&
      words.every((w) => k.q.includes(w)) &&
      (!useProfile || !profile || languagesFit(j.languages, profile.langs))
    );
  }
  const best = (k: Card, st: State) => Math.min(...k.vs.filter((v) => st.v.includes(v)).map((v) => RANK[v]));

  function updateCounts(st: State) {
    const set = (key: string, n: number) => {
      const el = counts.get(key);
      if (el) el.textContent = String(n);
    };
    const pool = (g: Group) => cards.filter((k) => passes(k, st, g));
    const pv = pool("v");
    for (const v of ["eligible", "likely", "unclear"] as V[]) set(`v:${v}`, pv.filter((k) => k.vs.includes(v)).length);
    for (const g of ["f", "s", "e"] as const) {
      const key = ({ f: "family", s: "seniority", e: "engagement" } as const)[g];
      const pg = pool(g);
      boxes(g).forEach((b) => set(`${g}:${b.value}`, pg.filter((k) => k.job[key] === b.value).length));
    }
    const pl = pool("l");
    boxes("l").forEach((b) => set(`l:${b.value}`, pl.filter((k) => k.job.languages.includes(b.value)).length));
    const pd = pool("d");
    set("d:1", pd.filter((k) => k.days < 1).length);
    set("d:7", pd.filter((k) => k.days < 7).length);
    set("d:", pd.length);
    set("sal:1", pool("sal").filter((k) => k.job.salary).length);
  }

  function renderPager(total: number) {
    const pages = Math.ceil(total / PAGE);
    pager.replaceChildren();
    if (pages <= 1) return;
    const btn = (label: string, p: number, opts: { current?: boolean; aria?: string; disabled?: boolean } = {}) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      if (opts.aria) b.setAttribute("aria-label", opts.aria);
      if (opts.current) b.setAttribute("aria-current", "page");
      b.disabled = !!opts.disabled;
      b.addEventListener("click", () => {
        page = p;
        apply(false);
        root!.querySelector("#count")?.scrollIntoView({ block: "start" });
      });
      return b;
    };
    pager.append(btn("‹", page - 1, { aria: String(t.prev), disabled: page === 1 }));
    const shown = [...new Set([1, page - 1, page, page + 1, pages])].filter((p) => p >= 1 && p <= pages).sort((a, b) => a - b);
    shown.forEach((p, i) => {
      if (i && p - shown[i - 1] > 1) {
        const gap = document.createElement("span");
        gap.textContent = "…";
        pager.append(gap);
      }
      pager.append(btn(String(p), p, { current: p === page }));
    });
    pager.append(btn("›", page + 1, { aria: String(t.next), disabled: page === pages }));
  }

  function renderChips(st: State) {
    const keep = chips.querySelector("[data-open-filters]")!;
    const active = st.f.length + st.s.length + st.e.length + st.l.length + (st.d ? 1 : 0) + (st.sal ? 1 : 0);
    keep.textContent = active ? `${t.filters} (${active})` : String(t.filters);
    const chip = (label: string, undo: () => void) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = `${label} ✕`;
      b.setAttribute("aria-label", `${t.remove}: ${label}`);
      b.addEventListener("click", () => {
        undo();
        page = 1;
        apply();
      });
      return b;
    };
    const labelOf = (name: string, value: string) => {
      const label = form.querySelector(`input[name="${name}"][value="${CSS.escape(value)}"]`)?.closest("label");
      const copy = label?.cloneNode(true) as HTMLElement | undefined;
      copy?.querySelector(".n")?.remove();
      return copy?.textContent?.trim() || value;
    };
    const out: HTMLElement[] = [];
    if (st.q) out.push(chip(`“${bandQ.value.trim()}”`, () => (bandQ.value = "")));
    for (const k of MULTI)
      for (const v of st[k])
        out.push(chip(labelOf(k, v), () => boxes(k).forEach((b) => b.value === v && (b.checked = false))));
    if (st.d) out.push(chip(labelOf("d", st.d), () => boxes("d").forEach((b) => (b.checked = b.value === ""))));
    if (st.sal) out.push(chip(labelOf("sal", "1"), () => boxes("sal").forEach((b) => (b.checked = false))));
    chips.replaceChildren(keep, ...out);
  }

  function apply(resetPage = true) {
    if (resetPage) page = 1;
    const st = read();
    score(st.c);
    ctx.code = st.c;
    const matches = cards.filter((k) => passes(k, st));
    matches.sort((a, b) =>
      st.sort === "new"
        ? when(b.job).localeCompare(when(a.job))
        : best(a, st) - best(b, st) || when(b.job).localeCompare(when(a.job)),
    );
    const pages = Math.max(1, Math.ceil(matches.length / PAGE));
    page = Math.min(page, pages);
    list.innerHTML = matches
      .slice((page - 1) * PAGE, page * PAGE)
      .map((k) => card(k.job, ctx, st.v))
      .join("");
    initSaveButtons(list);

    updateCounts(st);
    renderPager(matches.length);
    renderChips(st);
    root!.querySelector("[data-count]")!.textContent =
      matches.length === 1 ? String(t.jobsN1) : fill(String(t.jobsN), { n: matches.length });
    // The heading follows the verdict boxes: the usual "open or likely open", else the ticked verdicts.
    const usual = st.v.length === 2 && DEFAULT_V.every((v) => st.v.includes(v));
    const place = st.c ? names[st.c] : String(t.region);
    const label = t.label as Record<string, string>;
    root!.querySelector("[data-sub]")!.textContent = usual
      ? st.c
        ? fill(String(t.openTo), { places: place })
        : String(t.openAny)
      : `${st.v.map((v) => label[v]).join(" / ")} · ${place}`;
    // The band heading names the visitor's country: "Remote jobs open to <Tunisia>".
    const h1 = root!.querySelector<HTMLElement>(".band h1");
    if (h1) {
      if (st.c) {
        const [pre, post] = String(t.title).split("{country}");
        const span = document.createElement("span");
        span.className = "place";
        span.textContent = names[st.c];
        h1.replaceChildren(pre, span, post ?? "");
      } else h1.textContent = String(t.titleAny);
    }
    const empty = root!.querySelector<HTMLElement>("[data-empty]")!;
    empty.hidden = matches.length > 0;
    root!.querySelector("[data-empty-title]")!.textContent = st.q
      ? fill(String(t.noneQ), { q: bandQ.value.trim() })
      : String(t.noneTitle);
    const alertC = root!.querySelector<HTMLSelectElement>("[data-alert-country]");
    if (alertC && st.c) alertC.value = st.c;

    const p = new URLSearchParams();
    if (st.q) p.set("q", bandQ.value.trim());
    if (st.c) p.set("c", st.c);
    for (const k of MULTI) if (st[k].length) p.set(k, st[k].join(","));
    if (!(st.v.length === DEFAULT_V.length && DEFAULT_V.every((v) => st.v.includes(v)))) p.set("v", st.v.join(","));
    if (st.d) p.set("d", st.d);
    if (st.sal) p.set("sal", "1");
    if (st.sort) p.set("sort", st.sort);
    if (page > 1) p.set("p", String(page));
    const qs = p.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }

  // ---- events
  form.addEventListener("change", () => apply());
  sortSel.addEventListener("change", () => apply());
  band.addEventListener("submit", (ev) => {
    ev.preventDefault();
    apply();
  });
  let timer: number | undefined;
  bandQ.addEventListener("input", () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => apply(), 160);
  });
  bandC.addEventListener("change", () => {
    remember(bandC.value);
    apply();
  });
  root.querySelectorAll("[data-clear]").forEach((b) =>
    b.addEventListener("click", () => {
      write({});
      apply();
    }),
  );
  root.querySelector("[data-open-filters]")?.addEventListener("click", (ev) => {
    ev.preventDefault();
    aside.classList.toggle("open");
  });

  apply(false);
}
