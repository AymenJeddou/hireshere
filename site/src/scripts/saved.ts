// Saved jobs and application status, kept in this browser only (localStorage).
export type Status = "saved" | "applied" | "interview" | "offer" | "rejected";
type Store = Record<string, { status: Status; t: number }>;
const KEY = "hh_saved";

export function load(): Store {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

export function save(store: Store): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
  } catch {
    // Private mode or storage blocked: saving silently does nothing.
  }
}

function paint(btn: HTMLElement, on: boolean): void {
  btn.setAttribute("aria-pressed", String(on));
  const label = btn.querySelector<HTMLElement>("[data-save-label]");
  if (label) label.textContent = (on ? label.dataset.on : label.dataset.off) ?? "";
}

/** Wire every [data-save="<job id>"] button on the page. */
export function initSaveButtons(root: ParentNode = document): void {
  const store = load();
  root.querySelectorAll<HTMLElement>("[data-save]").forEach((btn) => {
    const id = btn.dataset.save!;
    paint(btn, id in store);
    btn.addEventListener("click", () => {
      const s = load();
      if (id in s) delete s[id];
      else s[id] = { status: "saved", t: Date.now() };
      save(s);
      paint(btn, id in s);
    });
  });
}
