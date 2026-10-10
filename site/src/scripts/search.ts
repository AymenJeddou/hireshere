import { groups, groupText, type LineText, type V } from "../verdictline";
import { languagesFit, loadProfile } from "./profile";
import { initSaveButtons } from "./saved";
// Job search: facets with live counts, URL state, pagination, alerts form. No framework.
const PAGE = 20;
const MULTI = ["c", "f", "s", "e", "l"] as const;
const DEFAULT_V: V[] = ["eligible", "likely"];

type Strings = LineText & Record<string, string | Record<string, string>>;
type State = {
  q: string;
  c: string[];
  v: V[];
  f: string[];
  s: string[];
  e: string[];
  l: string[];
  d: string;
  sal: boolean;
  sort: string;
  p: number;
};
type Card = {
  el: HTMLLIElement;
  vs: Record<string, V>;
  r: Record<string, string>;
  f: string;
  s: string;
  e: string;
  l: string[];
  q: string;
  seen: string;
  days: number;
  sal: boolean;
};
const fill = (s: string, vars: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
const RANK: Record<V, number> = { eligible: 0, likely: 1, unclear: 2 };

export function initSearch(): void {
  const root = document.querySelector<HTMLElement>("[data-search]");
  if (!root) return;
  const t = JSON.parse(root.dataset.i18n ?? "{}") as Strings;
  const ALL = Object.keys(t.names);
  const form = root.querySelector<HTMLFormElement>("[data-filters]")!;
  const band = root.querySelector<HTMLFormElement>("[data-searchbar]")!;
  const bandQ = band.elements.namedItem("q") as HTMLInputElement;
  const bandC = band.elements.namedItem("c") as HTMLSelectElement;
  const sortSel = root.querySelector<HTMLSelectElement>("[data-sort]")!;
  const list = root.querySelector<HTMLOListElement>("[data-cards]")!;
  const pager = root.querySelector<HTMLElement>("[data-pager]")!;
  const chips = root.querySelector<HTMLElement>("[data-chips]")!;
  const aside = root.querySelector<HTMLElement>(".filters")!;
  const cards: Card[] = [...list.querySelectorAll<HTMLLIElement>(".card")].map((el) => ({
    el,
    vs: JSON.parse(el.dataset.vs ?? "{}"),
    r: JSON.parse(el.dataset.r ?? "{}"),
    f: el.dataset.f ?? "",
    s: el.dataset.s ?? "",
    e: el.dataset.e ?? "",
    l: (el.dataset.l ?? "").split(" ").filter(Boolean),
    q: el.dataset.q ?? "",
    seen: el.dataset.seen ?? "",
    days: Number(el.dataset.days ?? 0),
    sal: el.dataset.sal === "1",
  }));
  const counts = new Map([...root.querySelectorAll<HTMLElement>("[data-n]")].map((n) => [n.dataset.n!, n]));
  initSaveButtons(root);
  root.classList.add("enhanced");

  // ---- state <-> form <-> URL
  const boxes = (name: string) => [...form.querySelectorAll<HTMLInputElement>(`input[name="${name}"]`)];
  function read(): State {
    const fd = new FormData(form);
    return {
      q: bandQ.value.trim().toLowerCase(),
      c: fd.getAll("c").map(String),
      v: fd.getAll("v").map(String) as V[],
      f: fd.getAll("f").map(String),
      s: fd.getAll("s").map(String),
      e: fd.getAll("e").map(String),
      l: fd.getAll("l").map(String),
      d: String(fd.get("d") ?? ""),
      sal: fd.has("sal"),
      sort: sortSel.value,
      p: page,
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
  let page = Math.max(1, Number(params.get("p")) || 1);
  write({
    q: params.get("q") ?? "",
    c: split("c").map((c) => c.toUpperCase()),
    v: params.has("v") ? (split("v") as V[]) : DEFAULT_V,
    f: split("f"),
    s: split("s"),
    e: split("e"),
    l: split("l"),
    d: params.get("d") ?? "",
    sal: params.get("sal") === "1",
    sort: params.get("sort") ?? "",
  });

  // Light profile: default filters when the URL carries none.
  const profile = loadProfile();
  const banner = root.querySelector<HTMLElement>("[data-profile-banner]")!;
  let useProfile = !!profile && !location.search;
  if (useProfile && profile) {
    write({
      c: profile.country ? [profile.country] : [],
      f: profile.f ? [profile.f] : [],
      s: profile.s ? [profile.s] : [],
      e: profile.e ? [profile.e] : [],
    });
  }
  banner.hidden = !useProfile;
  root.querySelector("[data-profile-off]")?.addEventListener("click", () => {
    useProfile = false;
    banner.hidden = true;
    write({});
    apply();
  });

  // ---- filtering
  const scopeOf = (st: State) => (st.c.length ? st.c : ALL);
  type Group = "c" | "v" | "f" | "s" | "e" | "l" | "d" | "sal" | "q";
  function passes(k: Card, st: State, skip?: Group): boolean {
    const scope = scopeOf(st);
    const words = st.q.split(/\s+/).filter(Boolean);
    return (
      (skip === "c" || skip === "v" || scope.some((c) => k.vs[c] && st.v.includes(k.vs[c]))) &&
      (skip === "f" || !st.f.length || st.f.includes(k.f)) &&
      (skip === "s" || !st.s.length || st.s.includes(k.s)) &&
      (skip === "e" || !st.e.length || st.e.includes(k.e)) &&
      (skip === "l" || !st.l.length || st.l.every((l) => k.l.includes(l))) &&
      (skip === "d" || !st.d || k.days < Number(st.d)) &&
      (skip === "sal" || !st.sal || k.sal) &&
      words.every((w) => k.q.includes(w)) &&
      (!useProfile || !profile || languagesFit(k.l, profile.langs))
    );
  }
  const best = (k: Card, st: State) =>
    Math.min(...scopeOf(st).filter((c) => k.vs[c] && st.v.includes(k.vs[c])).map((c) => RANK[k.vs[c]]));

  function updateCounts(st: State) {
    const set = (key: string, n: number) => {
      const el = counts.get(key);
      if (el) el.textContent = String(n);
    };
    const pool = (g: Group) => cards.filter((k) => passes(k, st, g));
    const pc = pool("c");
    for (const c of ALL) set(`c:${c}`, pc.filter((k) => k.vs[c] && st.v.includes(k.vs[c])).length);
    const pv = pool("v");
    for (const v of ["eligible", "likely", "unclear"] as V[])
      set(`v:${v}`, pv.filter((k) => scopeOf(st).some((c) => k.vs[c] === v)).length);
    for (const g of ["f", "s", "e"] as const) {
      const pg = pool(g);
      boxes(g).forEach((b) => set(`${g}:${b.value}`, pg.filter((k) => k[g] === b.value).length));
    }
    const pl = pool("l");
    boxes("l").forEach((b) => set(`l:${b.value}`, pl.filter((k) => k.l.includes(b.value)).length));
    const pd = pool("d");
    set("d:1", pd.filter((k) => k.days < 1).length);
    set("d:7", pd.filter((k) => k.days < 7).length);
    set("d:", pd.length);
    set("sal:1", pool("sal").filter((k) => k.sal).length);
  }

  function updateLine(k: Card, st: State) {
    const scope = scopeOf(st);
    const gs = groups(k.vs, scope.filter((c) => k.vs[c]), st.v);
    const line = k.el.querySelector<HTMLElement>("[data-line]")!;
    const lamps = new Map(
      [...k.el.querySelectorAll<HTMLElement>(".vl")].map((s) => [s.className.match(/v-(\w+)/)![1], s.querySelector("svg")]),
    );
    line.replaceChildren(
      ...gs.map((g) => {
        const span = document.createElement("span");
        span.className = `vl v-${g.v}`;
        const lamp = lamps.get(g.v) ?? lampFor(g.v);
        if (lamp) span.append(lamp.cloneNode(true));
        span.append(groupText(g, st.c.length ? 0 : scope.length, t));
        return span;
      }),
    );
    if (gs.length === 1) {
      const why = document.createElement("span");
      why.className = "why";
      why.textContent = k.r[gs[0].codes[0]] ?? "";
      line.append(why);
    }
  }
  // A lamp of each shape, taken from the facet list, for cards that did not render one.
  const lampFor = (v: V) => form.querySelector(`.v-${v} svg`);

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
        root.querySelector("#count")?.scrollIntoView({ block: "start" });
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
    const active = st.c.length + st.f.length + st.s.length + st.e.length + st.l.length + (st.d ? 1 : 0) + (st.sal ? 1 : 0);
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
    const matches = cards.filter((k) => passes(k, st));
    matches.sort((a, b) =>
      st.sort === "new"
        ? b.seen.localeCompare(a.seen)
        : best(a, st) - best(b, st) || b.seen.localeCompare(a.seen),
    );
    const pages = Math.max(1, Math.ceil(matches.length / PAGE));
    page = Math.min(page, pages);
    const visible = new Set(matches.slice((page - 1) * PAGE, page * PAGE));
    for (const k of cards) k.el.hidden = !visible.has(k);
    list.append(...matches.map((k) => k.el));
    for (const k of visible) updateLine(k, st);

    updateCounts(st);
    renderPager(matches.length);
    renderChips(st);
    const names = st.c.map((c) => t.names[c]);
    root.querySelector("[data-count]")!.textContent =
      matches.length === 1 ? String(t.jobsN1) : fill(String(t.jobsN), { n: matches.length });
    // The heading follows the verdict boxes: the usual "open or likely open", else the ticked verdicts.
    const usual = st.v.length === 2 && DEFAULT_V.every((v) => st.v.includes(v));
    const places = names.length ? names.join(", ") : String(t.region);
    const label = t.label as Record<string, string>;
    root.querySelector("[data-sub]")!.textContent = usual
      ? names.length
        ? fill(String(t.openTo), { places })
        : String(t.openAny)
      : `${st.v.map((v) => label[v]).join(" / ")} · ${places}`;
    const empty = root.querySelector<HTMLElement>("[data-empty]")!;
    empty.hidden = matches.length > 0;
    root.querySelector("[data-empty-title]")!.textContent = st.q
      ? fill(String(t.noneQ), { q: bandQ.value.trim() })
      : String(t.noneTitle);
    // Band select mirrors the country boxes: one country, all, or "several".
    bandC.value = st.c.length === 0 ? "" : st.c.length === 1 ? st.c[0] : "multi";
    const alertC = root.querySelector<HTMLSelectElement>("[data-alert-country]");
    if (alertC && st.c.length) alertC.value = st.c[0];

    const p = new URLSearchParams();
    if (st.q) p.set("q", bandQ.value.trim());
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
    if (bandC.value !== "multi") boxes("c").forEach((b) => (b.checked = b.value === bandC.value));
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

  // ---- alerts form
  root.querySelector<HTMLFormElement>(".alerts-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = ev.currentTarget as HTMLFormElement;
    const msg = f.querySelector<HTMLElement>(".form-msg")!;
    const email = f.elements.namedItem("email") as HTMLInputElement;
    if (!email.value || !email.validity.valid) {
      msg.className = "form-msg err";
      msg.textContent = String(t.alertsInvalid);
      email.setAttribute("aria-invalid", "true");
      email.focus();
      return;
    }
    email.removeAttribute("aria-invalid");
    const button = f.querySelector<HTMLButtonElement>('button[type="submit"]')!;
    const label = button.textContent;
    button.disabled = true;
    button.textContent = String(t.sending);
    try {
      const res = await fetch(f.action, { method: "POST", body: new FormData(f) });
      if (!res.ok) throw new Error(String(res.status));
      msg.className = "form-msg ok";
      msg.textContent = String(t.alertsOk);
      f.reset();
    } catch {
      msg.className = "form-msg err";
      msg.textContent = String(t.alertsFailed);
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  });

  apply(false);
}
