import type { APIRoute } from "astro";
import { allJobs, countries, site as meta } from "../data";
import { href, LANGS, type Page } from "../i18n";

export const GET: APIRoute = ({ site }) => {
  const pages: [Page, string?][] = [
    ["home"],
    ["how"],
    ["sources"],
    ...countries.map((c): [Page, string] => ["country", c.code]),
    ...allJobs.map((j): [Page, string] => ["job", j.slug]),
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
