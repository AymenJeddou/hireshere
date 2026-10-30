// Shared validation for the two form endpoints. Runs on Cloudflare Pages Functions.
// Countries come from the pipeline's export (every country in data/countries.json).
import meta from "../../src/data/meta.json";

export const COUNTRIES = Object.keys(meta.world);
export const FAMILIES = ["", "engineering", "data", "design", "product", "marketing", "sales", "support", "ops", "other"];

export function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", "x-content-type-options": "nosniff" },
  });
}

export async function readForm(request) {
  const type = request.headers.get("content-type") || "";
  if (!type.includes("form")) return null;
  let form;
  try {
    form = await request.formData();
  } catch {
    return null; // malformed body: a 400, not an uncaught 500
  }
  const get = (key) => String(form.get(key) ?? "").trim();
  get.all = (key) => form.getAll(key).map(String);
  return get;
}
