"""Post new eligible/likely jobs to one Telegram channel per featured country (config.COUNTRIES).

Config (env): TELEGRAM_BOT_TOKEN, and TELEGRAM_CHANNELS such as
"TN=@hireshere_tn:fr,EG=@hireshere_eg:ar" (country=channel[:lang], lang defaults to en).
The bot must be an admin of each channel.
Posted jobs are recorded in jobs.db so nothing is posted twice. A channel's first run posts only
the newest few jobs and marks the rest as seen, so a new channel is not flooded.
"""

import html
import os
import sqlite3
import time

import httpx

from pipeline import config
from pipeline.alerts import T
from pipeline.export import build, country_view

PER_RUN = 15  # ponytail: fixed cap per channel per run; Telegram allows ~20 posts/min per channel
FIRST_RUN = 5


def channels(spec: str) -> dict[str, tuple[str, str]]:
    """Parse "TN=@a:fr,EG=@b" into {"TN": ("@a", "fr"), "EG": ("@b", "en")}."""
    out = {}
    for part in filter(None, (p.strip() for p in spec.split(","))):
        code, _, rest = part.partition("=")
        chat, _, lang = rest.partition(":")
        if code.upper() in config.COUNTRIES and chat:
            out[code.upper()] = (chat, lang if lang in T else "en")
    return out


def message(job: dict, lang: str) -> str:
    e = html.escape
    t = T[lang]
    prefix = "" if lang == "en" else f"/{lang}"
    lamp = "🟢" if job["verdict"] == "eligible" else "🟠"
    lines = [
        f"<b>{e(job['title'])}</b>",
        e(job["company"]) + (f" · {e(job['scope'])}" if job["scope"] else ""),
        f"{lamp} {t[job['verdict']]}: {e(job['reason'][lang])}",
        f"https://{config.DOMAIN}{prefix}/jobs/{job['slug']}",
    ]
    return "\n".join(lines)


def run(conn: sqlite3.Connection) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    targets = channels(os.environ.get("TELEGRAM_CHANNELS", ""))
    if not token or not targets:
        return "Telegram skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNELS not set."
    conn.execute(
        "CREATE TABLE IF NOT EXISTS telegram_posts (job_id TEXT, channel TEXT, posted_at TEXT,"
        " PRIMARY KEY (job_id, channel))"
    )
    jobs = build(conn)
    first_seen = dict(conn.execute("SELECT id, first_seen_at FROM jobs WHERE expired_at IS NULL"))
    report = []
    with httpx.Client(timeout=30) as client:
        for code, (chat, lang) in targets.items():
            done = {
                r[0]
                for r in conn.execute("SELECT job_id FROM telegram_posts WHERE channel = ?", [chat])
            }
            new = [
                j
                for j in country_view(jobs, code)
                if j["verdict"] in ("eligible", "likely") and j["id"] not in done
            ]
            # Oldest first, so the newest job ends up at the bottom of the channel.
            new.sort(key=lambda j: first_seen.get(j["id"], ""))
            if not done:  # first run for this channel
                skip, new = new[:-FIRST_RUN], new[-FIRST_RUN:]
                conn.executemany(
                    "INSERT OR IGNORE INTO telegram_posts VALUES (?, ?, 'skipped')",
                    [(j["id"], chat) for j in skip],
                )
            sent = 0
            for job in new[:PER_RUN]:
                r = client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat, "text": message(job, lang), "parse_mode": "HTML"},
                )
                if r.status_code >= 400:
                    report.append(f"{code}: send failed, HTTP {r.status_code} {r.text[:200]}")
                    break
                conn.execute(
                    "INSERT OR IGNORE INTO telegram_posts VALUES (?, ?, datetime('now'))",
                    [job["id"], chat],
                )
                conn.commit()
                sent += 1
                time.sleep(3)
            conn.commit()
            report.append(f"{code} ({chat}): {sent} posted, {max(len(new) - sent, 0)} waiting")
    return "## Telegram\n\n" + "\n".join(f"- {line}" for line in report)
