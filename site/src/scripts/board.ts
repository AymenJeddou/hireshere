// Country board: filtering, URL state, pagination, report and alert forms. No framework.
const PAGE = 40;
const KEYS = ["q", "f", "s", "l", "e"] as const;
const DEFAULT_VERDICTS = ["eligible", "likely"];

type Strings = Record<string, string>;
const fill = (s: string, vars: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));

export function initBoard(): void {
  const root = document.querySelector<HTMLElement>(".board");
  if (!root) return;
  const t: Strings = JSON.parse(root.dataset.i18n ?? "{}");
  const form = root.querySelector<HTMLFormElement>(".filters")!;
  const rows = [...root.querySelectorAll<HTMLLIElement>("[data-jobs] > .job")];
  const status = root.querySelector<HTMLElement>("[data-status]")!;
  const empty = root.querySelector<HTMLElement>("[data-empty]")!;
  const more = root.querySelector<HTMLButtonElement>("[data-more]")!;
  const counts = new Map(
    [...root.querySelectorAll<HTMLElement>("[data-count]")].map((el) => [el.dataset.count!, el]),
  );
  let limit = PAGE;
  root.classList.add("enhanced");
  const toggle = root.querySelector<HTMLButtonElement>("[data-filter-toggle]")!;
  const filterRow = root.querySelector<HTMLElement>(".filter-row")!;
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    filterRow.classList.toggle("open", open);
  });

  // Restore filters from the URL so a filtered view can be shared.
  const params = new URLSearchParams(location.search);
  if (params.has("v")) {
    const vs = params.get("v")!.split(",");
    form.querySelectorAll<HTMLInputElement>('input[name="v"]').forEach((i) => {
      i.checked = vs.includes(i.value);
    });
  }
  for (const k of KEYS) {
    const el = form.elements.namedItem(k) as HTMLInputElement | HTMLSelectElement | null;
    if (el && params.has(k)) el.value = params.get(k)!;
  }

  function state() {
    const fd = new FormData(form);
    return {
      v: fd.getAll("v").map(String),
      q: String(fd.get("q") ?? "").trim().toLowerCase(),
      f: String(fd.get("f") ?? ""),
      s: String(fd.get("s") ?? ""),
      l: String(fd.get("l") ?? ""),
      e: String(fd.get("e") ?? ""),
    };
  }

  function apply(resetLimit = true) {
    if (resetLimit) limit = PAGE;
    const st = state();
    const words = st.q.split(/\s+/).filter(Boolean);
    const perVerdict: Record<string, number> = { eligible: 0, likely: 0, unclear: 0 };
    const matches: HTMLLIElement[] = [];
    for (const row of rows) {
      const d = row.dataset;
      const ok =
        (!st.f || d.f === st.f) &&
        (!st.s || d.s === st.s) &&
        (!st.e || d.e === st.e) &&
        (!st.l || (d.l ?? "").split(" ").includes(st.l)) &&
        words.every((w) => (d.q ?? "").includes(w));
      if (ok) perVerdict[d.v!]++;
      if (ok && st.v.includes(d.v!)) matches.push(row);
    }
    const visible = new Set(matches.slice(0, limit));
    for (const row of rows) row.hidden = !visible.has(row);
    for (const [v, el] of counts) el.textContent = String(perVerdict[v] ?? 0);

    const active = (["f", "s", "l", "e"] as const).filter((k) => st[k]).length;
    toggle.querySelector("[data-filter-label]")!.textContent = active
      ? fill(t.filtersActive, { n: active })
      : t.filters;
    status.textContent = fill(t.count, { shown: visible.size, total: matches.length });
    empty.hidden = matches.length > 0;
    const left = matches.length - visible.size;
    more.hidden = left <= 0;
    more.textContent = fill(t.more, { n: Math.min(PAGE, left) });

    // Keep the URL in sync without adding history entries.
    const p = new URLSearchParams();
    const vDefault = st.v.length === DEFAULT_VERDICTS.length && DEFAULT_VERDICTS.every((v) => st.v.includes(v));
    if (!vDefault) p.set("v", st.v.join(","));
    for (const k of KEYS) if (st[k]) p.set(k, st[k]);
    const qs = p.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }

  let timer: number | undefined;
  form.addEventListener("input", (ev) => {
    const target = ev.target as HTMLElement;
    window.clearTimeout(timer);
    if (target.matches('input[type="search"]')) timer = window.setTimeout(() => apply(), 140);
    else apply();
  });
  form.addEventListener("reset", () => {
    // Let the browser restore defaults first, then re-filter.
    window.setTimeout(() => apply(), 0);
  });
  root.querySelector("[data-reset]")?.addEventListener("click", () => form.reset());
  more.addEventListener("click", () => {
    const firstNew = rows.filter((r) => !r.hidden).length;
    limit += PAGE;
    apply(false);
    // Move focus to the first newly revealed job for keyboard and screen reader users.
    const next = rows.filter((r) => !r.hidden)[firstNew];
    next?.querySelector<HTMLElement>(".job-title")?.setAttribute("tabindex", "-1");
    next?.querySelector<HTMLElement>(".job-title")?.focus({ preventScroll: false });
  });

  // Report form: cloned from one template when a row's "Report an error" opens.
  const template = root.querySelector<HTMLTemplateElement>("#report-template");
  root.addEventListener(
    "toggle",
    (ev) => {
      const details = ev.target as HTMLDetailsElement;
      if (!details.matches?.(".report") || !details.open || !template) return;
      const slot = details.querySelector(".report-slot");
      if (!slot || slot.childElementCount) return;
      const node = template.content.cloneNode(true) as DocumentFragment;
      const row = details.closest<HTMLLIElement>(".job")!;
      const f = node.querySelector("form")!;
      (f.elements.namedItem("job") as HTMLInputElement).value = row.dataset.id ?? "";
      (f.elements.namedItem("verdict") as HTMLInputElement).value = row.dataset.v ?? "";
      slot.append(node);
      slot.querySelector<HTMLInputElement>('input[type="radio"]')?.focus();
    },
    true,
  );

  root.addEventListener("submit", async (ev) => {
    const f = ev.target as HTMLFormElement;
    if (!f.matches(".report-form, .alerts-form")) return;
    ev.preventDefault();
    const msg = f.querySelector<HTMLElement>(".form-msg")!;
    const isAlerts = f.matches(".alerts-form");
    if (isAlerts) {
      const email = f.elements.namedItem("email") as HTMLInputElement;
      if (!email.value || !email.validity.valid) {
        msg.className = "form-msg err";
        msg.textContent = t.alertsInvalid;
        email.setAttribute("aria-invalid", "true");
        email.focus();
        return;
      }
      email.removeAttribute("aria-invalid");
    } else if (!f.reportValidity()) {
      return;
    }
    const button = f.querySelector<HTMLButtonElement>('button[type="submit"]')!;
    const label = button.textContent;
    button.disabled = true;
    button.textContent = t.sending;
    msg.className = "form-msg";
    msg.textContent = "";
    try {
      const res = await fetch(f.action, { method: "POST", body: new FormData(f) });
      if (!res.ok) throw new Error(String(res.status));
      msg.className = "form-msg ok";
      msg.textContent = isAlerts ? t.alertsOk : t.reportSent;
      if (isAlerts) f.reset();
      else f.querySelectorAll("fieldset, label.field, button").forEach((el) => el.remove());
    } catch {
      msg.className = "form-msg err";
      msg.textContent = isAlerts ? t.alertsFailed : t.reportFailed;
    } finally {
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = label;
      }
    }
  });

  apply();
}
