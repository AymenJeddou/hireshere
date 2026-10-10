import type { APIRoute } from "astro";
import { allJobs, countries, jobsFor, site as meta } from "../data";
import { href, labels, LANGS, type Page } from "../i18n";

export const GET: APIRoute = ({ site }) => {
  const pages: [Page, string?][] = [
    ["home"],
    ["how"],
    ["sources"],
    ...countries.map((c): [Page, string] => ["country", c.code]),
    ...allJobs.map((j): [Page, string] => ["job", j.slug]),
    ["companies"],
    ...[...new Set(allJobs.map((j) => j.company_key))].map((k): [Page, string] => ["company", k]),
    ...countries.flatMap((c) =>
      Object.keys(labels.family)
        .filter((f) => f !== "other" && jobsFor(c.code).some((j) => j.family === f && j.verdict !== "unclear"))
        .map((f): [Page, string] => ["field", `${c.code.toLowerCase()}/${f}`]),
    ),
  ];
  const lastmod = meta.updated.slice(0, 10);
  const urls = pages.flatMap(([p, c]) =>
    LANGS.map((l) => `<url><loc>${new URL(href(l, p, c), site)}</loc><lastmod>${lastmod}</lastmod></url>`),
  );
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.join("")}</urlset>\n`,
    { headers: { "Content-Type": "application/xml" } },
  );
};
