import type { APIRoute } from "astro";
import { allJobs } from "../data";

// Minimal lookup for the "My jobs" page: saved ids live in the browser, details come from here.
export const GET: APIRoute = () =>
  new Response(
    JSON.stringify(Object.fromEntries(allJobs.map((j) => [j.id, [j.slug, j.title, j.company, j.url]]))),
    { headers: { "Content-Type": "application/json" } },
  );
