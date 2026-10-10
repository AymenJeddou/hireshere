import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) =>
  new Response(`User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /shell/\n\nSitemap: ${new URL("/sitemap.xml", site)}\n`);
