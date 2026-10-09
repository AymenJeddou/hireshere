// All interface copy, English first, French second ("vous").
export type Lang = "en" | "fr";
export const LANGS: Lang[] = ["en", "fr"];

export type Page = "home" | "country" | "how" | "sources";

const SLUGS: Record<Page, Record<Lang, string>> = {
  home: { en: "/", fr: "/fr" },
  country: { en: "/", fr: "/fr/" },
  how: { en: "/how-it-works", fr: "/fr/comment-ca-marche" },
  sources: { en: "/sources", fr: "/fr/sources" },
};

export function href(lang: Lang, page: Page, country?: string): string {
  if (page === "country") return SLUGS.country[lang] + (country ?? "").toLowerCase();
  return SLUGS[page][lang];
}

export const VERDICTS = ["eligible", "likely", "unclear"] as const;
export type Verdict = (typeof VERDICTS)[number];

export const labels = {
  verdict: {
    eligible: { en: "Eligible", fr: "Éligible" },
    likely: { en: "Likely", fr: "Probable" },
    unclear: { en: "Unclear", fr: "Incertain" },
  },
  verdictHelp: {
    eligible: {
      en: "The posting says this role is open to your country or to anyone, anywhere.",
      fr: "L'annonce indique que ce poste est ouvert à votre pays ou à tout le monde.",
    },
    likely: {
      en: "Open to a region or time zone that includes your country. Worth applying; confirm with the employer.",
      fr: "Ouvert à une région ou un fuseau horaire qui inclut votre pays. À tenter ; confirmez auprès de l'employeur.",
    },
    unclear: {
      en: "Remote, but the posting does not say where candidates may live. Ask before you invest time.",
      fr: "Télétravail, mais l'annonce ne dit pas d'où les candidats peuvent travailler. Renseignez-vous avant d'investir du temps.",
    },
  },
  family: {
    engineering: { en: "Engineering", fr: "Ingénierie" },
    data: { en: "Data", fr: "Données" },
    design: { en: "Design", fr: "Design" },
    product: { en: "Product", fr: "Produit" },
    marketing: { en: "Marketing", fr: "Marketing" },
    sales: { en: "Sales", fr: "Vente" },
    support: { en: "Support", fr: "Support" },
    ops: { en: "Operations", fr: "Opérations" },
    other: { en: "Other", fr: "Autre" },
  },
  seniority: {
    intern: { en: "Intern", fr: "Stage" },
    junior: { en: "Junior", fr: "Junior" },
    mid: { en: "Mid-level", fr: "Confirmé" },
    senior: { en: "Senior", fr: "Senior" },
    lead: { en: "Lead", fr: "Lead" },
    unclear: { en: "Level not stated", fr: "Niveau non précisé" },
  },
  engagement: {
    employee: { en: "Employee", fr: "Salarié" },
    contractor: { en: "Contractor", fr: "Freelance" },
    either: { en: "Employee or contractor", fr: "Salarié ou freelance" },
    unclear: { en: "Contract not stated", fr: "Contrat non précisé" },
  },
} as const;

export function languageName(code: string, lang: Lang): string {
  try {
    const n = new Intl.DisplayNames([lang], { type: "language" }).of(code);
    return n ? n.charAt(0).toUpperCase() + n.slice(1) : code;
  } catch {
    return code;
  }
}

export function formatDate(iso: string, lang: Lang, withYear = false): string {
  return new Intl.DateTimeFormat(lang === "fr" ? "fr-FR" : "en-GB", {
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    timeZone: "UTC",
  }).format(new Date(iso));
}

const en = {
  skip: "Skip to content",
  nav_how: "How it works",
  nav_sources: "Sources",
  nav_countries: "Countries",
  switch_lang: "Français",
  switch_lang_short: "FR",
  footer_disclaimer:
    "Verdicts are automated estimates made by reading each posting. Always confirm eligibility with the employer before you apply.",
  footer_data: "Jobs come straight from company hiring pages and refresh daily.",
  updated: "Updated",

  home_title: "Remote jobs you can actually get from North Africa",
  home_lede:
    "Most “remote” jobs only hire in the US or Europe. We check every posting and show you the ones open to your country, with the sentence that proves it.",
  home_fresh: "{jobs} jobs checked at {companies} companies · updated {date}",
  home_proof: "A real verdict from today’s board for {country}",
  home_pick: "Choose your country",
  home_open: "{n} jobs open or likely open",
  eligible_n: "eligible",
  likely_n: "likely",
  alerts_prompt: "Get new {country} jobs by email",
  home_sample: "What a verdict looks like",
  home_sample_note: "One real posting per verdict, from today’s board for {country}.",
  home_see_all: "See all {n} jobs for {country}",
  home_how_title: "How a job gets on your board",
  home_how_1_t: "Straight from the source",
  home_how_1:
    "We read public job feeds from companies’ own hiring systems every day. Jobs that disappear are removed the same day.",
  home_how_2_t: "Read for eligibility",
  home_how_2:
    "Each posting is read for who may apply: countries, regions, time zones, work permits, contract type and language.",
  home_how_3_t: "Shown with its evidence",
  home_how_3:
    "You see a verdict for your country and the exact sentence it rests on, so you can judge it yourself.",
  home_more: "Read the full method",

  country_title: "Remote jobs open to people in {country}",
  country_meta_title: "Remote jobs open to {country} | {product}",
  country_sub: "{open} jobs open or likely open to {country}, plus {unclear} unclear, from {companies} companies. Updated {date}.",
  country_note: "Verdicts are automated estimates. Always confirm with the employer.",
  country_note_link: "How verdicts work",
  filter_verdict: "Show",
  filter_search: "Search title or company",
  filter_search_ph: "e.g. backend, design, Canonical",
  filter_family: "Role",
  filter_seniority: "Level",
  filter_language: "Language",
  filter_engagement: "Contract",
  filter_any: "Any",
  filter_reset: "Reset filters",
  filters: "Filters",
  filters_active: "Filters ({n})",
  results_count: "Showing {shown} of {total} jobs",
  results_none_title: "No jobs match these filters",
  results_none_q: "No jobs match “{q}”",
  results_none: "Try fewer filters or a shorter search.",
  show_unclear: "Show {n} unclear jobs",
  unclear_hidden: "Unclear jobs hidden.",
  more: "Show {n} more",
  first_seen: "First seen {date}",
  apply: "Apply on company site",
  apply_sr: "(opens the original posting in a new tab)",
  quote_missing: "No exact sentence to quote. The verdict rests on the location field: {location}.",
  quote_label: "From the posting",
  report: "Report an error",
  report_q: "What is wrong?",
  report_wrong: "The verdict is wrong for my country",
  report_closed: "The job is closed or the link is broken",
  report_info: "Other details are wrong",
  report_note: "Anything we should know? (optional)",
  report_send: "Send report",
  report_sent: "Thank you. We review every report.",
  report_failed: "We couldn’t send your report. Please try again later.",
  legend_title: "What the verdicts mean",
  alerts_title: "Get new jobs by email",
  alerts_body: "One email when new jobs open to {country} appear in your field. Nothing else.",
  alerts_email: "Email address",
  alerts_family: "Field",
  alerts_all: "All fields",
  alerts_submit: "Sign me up",
  alerts_ok: "You’re on the list. We’ll email you when new jobs open to you appear.",
  alerts_failed: "We couldn’t save your email. Please try again later.",
  alerts_invalid: "Please enter a valid email address.",
  alerts_privacy: "We keep only your email, country and field. Unsubscribe from any email.",
  sending: "Sending…",
  confidence_low: "Low confidence",

  how_title: "How it works",
  sources_title: "Sources",
};

const fr: typeof en = {
  skip: "Aller au contenu",
  nav_how: "Comment ça marche",
  nav_sources: "Sources",
  nav_countries: "Pays",
  switch_lang: "English",
  switch_lang_short: "EN",
  footer_disclaimer:
    "Les verdicts sont des estimations automatiques fondées sur la lecture de chaque annonce. Vérifiez toujours votre éligibilité auprès de l’employeur avant de postuler.",
  footer_data: "Les offres viennent directement des pages carrières des entreprises et sont mises à jour chaque jour.",
  updated: "Mis à jour",

  home_title: "Des offres en télétravail vraiment ouvertes depuis l’Afrique du Nord",
  home_lede:
    "La plupart des offres « remote » ne recrutent qu’aux États-Unis ou en Europe. Nous vérifions chaque annonce et vous montrons celles ouvertes à votre pays, avec la phrase qui le prouve.",
  home_fresh: "{jobs} offres vérifiées dans {companies} entreprises · mis à jour le {date}",
  home_proof: "Un vrai verdict du tableau du jour pour {country}",
  home_pick: "Choisissez votre pays",
  home_open: "{n} offres ouvertes ou probablement ouvertes",
  eligible_n: "éligibles",
  likely_n: "probables",
  alerts_prompt: "Recevoir les nouvelles offres par e-mail",
  home_sample: "À quoi ressemble un verdict",
  home_sample_note: "Une vraie annonce par verdict, tirée du tableau du jour pour {country}.",
  home_see_all: "Voir les {n} offres pour {country}",
  home_how_title: "Comment une offre arrive sur votre tableau",
  home_how_1_t: "À la source",
  home_how_1:
    "Nous lisons chaque jour les flux publics des systèmes de recrutement des entreprises. Les offres retirées disparaissent le jour même.",
  home_how_2_t: "Lue pour l’éligibilité",
  home_how_2:
    "Chaque annonce est lue pour savoir qui peut postuler : pays, régions, fuseaux horaires, permis de travail, type de contrat et langue.",
  home_how_3_t: "Affichée avec sa preuve",
  home_how_3:
    "Vous voyez un verdict pour votre pays et la phrase exacte sur laquelle il repose, pour juger par vous-même.",
  home_more: "Lire la méthode complète",

  country_title: "Offres en télétravail ouvertes aux candidats {country_en}",
  country_meta_title: "Télétravail ouvert aux candidats {country_en} | {product}",
  country_sub: "{open} offres ouvertes ou probablement ouvertes {country_en}, plus {unclear} incertaines, de {companies} entreprises. Mis à jour le {date}.",
  country_note: "Les verdicts sont des estimations automatiques. Confirmez toujours auprès de l’employeur.",
  country_note_link: "Comment sont établis les verdicts",
  filter_verdict: "Afficher",
  filter_search: "Rechercher un poste ou une entreprise",
  filter_search_ph: "ex. backend, design, Canonical",
  filter_family: "Métier",
  filter_seniority: "Niveau",
  filter_language: "Langue",
  filter_engagement: "Contrat",
  filter_any: "Tous",
  filter_reset: "Réinitialiser",
  filters: "Filtres",
  filters_active: "Filtres ({n})",
  results_count: "{shown} offres affichées sur {total}",
  results_none_title: "Aucune offre ne correspond à ces filtres",
  results_none_q: "Aucune offre pour « {q} »",
  results_none: "Essayez moins de filtres ou une recherche plus courte.",
  show_unclear: "Afficher {n} offres incertaines",
  unclear_hidden: "Offres incertaines masquées.",
  more: "Afficher {n} de plus",
  first_seen: "Vue le {date}",
  apply: "Postuler sur le site de l’entreprise",
  apply_sr: "(ouvre l’annonce d’origine dans un nouvel onglet)",
  quote_missing: "Pas de phrase exacte à citer. Le verdict repose sur le champ de localisation : {location}.",
  quote_label: "Extrait de l’annonce",
  report: "Signaler une erreur",
  report_q: "Qu’est-ce qui ne va pas ?",
  report_wrong: "Le verdict est faux pour mon pays",
  report_closed: "L’offre est close ou le lien ne marche pas",
  report_info: "D’autres informations sont fausses",
  report_note: "Une précision ? (facultatif)",
  report_send: "Envoyer",
  report_sent: "Merci. Nous examinons chaque signalement.",
  report_failed: "Impossible d’envoyer le signalement. Réessayez plus tard.",
  legend_title: "Ce que signifient les verdicts",
  alerts_title: "Recevez les nouvelles offres par e-mail",
  alerts_body: "Un e-mail quand de nouvelles offres ouvertes aux candidats {country_en} apparaissent dans votre domaine. Rien d’autre.",
  alerts_email: "Adresse e-mail",
  alerts_family: "Domaine",
  alerts_all: "Tous les domaines",
  alerts_submit: "Je m’inscris",
  alerts_ok: "C’est noté. Nous vous écrirons dès que de nouvelles offres ouvertes à vous apparaîtront.",
  alerts_failed: "Impossible d’enregistrer votre e-mail. Réessayez plus tard.",
  alerts_invalid: "Veuillez saisir une adresse e-mail valide.",
  alerts_privacy: "Nous ne gardons que votre e-mail, votre pays et votre domaine. Désinscription depuis chaque e-mail.",
  sending: "Envoi…",
  confidence_low: "Confiance faible",

  how_title: "Comment ça marche",
  sources_title: "Sources",
};

export const strings = { en, fr };
export type Key = keyof typeof en;

export function tr(lang: Lang, key: Key, vars: Record<string, string | number> = {}): string {
  return strings[lang][key].replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}
