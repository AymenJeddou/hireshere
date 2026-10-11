// Build-time access to the JSON written by `python -m pipeline.run export`.
// Job cards and job pages are rendered from the search index and detail shards in
// public/data; the build only uses the English index for lists, counts and the sitemap.
import index from "../public/data/search-en.json";
import companiesIndex from "./data/companies.json";
import meta from "./data/meta.json";
import { type Lang, LOCALE } from "./i18n";
import type { SJob } from "./scripts/cards";

export { SOURCES } from "./scripts/cards";

export const site = meta;
export const jobs = index as unknown as SJob[];

export interface Country {
  code: string;
  name: string;
  name_fr: string;
  name_ar: string;
}

/** Featured countries: getting-paid guide, Telegram channels. */
export const countries: Country[] = Object.entries(meta.countries).map(([code, c]) => ({
  code,
  name: c.name,
  name_fr: c.name_fr,
  name_ar: c.name_ar,
}));

/** Every country a visitor can pick, sorted by its name in `lang`. */
export function world(lang: Lang): { code: string; name: string }[] {
  const sort = new Intl.Collator(LOCALE[lang]).compare;
  return Object.entries(meta.world)
    .map(([code, c]) => ({ code, name: countryName(c, lang) }))
    .sort((a, b) => sort(a.name, b.name));
}

export function countryName(c: Omit<Country, "code">, lang: Lang): string {
  return { en: c.name, fr: c.name_fr, ar: c.name_ar }[lang];
}

/** Company pages: name, website, number of jobs, countries named in their postings. */
export const companies = companiesIndex as Record<string, { name: string; website: string; n: number; entry: number; named: string[] }>;

export function companyJobs(key: string): SJob[] {
  return jobs.filter((j) => j.company_key === key);
}

export const companyKeys = () => [...new Set(jobs.map((j) => j.company_key))];

export function totalBoards(): number {
  return Object.values(meta.boards).reduce((a, b) => a + (b as number), 0);
}
