"""Fetch each company's own icon once into site/public/logos/<key>.<ext>.

    python -m pipeline.logos [--force]

Fills missing websites in data/boards.csv from the company's own board page first, then
uses the company's website from data/boards.csv and its declared icons, preferring the
large apple-touch-icon. Files are committed, so pages never hotlink third parties.
"""

import argparse
import csv
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import httpx

from pipeline import config
from pipeline.export import slugify, websites
from pipeline.run import load_boards

OUT = Path("site/public/logos")
# Icons that came back unusable (white on white, empty or corrupt): these show initials.
SKIP = {
    "intevity",
    "medium",
    "niantic-spatial",
    "spacial-ai",
    "superior-executive-legal-recruiting",
}
TYPES = {"image/png": "png", "image/svg+xml": "svg", "image/x-icon": "ico",
         "image/vnd.microsoft.icon": "ico", "image/jpeg": "jpg", "image/webp": "webp"}  # fmt: skip


class Icons(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        rel = (a.get("rel") or "").lower()
        if tag != "link" or "icon" not in rel or not a.get("href") or a["href"].startswith("data:"):
            return
        size = max(
            (int(s.split("x")[0]) for s in (a.get("sizes") or "").split() if "x" in s), default=0
        )
        rank = (
            1000
            if "apple-touch-icon" in rel
            else size or (64 if a["href"].endswith(".svg") else 16)
        )
        self.found.append((rank, a["href"]))


# Where each board page links to the company's home page.
HOME = {
    "ashby": ("https://jobs.ashbyhq.com/{}", r'"publicWebsite":"(https?://[^"]+)"'),
    "lever": (
        "https://jobs.lever.co/{}",
        r'class="main-footer-text"><p><a href="(https?://[^"]+)"',
    ),
    "teamtailor": (
        "https://{}.teamtailor.com/",
        r'Homepage</span>\s*<a[^>]*href="(https?://[^"]+)"',
    ),
    "smartrecruiters": (
        "https://careers.smartrecruiters.com/{}",
        r'<li class="nav-item"><a href="(https?://[^"]+)" class="nav-link"',
    ),
}

ATS_HOSTS = r"example\.com|ashbyhq|lever\.co|greenhouse|smartrecruiters|teamtailor|workable|recruitee|ultipro"


def discover_websites(client: httpx.Client) -> None:
    """Write the home page link from each board page into boards.csv where it is empty."""
    with open(config.BOARDS_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    found = 0
    for r in rows:
        if r["website"] or r["ats"] not in HOME:
            continue
        url, pattern = HOME[r["ats"]]
        try:
            m = re.search(pattern, client.get(url.format(r["slug"])).text)
        except (httpx.HTTPError, ValueError):
            continue
        if m and not re.search(ATS_HOSTS, m.group(1), re.I):
            r["website"] = m.group(1)
            found += 1
    with open(config.BOARDS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"websites: found {found} from board pages")


def fetch_logo(client: httpx.Client, site: str) -> tuple[bytes, str] | None:
    page = client.get(site)
    parser = Icons()
    parser.feed(page.text)
    candidates = [urljoin(str(page.url), h) for _, h in sorted(parser.found, reverse=True)]
    for url in candidates + [
        urljoin(str(page.url), "/apple-touch-icon.png"),
        urljoin(str(page.url), "/favicon.ico"),
    ]:
        try:
            r = client.get(url)
        except (httpx.HTTPError, ValueError):
            continue
        ext = TYPES.get(r.headers.get("content-type", "").split(";")[0].strip())
        # ponytail: size cap instead of resizing; add Pillow if more big icons show up.
        if r.status_code == 200 and ext and 100 < len(r.content) < 120_000:
            return r.content, ext
    return None


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="pipeline.logos")
    p.add_argument("--force", action="store_true", help="refetch logos that already exist")
    args = p.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    with httpx.Client(
        timeout=20, follow_redirects=True, headers={"User-Agent": config.USER_AGENT}
    ) as client:
        discover_websites(client)
        sites = websites()
        companies = {
            slugify(b.company_name): sites[(b.ats, b.slug)]
            for b in load_boards()
            if (b.ats, b.slug) in sites
        }
        for key, site in sorted(companies.items()):
            if key in SKIP:
                continue
            if not args.force and any(OUT.glob(f"{key}.*")):
                ok += 1
                continue
            try:
                got = fetch_logo(client, site)
            except (httpx.HTTPError, ValueError) as e:
                print(f"  {key}: {type(e).__name__}", file=sys.stderr)
                continue
            if got:
                for old in OUT.glob(f"{key}.*"):
                    old.unlink()
                (OUT / f"{key}.{got[1]}").write_bytes(got[0])
                ok += 1
            else:
                print(f"  {key}: no icon found", file=sys.stderr)
    print(f"logos: {ok} of {len(companies)} companies")


if __name__ == "__main__":
    main()
