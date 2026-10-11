"""Jobicy public remote-jobs API (one board: ats=jobicy, slug=all).

Terms (the feed's notice and jobicy.com/jobs-rss-feed): credit Jobicy with a direct link and send
every Apply button to the job URL in the feed. The feed only holds the last 7 days and a job
missing from it may still be open, so these jobs expire by age (config.ROLLING_DAYS).
"""

import html

from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text, iso_date

URL = "https://jobicy.com/api/v2/remote-jobs"
MAX_PAGES = 10


def _join(v) -> str:
    return ", ".join(v) if isinstance(v, list) else str(v or "")


def parse(data: dict, board: Board) -> list[Job]:
    jobs = []
    for j in data.get("jobs") or []:
        level = j.get("jobLevel") or ""
        desc = html_to_text(j.get("jobDescription"))
        jobs.append(
            Job(
                source="jobicy",
                board_slug=board.slug,
                source_job_id=str(j["id"]),
                company_name=html.unescape(j.get("companyName") or "").strip()
                or board.company_name,
                title=html.unescape(j["jobTitle"]).strip(),
                location_raw="Remote; " + _join(j.get("jobGeo")) if j.get("jobGeo") else "Remote",
                remote_flag_raw="remote",
                department=_join(j.get("jobIndustry")) or None,
                employment_type_raw=_join(j.get("jobType")) or None,
                salary_min=j.get("annualSalaryMin") or None,
                salary_max=j.get("annualSalaryMax") or None,
                salary_currency=j.get("salaryCurrency") or None,
                description_text=f"Level: {level}\n\n{desc}" if level and level != "Any" else desc,
                apply_url=j["url"],
                posted_at=iso_date(j.get("pubDate")),
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    jobs: list[Job] = []
    params = {"count": 100}
    for _ in range(MAX_PAGES):
        data = await get_json(client, URL, params)
        jobs += parse(data, board)
        if not data.get("hasMore") or not data.get("nextCursor"):
            break
        params = {"count": 100, "cursor": data["nextCursor"]}
    return jobs
