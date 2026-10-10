// Build-time access to the JSON written by `python -m pipeline.run export`.
import jobsIndex from "./data/jobs.json";
import meta from "./data/meta.json";
import { type Lang, LOCALE, type Verdict } from "./i18n";

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
  seen_at: string;
  slug: string;
  company_key: string;
  website: string;
  salary: [number | null, number | null, string | null] | null;
  tz: [number | null, number | null, string | null] | null;
  department: string;
  contract: string;
  workplace: string;
  named: string[];
}

/** One record per job with every country's verdict (jobs.json). */
export interface JobRecord extends Omit<Job, "verdict" | "reason"> {
  verdicts: Record<string, { v: Verdict; reason: Record<Lang, string> }>;
}

export interface Country {
  code: string;
  name: string;
  name_fr: string;
  name_ar: string;
  fr_le: string;
  fr_en: string;
  utc_offset: number;
  counts: Partial<Record<Verdict, number>>;
}

const files = import.meta.glob<{ default: Job[] }>("./data/[a-z][a-z].json", { eager: true });

export const site = meta;

// Where jobs come from. Remote OK's API terms: name them and link back to their job page.
export const SOURCES: Record<string, { name: string; url: string }> = {
  greenhouse: { name: "Greenhouse", url: "https://www.greenhouse.com" },
  lever: { name: "Lever", url: "https://www.lever.co" },
  ashby: { name: "Ashby", url: "https://www.ashbyhq.com" },
  smartrecruiters: { name: "SmartRecruiters", url: "https://www.smartrecruiters.com" },
  workable: { name: "Workable", url: "https://www.workable.com" },
  recruitee: { name: "Recruitee", url: "https://recruitee.com" },
  teamtailor: { name: "Teamtailor", url: "https://www.teamtailor.com" },
  remoteok: { name: "Remote OK", url: "https://remoteok.com" },
};

export const countries: Country[] = Object.entries(meta.countries).map(([code, c]) => ({
  code,
  ...(c as Omit<Country, "code">),
}));

export function jobsFor(code: string): Job[] {
  return files[`./data/${code.toLowerCase()}.json`]?.default ?? [];
}

export const allJobs = jobsIndex as JobRecord[];

export function companyJobs(key: string): JobRecord[] {
  return allJobs.filter((j) => j.company_key === key);
}

/** First seen in the last 36 hours before this build: "new today" for a daily site. */
export function isNew(seenAt: string): boolean {
  return Date.parse(site.updated) - Date.parse(seenAt) < 36 * 3600 * 1000;
}

export function salaryText(s: Job["salary"], lang: Lang): string {
  if (!s) return "";
  const [lo, hi, cur] = s;
  const fmt = (n: number) =>
    new Intl.NumberFormat(lang === "en" ? "en-US" : LOCALE[lang], {
      style: cur ? "currency" : "decimal",
      currency: cur ?? undefined,
      maximumFractionDigits: 0,
      notation: n >= 10000 ? "compact" : "standard",
    }).format(n);
  if (lo && hi && lo !== hi) return `${fmt(lo)} – ${fmt(hi)}`;
  return fmt((lo ?? hi) as number);
}

/** Does the posting's time-zone window include the country's offset? null when unknown. */
export function tzFits(tz: Job["tz"], code: string): boolean | null {
  if (!tz || (tz[0] == null && tz[1] == null)) return null;
  const off = countries.find((c) => c.code === code)?.utc_offset ?? 0;
  return (tz[0] ?? -12) <= off && off <= (tz[1] ?? 14);
}

export function countryName(c: Country, lang: Lang): string {
  return { en: c.name, fr: c.name_fr, ar: c.name_ar }[lang];
}

export function openCount(c: Country): number {
  return (c.counts.eligible ?? 0) + (c.counts.likely ?? 0);
}

export function totalBoards(): number {
  return Object.values(meta.boards).reduce((a, b) => a + (b as number), 0);
}
