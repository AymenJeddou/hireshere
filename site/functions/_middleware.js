// One canonical address: www and the pages.dev preview host redirect to the apex domain.
import meta from "../src/data/meta.json";

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  const canonical = meta.domain;
  if (url.hostname === `www.${canonical}` || url.hostname === "hireshere.pages.dev") {
    url.hostname = canonical;
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
