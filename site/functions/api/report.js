import { COUNTRIES, json, readForm } from "./_shared.js";

const KINDS = ["wrong_verdict", "closed", "other"];

export async function onRequestPost({ request, env }) {
  const get = await readForm(request);
  if (!get) return json({ error: "bad request" }, 400);
  const job = get("job");
  const country = get("country");
  const kind = get("kind");
  if (!job || job.length > 200 || !COUNTRIES.includes(country) || !KINDS.includes(kind)) {
    return json({ error: "invalid" }, 422);
  }
  await env.DB.prepare(
    "INSERT INTO reports (job_id, country, verdict, kind, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
  )
    .bind(job, country, get("verdict").slice(0, 20), kind, get("note").slice(0, 500), new Date().toISOString())
    .run();
  return json({ ok: true });
}
