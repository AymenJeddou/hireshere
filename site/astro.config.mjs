import { readFileSync } from "node:fs";
import { defineConfig } from "astro/config";

// The domain lives in pipeline/config.py and reaches the site through the exported meta.json.
const meta = JSON.parse(readFileSync(new URL("./src/data/meta.json", import.meta.url), "utf-8"));

// Static output; Cloudflare Pages serves /dist and runs /functions.
export default defineConfig({
  site: `https://${meta.domain}`,
  trailingSlash: "never",
  build: { format: "file" },
});
