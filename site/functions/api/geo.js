import { json } from "./_shared.js";

// The visitor's country as Cloudflare sees it (two-letter code, "" when unknown).
export function onRequestGet({ request }) {
  const c = request.cf?.country;
  return json({ country: typeof c === "string" && /^[A-Z]{2}$/.test(c) ? c : "" });
}
