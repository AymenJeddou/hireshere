// Welcome email for a new alert subscriber, sent once from the sign-up Function via Resend.
// The unsubscribe token matches pipeline/alerts.py and api/unsubscribe.js (HMAC-SHA256, hex).
import meta from "../../src/data/meta.json";

const FIELDS = {
  engineering: ["engineering", "ingénierie", "الهندسة والتطوير"], data: ["data", "données", "البيانات"],
  design: ["design", "design", "التصميم"], product: ["product", "produit", "إدارة المنتج"],
  marketing: ["marketing", "marketing", "التسويق"], sales: ["sales", "vente", "المبيعات"],
  support: ["support", "support", "الدعم"], ops: ["operations", "opérations", "العمليات"],
  other: ["other", "autre", "أخرى"],
};
const LANGS = ["en", "fr", "ar"];

const T = {
  en: {
    subject: "You're subscribed: remote jobs open to {country}",
    hello: "Thanks for subscribing to HiresHere alerts.",
    what: "Once a day, when new remote jobs{field} open to people in {country} appear, we send you one email with them, each with the sentence from the posting that proves you can apply. No new jobs, no email.",
    now: "See the jobs open to {country} now",
    field: " in {field}",
    foot: "You get this email because you signed up on hireshere.app.",
    unsub: "Unsubscribe",
  },
  fr: {
    subject: "Inscription confirmée : alertes HiresHere, pays : {country}",
    hello: "Merci de vous être inscrit aux alertes HiresHere.",
    what: "Une fois par jour, quand de nouvelles offres en télétravail{field} sont ouvertes aux personnes qui vivent dans votre pays ({country}), nous vous les envoyons dans un seul e-mail, chacune avec la phrase de l’annonce qui le prouve. Pas de nouvelle offre, pas d’e-mail.",
    now: "Voir les offres ouvertes : {country}",
    field: " (domaine : {field})",
    foot: "Vous recevez cet e-mail parce que vous vous êtes inscrit sur hireshere.app.",
    unsub: "Se désinscrire",
  },
  ar: {
    subject: "تم اشتراكك: وظائف عن بعد مفتوحة في {country}",
    hello: "شكرًا لاشتراكك في تنبيهات HiresHere.",
    what: "مرة واحدة في اليوم، عند ظهور وظائف جديدة عن بعد{field} مفتوحة للمقيمين في {country}، نرسلها إليك في رسالة واحدة، مع الجملة من الإعلان التي تثبت أنه يمكنك التقديم. إن لم توجد وظائف جديدة فلن نرسل شيئًا.",
    now: "عرض الوظائف المفتوحة في {country} الآن",
    field: " في مجال {field}",
    foot: "تصلك هذه الرسالة لأنك اشتركت في hireshere.app.",
    unsub: "إلغاء الاشتراك",
  },
};

const fill = (s, v) => s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? "");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

export async function token(email, secret) {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(email)));
  return [...sig].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** {subject, html, text} for one new subscriber. Pure apart from the token. */
export function render({ email, country, family, lang }, unsubUrl) {
  const t = T[lang] ?? T.en;
  const c = meta.world[country] ?? { name: country, name_fr: country, name_ar: country };
  const name = { en: c.name, fr: c.name_fr, ar: c.name_ar }[lang] ?? c.name;
  const f = FIELDS[family]?.[LANGS.indexOf(lang)] ?? "";
  const v = { country: name, field: f ? fill(t.field, { field: f }) : "" };
  const page = `https://${meta.domain}${lang === "en" ? "" : "/" + lang}/jobs?c=${country}`;
  const html =
    `<div dir="${lang === "ar" ? "rtl" : "ltr"}" style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#14223a">` +
    `<p style="font-size:18px;font-weight:700;margin:0 0 12px">HiresHere</p>` +
    `<p style="font-size:15px">${esc(t.hello)}</p>` +
    `<p style="font-size:15px">${esc(fill(t.what, v))}</p>` +
    `<p><a href="${page}" style="display:inline-block;background:#0b3a53;color:#fff;padding:12px 20px;border-radius:999px;text-decoration:none;font-weight:600">${esc(fill(t.now, v))}</a></p>` +
    `<p style="color:#5f6e84;font-size:12px">${esc(t.foot)}<br><a href="${unsubUrl}" style="color:#5f6e84">${t.unsub}</a></p></div>`;
  const text = [t.hello, fill(t.what, v), `${fill(t.now, v)}: ${page}`, t.foot, `${t.unsub}: ${unsubUrl}`].join("\n\n");
  return { subject: fill(t.subject, v), html, text };
}

/** Send it. Never throws: a failed welcome must not break the sign-up. */
export async function sendWelcome(env, sub) {
  if (!env.RESEND_API_KEY || !env.UNSUBSCRIBE_SECRET) return;
  try {
    const unsub = `https://${meta.domain}/api/unsubscribe?e=${encodeURIComponent(sub.email)}&t=${await token(sub.email, env.UNSUBSCRIBE_SECRET)}`;
    const { subject, html, text } = render(sub, unsub);
    await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
      body: JSON.stringify({
        from: `HiresHere <alerts@${meta.domain}>`,
        reply_to: `contact@${meta.domain}`,
        to: [sub.email],
        subject,
        html,
        text,
        headers: { "List-Unsubscribe": `<${unsub}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" },
      }),
    });
  } catch {
    // the subscriber is saved; the welcome is a courtesy
  }
}
