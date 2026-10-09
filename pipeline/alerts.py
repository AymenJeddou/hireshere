"""Daily email digest: new eligible/likely jobs per subscriber's country and field.

Subscribers live in Cloudflare D1 (written by site/functions/api/subscribe.js) and are read
through the D1 REST API. Mail goes out through Resend. Each subscriber gets the jobs first
seen since their last digest (or since signup), so a missed day is caught up, never doubled.
"""

import hashlib
import hmac
import html
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

import httpx

from pipeline import config
from pipeline.export import build

# ponytail: Resend free tier caps at 100 emails/day; leftovers go out next run. Paid tier lifts it.
DAILY_CAP = 95
MAX_JOBS = 20
FROM = f"{config.PRODUCT_NAME} <alerts@{config.DOMAIN}>"

T = {
    "en": {
        "subject": "{n} new remote jobs open to {country}",
        "subject1": "1 new remote job open to {country}",
        "intro": "New remote jobs open or likely open to candidates in {country}{field}, found since your last email.",
        "field": " in {field}",
        "eligible": "Eligible",
        "likely": "Likely",
        "more": "See all jobs for {country}",
        "foot": "Verdicts are automated estimates. Always confirm with the employer.",
        "unsub": "Unsubscribe",
    },
    "fr": {
        "subject": "{n} nouvelles offres en télétravail ouvertes {country_en}",
        "subject1": "1 nouvelle offre en télétravail ouverte {country_en}",
        "intro": "Nouvelles offres ouvertes ou probablement ouvertes aux candidats {country_en}{field}, depuis votre dernier e-mail.",
        "field": " en {field}",
        "eligible": "Éligible",
        "likely": "Probable",
        "more": "Voir toutes les offres pour {country}",
        "foot": "Les verdicts sont des estimations automatiques. Confirmez toujours auprès de l’employeur.",
        "unsub": "Se désinscrire",
    },
}
FIELDS = {
    "engineering": ("engineering", "ingénierie"), "data": ("data", "données"),
    "design": ("design", "design"), "product": ("product", "produit"),
    "marketing": ("marketing", "marketing"), "sales": ("sales", "vente"),
    "support": ("support", "support"), "ops": ("operations", "opérations"), "other": ("other", "autre"),
}  # fmt: skip


def unsubscribe_token(email: str, secret: str) -> str:
    """Must match site/functions/api/unsubscribe.js (HMAC-SHA256, hex)."""
    return hmac.new(secret.encode(), email.encode(), hashlib.sha256).hexdigest()


def pick(jobs: list[dict], first_seen: dict[str, str], since: str, family: str) -> list[dict]:
    """New eligible/likely jobs for one subscriber, eligible first, newest first."""
    hits = [
        j
        for j in jobs
        if j["verdict"] in ("eligible", "likely")
        and first_seen.get(j["id"], "") > since
        and (not family or j["family"] == family)
    ]
    hits.sort(key=lambda j: first_seen[j["id"]], reverse=True)
    hits.sort(key=lambda j: j["verdict"] != "eligible")
    return hits


def render(sub: dict, jobs: list[dict], unsub_url: str) -> tuple[str, str, str]:
    lang = sub["lang"] if sub["lang"] in T else "en"
    t, c = T[lang], config.COUNTRIES[sub["country"]]
    name = c["name"] if lang == "en" else c["name_fr"]
    field = FIELDS.get(sub["family"], ("", ""))[lang == "fr"]
    v = {"n": len(jobs), "country": name, "country_en": c.get("fr_en", name)}
    v["field"] = t["field"].format(field=field) if field else ""
    subject = t["subject1" if len(jobs) == 1 else "subject"].format(**v)
    page = f"https://{config.DOMAIN}{'/fr' if lang == 'fr' else ''}/{sub['country'].lower()}"
    shown = jobs[:MAX_JOBS]
    e = html.escape

    rows = "".join(
        f'<tr><td style="padding:14px 0;border-bottom:1px solid #dce2ea">'
        f'<a href="{e(j["url"])}" style="color:#14223a;font-weight:600;text-decoration:none">{e(j["title"])}</a>'
        f'<div style="color:#44546b;font-size:14px">{e(j["company"])}'
        f"{' · ' + e(j['scope']) if j['scope'] else ''}"
        f' · <strong style="color:{"#16794a" if j["verdict"] == "eligible" else "#9a5800"}">{t[j["verdict"]]}</strong></div>'
        f'<div style="color:#44546b;font-size:14px;margin-top:4px">{e(j["reason"][lang])}</div></td></tr>'
        for j in shown
    )
    body = (
        f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#14223a">'
        f'<p style="font-size:18px;font-weight:700;margin:0 0 12px">{config.PRODUCT_NAME}</p>'
        f'<p style="font-size:15px">{e(t["intro"].format(**v))}</p>'
        f'<table style="width:100%;border-collapse:collapse">{rows}</table>'
        f'<p><a href="{page}" style="color:#1d5bc7">{e(t["more"].format(**v))}</a></p>'
        f'<p style="color:#5f6e84;font-size:12px">{e(t["foot"])}<br>'
        f'<a href="{unsub_url}" style="color:#5f6e84">{t["unsub"]}</a></p></div>'
    )
    text = "\n\n".join(
        [t["intro"].format(**v)]
        + [
            f"{j['title']} - {j['company']} ({t[j['verdict']]})\n{j['reason'][lang]}\n{j['url']}"
            for j in shown
        ]
        + [f"{t['more'].format(**v)}: {page}", t["foot"], f"{t['unsub']}: {unsub_url}"]
    )
    return subject, body, text


def _d1(client: httpx.Client, sql: str, params: list | None = None) -> list[dict]:
    db_id = re.search(
        r'"database_id":\s*"([^"]+)"', Path("site/wrangler.jsonc").read_text("utf-8")
    )[1]
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}"
        f"/d1/database/{db_id}/query"
    )
    r = client.post(
        url,
        json={"sql": sql, "params": params or []},
        headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}"},
    )
    r.raise_for_status()
    return r.json()["result"][0]["results"]


def run(conn: sqlite3.Connection, dry_run: bool = False) -> str:
    secret = os.environ.get("UNSUBSCRIBE_SECRET") or ("preview" if dry_run else "")
    key = os.environ.get("RESEND_API_KEY")
    if not secret or (not key and not dry_run):
        return "Alerts skipped: RESEND_API_KEY or UNSUBSCRIBE_SECRET not set."
    per_country = build(conn)
    first_seen = dict(conn.execute("SELECT id, first_seen_at FROM jobs WHERE expired_at IS NULL"))
    sent = skipped = 0
    with httpx.Client(timeout=30) as client:
        subs = _d1(
            client,
            "SELECT email, country, family, lang, COALESCE(last_sent_at, created_at) AS since "
            "FROM subscribers ORDER BY since",
        )
        for sub in subs:
            jobs = pick(
                per_country.get(sub["country"], []), first_seen, sub["since"], sub["family"]
            )
            if not jobs:
                continue
            if sent >= DAILY_CAP:
                skipped += 1
                continue
            unsub = (
                f"https://{config.DOMAIN}/api/unsubscribe?e={quote(sub['email'])}"
                f"&t={unsubscribe_token(sub['email'], secret)}"
            )
            subject, body, text = render(sub, jobs, unsub)
            if dry_run:
                Path("alerts-preview.html").write_text(body, "utf-8")
                return f"Dry run: {len(subs)} subscribers, first digest: {subject!r} -> alerts-preview.html"
            r = client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "from": FROM,
                    "reply_to": config.CONTACT_EMAIL,
                    "to": [sub["email"]],
                    "subject": subject,
                    "html": body,
                    "text": text,
                    "headers": {
                        "List-Unsubscribe": f"<{unsub}>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    },
                },  # fmt: skip
            )
            if r.status_code >= 400:
                print(f"  send failed for a subscriber: HTTP {r.status_code} {r.text[:200]}")
                continue
            _d1(
                client,
                "UPDATE subscribers SET last_sent_at = ? WHERE email = ? AND country = ? AND family = ?",
                [
                    max(first_seen[j["id"]] for j in jobs),
                    sub["email"],
                    sub["country"],
                    sub["family"],
                ],
            )
            sent += 1
    return f"## Alerts\n\n{len(subs)} subscribers, {sent} digests sent, {skipped} held for the daily cap."
