// The visitor's country: ?c= in the URL, else their last choice (localStorage, mirrored in a
// cookie so job pages rendered by a Function can read it), else where Cloudflare sees them.
const KEY = "hh_country";

export function remember(code: string): void {
  try {
    localStorage.setItem(KEY, code);
  } catch {
    // Storage blocked: the choice lasts for this page only.
  }
  document.cookie = `${KEY}=${code}; path=/; max-age=31536000; samesite=lax`;
}

/** "" means all countries. `valid` keeps unknown codes out. */
export async function visitorCountry(valid: (code: string) => boolean): Promise<string> {
  const check = (c: string | null) => (c && valid(c) ? c : "");
  const url = new URLSearchParams(location.search).get("c");
  if (url !== null) return check(url.split(",")[0].toUpperCase());
  try {
    const saved = localStorage.getItem(KEY);
    if (saved !== null) return check(saved);
    const seen = sessionStorage.getItem("hh_geo");
    if (seen !== null) return check(seen);
  } catch {
    // Storage blocked: ask the server every time.
  }
  try {
    const { country } = await fetch("/api/geo").then((r) => r.json());
    sessionStorage.setItem("hh_geo", country ?? "");
    return check(country);
  } catch {
    return "";
  }
}
