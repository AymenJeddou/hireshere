// Every interface string exists in en, fr and ar with the same {placeholders}.
//   npm run check:i18n   (Node 22.13+)
import { readFileSync } from "node:fs";

// French drops {country} here on purpose: "à la Tunisie / au Maroc / aux Émirats" can't be one template.
const ALLOWED = new Set(["fr alerts_body"]);

// i18n.ts imports "./i18n-ar" without an extension, which Node can't resolve, so load both by hand.
const load = async (file) =>
  import("data:text/javascript;base64," + Buffer.from(
    (await import("node:module")).stripTypeScriptTypes(readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8"))
      .replace(/import \{ ar \} from "\.\/i18n-ar";/, ""),
  ).toString("base64"));

const { ar } = await load("i18n-ar.ts");
globalThis.ar = ar;
const { strings } = await load("i18n.ts");

const holes = (s) => [...String(s).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
const problems = [];
for (const lang of ["fr", "ar"]) {
  const t = strings[lang];
  for (const k of Object.keys(strings.en)) {
    if (!(k in t)) problems.push(`${lang} missing ${k}`);
    else if (holes(strings.en[k]) !== holes(t[k]) && !ALLOWED.has(`${lang} ${k}`))
      problems.push(`${lang} ${k}: {${holes(strings.en[k])}} vs {${holes(t[k])}}`);
  }
  for (const k of Object.keys(t)) if (!(k in strings.en)) problems.push(`${lang} extra ${k}`);
}
if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`i18n ok: ${Object.keys(strings.en).length} strings in en, fr, ar`);
