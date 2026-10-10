// One canonical address: www and the pages.dev preview host redirect to the apex domain.
// Old country boards (/tn, /fr/tn/engineering...) redirect to the search with the same filters.
import meta from "../src/data/meta.json";

const codes = Object.keys(meta.countries).map((c) => c.toLowerCase()).join("|");
const OLD = new RegExp(`^(/fr|/ar)?/(${codes})(?:/([a-z]+))?/?$`);

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  const canonical = meta.domain;
  if (url.hostname === `www.${canonical}` || url.hostname === "hireshere.pages.dev") {
    url.hostname = canonical;
    return Response.redirect(url.toString(), 301);
  }
  const old = url.pathname.match(OLD);
  if (old) {
    const [, prefix = "", code, field] = old;
    const to = new URL(`${prefix}/jobs`, url);
    to.searchParams.set("c", code.toUpperCase());
    if (field) to.searchParams.set("f", field);
    return Response.redirect(to.toString(), 301);
  }
  return next();
}
