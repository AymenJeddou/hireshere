"""After a deploy, check the live site the way a visitor would. Exit 1 on a real failure, so the
daily workflow fails and GitHub emails the owner.

    python -m pipeline.healthcheck [--index site/public/data/search-en.json]
"""

import argparse
import json
import sys
import time

import httpx

from pipeline import config

SHELL = 'id="job-slot"'  # the job page shell before a Function fills it


def problems(pages: dict[str, tuple[int, str]], jobs: list[str]) -> tuple[list[str], list[str]]:
    """(failures, warnings) from {path: (status, body)}. A job page served as the browser
    fallback shell still works for visitors, so it is a warning (Functions are off)."""
    fail, warn = [], []
    for path, (status, body) in pages.items():
        if status != 200:
            fail.append(f"{path}: HTTP {status}")
        elif path in jobs and SHELL in body:
            warn.append(f"{path}: served by the browser fallback (Pages Functions are off)")
        elif path in jobs and "Page not found" in body:
            fail.append(f"{path}: shows Page not found")
    return fail, warn


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pipeline.healthcheck")
    p.add_argument("--index", default="site/public/data/search-en.json")
    p.add_argument("--tries", type=int, default=3, help="a fresh deploy can take a minute")
    args = p.parse_args(argv)
    with open(args.index, encoding="utf-8") as f:
        index = json.load(f)
    jobs = [f"/jobs/{j['slug']}" for j in index[:3]]
    if index:
        jobs.append(f"/fr/jobs/{index[0]['slug']}")
    paths = ["/", "/jobs", "/api/geo", *jobs]
    base = f"https://{config.DOMAIN}"
    fail, warn = ["not run"], []
    with httpx.Client(timeout=30, headers={"User-Agent": config.USER_AGENT}) as client:
        for attempt in range(args.tries):
            if attempt:
                time.sleep(30)
            pages = {}
            for path in paths:
                try:
                    r = client.get(base + path)
                    pages[path] = (r.status_code, r.text)
                except httpx.HTTPError as e:
                    pages[path] = (0, type(e).__name__)
            fail, warn = problems(pages, jobs)
            if not fail:
                break
    for w in warn:
        print(f"warning: {w}")
    for x in fail:
        print(f"FAILED: {x}", file=sys.stderr)
    print("healthcheck:", "ok" if not fail else f"{len(fail)} failure(s)", f"({len(paths)} pages)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
