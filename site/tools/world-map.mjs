// One-off: world map SVG for the site, one <path id="ISO2"> per country (Natural Earth 1:110m).
// Morocco and Western Sahara are drawn as one shape, so no border is shown between them.
import { readFileSync, writeFileSync } from "node:fs";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature, merge } from "topojson-client";

const topo = JSON.parse(readFileSync("node_modules/world-atlas/countries-110m.json", "utf8"));
const countries = JSON.parse(readFileSync(process.argv[2], "utf8"));
const byName = Object.fromEntries(Object.entries(countries).map(([c, v]) => [v.name, c]));
const ALIAS = {
  "United States of America": "US", "Dem. Rep. Congo": "CD", "Central African Rep.": "CF", "Bosnia and Herz.": "BA",
  "Dominican Rep.": "DO", "Eq. Guinea": "GQ", "S. Sudan": "SS", "W. Sahara": "MA", "Czechia": "CZ", "Côte d'Ivoire": "CI",
  "eSwatini": "SZ", "Macedonia": "MK", "North Macedonia": "MK", "Solomon Is.": "SB", "Falkland Is.": "FK", "N. Cyprus": "CY",
  "Somaliland": "SO", "Kosovo": "XK", "Taiwan": "TW", "Palestine": "PS", "Russia": "RU", "South Korea": "KR",
  "North Korea": "KP", "Laos": "LA", "Vietnam": "VN", "Syria": "SY", "Iran": "IR", "Tanzania": "TZ", "Bolivia": "BO",
  "Venezuela": "VE", "Moldova": "MD", "Brunei": "BN", "Timor-Leste": "TL", "Myanmar": "MM", "Congo": "CG",
  "Guinea-Bissau": "GW", "Greenland": "GL", "Puerto Rico": "PR", "New Caledonia": "NC", "Bahamas": "BS",
  "Gambia": "GM", "Trinidad and Tobago": "TT", "Turkey": "TR", "Türkiye": "TR",
};
const iso = (name) => (name in ALIAS ? ALIAS[name] : byName[name]);
const geoms = topo.objects.countries.geometries.filter((g) => g.properties.name !== "Antarctica" && g.properties.name !== "Fr. S. Antarctic Lands");
const groups = new Map();
for (const g of geoms) {
  const c = iso(g.properties.name);
  if (!c) { console.error("unmatched", g.properties.name); continue; }
  (groups.get(c) ?? groups.set(c, []).get(c)).push(g);
}
const W = 960, H = 470;
const all = feature(topo, { type: "GeometryCollection", geometries: geoms });
const proj = geoNaturalEarth1().fitSize([W, H], all);
const path = geoPath(proj);
const r = (d) => d.replace(/(\d+\.\d{2})\d+/g, "$1");
const paths = [...groups].map(([c, gs]) => `<path id="${c}" d="${r(path(merge(topo, gs)))}"><title>${countries[c].name}</title></path>`);
writeFileSync(process.argv[3], `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}">${paths.join("")}</svg>\n`);
console.log(groups.size, "countries");
