import { COUNTRIES, FAMILIES, json, readForm } from "./_shared.js";

const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/;

export async function onRequestPost({ request, env }) {
  const get = await readForm(request);
  if (!get) return json({ error: "bad request" }, 400);
  if (get("website")) return json({ ok: true }); // honeypot: quietly drop bots
  const email = get("email").toLowerCase();
  const country = get("country");
  const family = get("family");
  const lang = ["fr", "ar"].includes(get("lang")) ? get("lang") : "en";
  if (!EMAIL.test(email) || !COUNTRIES.includes(country) || !FAMILIES.includes(family)) {
    return json({ error: "invalid" }, 422);
  }
  await env.DB.prepare(
    "INSERT OR IGNORE INTO subscribers (email, country, family, lang, created_at) VALUES (?, ?, ?, ?, ?)",
  )
    .bind(email, country, family, lang, new Date().toISOString())
    .run();
  return json({ ok: true });
}
