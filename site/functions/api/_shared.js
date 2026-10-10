// Shared validation for the two form endpoints. Runs on Cloudflare Pages Functions.
// Countries come from the pipeline's export (every country in data/countries.json).
import meta from "../../src/data/meta.json";

export const COUNTRIES = Object.keys(meta.world);
export const FAMILIES = ["", "engineering", "data", "design", "product", "marketing", "sales", "support", "ops", "other"];

export function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

export async function readForm(request) {
  const type = request.headers.get("content-type") || "";
  if (!type.includes("form")) return null;
  const form = await request.formData();
  return (key) => String(form.get(key) ?? "").trim();
}
