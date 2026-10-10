// One sentence for a card: which countries a job is open to, grouped by verdict.
// Shared by the build (JobCard.astro) and the browser (scripts/search.ts).
export type V = "eligible" | "likely" | "unclear";
const ORDER: V[] = ["eligible", "likely", "unclear"];

export interface LineText {
  label: Record<V, string>;
  names: Record<string, string>;
  inPlaces: string; // "{verdict} in {places}"
  inAll: string; // "{verdict} in all {n} countries"
}

const fill = (s: string, vars: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));

/** Groups for the countries in `scope` whose verdict is in `shown`, best verdict first. */
export function groups(vs: Record<string, V>, scope: string[], shown: V[]): { v: V; codes: string[] }[] {
  return ORDER.filter((v) => shown.includes(v))
    .map((v) => ({ v, codes: scope.filter((c) => vs[c] === v) }))
    .filter((g) => g.codes.length);
}

/** `all` is the number of countries when none is selected (0 when the visitor picked some):
 * "Eligible in all 4 countries" only makes sense for the whole region. */
export function groupText(g: { v: V; codes: string[] }, all: number, t: LineText): string {
  return all > 1 && g.codes.length === all
    ? fill(t.inAll, { verdict: t.label[g.v], n: all })
    : fill(t.inPlaces, { verdict: t.label[g.v], places: g.codes.map((c) => t.names[c]).join(", ") });
}
