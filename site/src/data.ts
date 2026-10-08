// Build-time access to the JSON written by `python -m pipeline.run export`.
import meta from "./data/meta.json";
import type { Lang, Verdict } from "./i18n";

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  seen: string;
  source: string;
  scope: string;
  family: string;
  seniority: string;
  engagement: string;
  languages: string[];
  confidence: "high" | "medium" | "low";
  quote: string;
  verdict: Verdict;
  reason: Record<Lang, string>;
}

export interface Country {
  code: string;
  name: string;
  name_fr: string;
  fr_le: string;
  fr_en: string;
  counts: Partial<Record<Verdict, number>>;
}

const files = import.meta.glob<{ default: Job[] }>("./data/[a-z][a-z].json", { eager: true });

export const site = meta;

export const countries: Country[] = Object.entries(meta.countries).map(([code, c]) => ({
  code,
  ...(c as Omit<Country, "code">),
}));

export function jobsFor(code: string): Job[] {
  return files[`./data/${code.toLowerCase()}.json`]?.default ?? [];
}

export function countryName(c: Country, lang: Lang): string {
  return lang === "fr" ? c.name_fr : c.name;
}

export function openCount(c: Country): number {
  return (c.counts.eligible ?? 0) + (c.counts.likely ?? 0);
}

export function totalBoards(): number {
  return Object.values(meta.boards).reduce((a, b) => a + (b as number), 0);
}
