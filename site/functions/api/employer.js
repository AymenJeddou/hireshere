import { COUNTRIES, json, readForm } from "./_shared.js";

// Employers asking to be listed. Reviewed by hand before a board is added to data/boards.csv.
export async function onRequestPost({ request, env }) {
  const get = await readForm(request);
  if (!get) return json({ error: "bad request" }, 400);
  if (get("website")) return json({ ok: true }); // honeypot
  const company = get("company").slice(0, 120);
  const careers = get("careers").slice(0, 300);
  const email = get("email").toLowerCase().slice(0, 200);
  const countries = get.all("countries").filter((c) => COUNTRIES.includes(c));
  if (!company || !/^https?:\/\/\S+\.\S+/.test(careers) || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    return json({ error: "invalid" }, 422);
  }
  await env.DB.prepare(
    "INSERT INTO employer_leads (company, careers_url, countries, email, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
  )
    .bind(company, careers, countries.join(","), email, get("note").slice(0, 1000), new Date().toISOString())
    .run();
  return json({ ok: true });
}
