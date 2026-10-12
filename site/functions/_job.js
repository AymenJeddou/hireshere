// Job pages (/jobs/<slug>, /fr/jobs/<slug>, /ar/jobs/<slug>), rendered per request so the
// deployment stays far under the 20,000-file limit. The static shell built by Astro brings the
// header, footer, CSS and scripts; the job comes from its detail shard.
import meta from "../src/data/meta.json";
import { jobMeta, jobPage } from "../src/scripts/jobpage.ts";

const SLUG = /^[a-z0-9-]{1,80}-[0-9a-f]{6}$/;
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const valid = (c) => (typeof c === "string" && c in meta.world ? c : "");

/** ?c= first, then the country picked on the site (cookie), then where Cloudflare sees them. */
function visitor(request, url) {
  const q = url.searchParams.get("c");
  if (q !== null) return valid(q.toUpperCase());
  const cookie = (request.headers.get("cookie") || "").match(/(?:^|;\s*)hh_country=([A-Z]{2})/);
  return valid(cookie?.[1]) || valid(request.cf?.country);
}

export function handler(lang) {
  return async ({ request, env, params }) => {
    const url = new URL(request.url);
    const asset = (path) => env.ASSETS.fetch(new URL(path, url));
    const slug = String(params.slug ?? "");
    let job = null;
    if (SLUG.test(slug)) {
      const shard = await asset(`/data/j/${slug.slice(-6, -4)}.json`);
      if (shard.ok) job = (await shard.json())[slug] ?? null;
    }
    if (!job) {
      // Closed (or never existed): 410 Gone with open jobs like it, picked in the browser.
      const page = await asset(`/closed/${lang}`);
      return new Response(page.body, { status: 410, headers: { "content-type": "text/html; charset=utf-8" } });
    }
    const code = visitor(request, url);
    const { title, description } = jobMeta(job, lang, code, meta);
    const shell = await (await asset(`/shell/${lang}`)).text();
    // Function replacers: job text may contain "$", which string replacements would interpret.
    const html = shell
      .replace(/<meta name="robots" content="noindex"\s*\/?>/, "")
      .replaceAll("__SLUG__", () => slug)
      .replaceAll("__TITLE__", () => esc(title))
      .replaceAll("__DESC__", () => esc(description))
      .replace('<div id="job-slot"></div>', () => jobPage(job, lang, code, meta));
    return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", vary: "Cookie" } });
  };
}
