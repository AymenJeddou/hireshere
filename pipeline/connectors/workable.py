"""Workable's public widget endpoint returns every job with its description in one request."""

from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text

URL = "https://apply.workable.com/api/v1/widget/accounts/{slug}"


def parse(data: dict, board: Board) -> list[Job]:
    jobs = []
    for j in data.get("jobs") or []:
        locs = j.get("locations") or []
        places = [", ".join(x for x in (loc.get("city"), loc.get("country")) if x) for loc in locs]
        if not places:
            places = [", ".join(x for x in (j.get("city"), j.get("country")) if x)]
        remote = j.get("telecommuting") is True
        jobs.append(
            Job(
                source="workable",
                board_slug=board.slug,
                source_job_id=j["shortcode"],
                company_name=board.company_name,
                title=j["title"].strip(),
                location_raw=("Remote; " if remote else "") + "; ".join(p for p in places if p),
                remote_flag_raw="remote" if remote else None,
                department=j.get("department") or None,
                employment_type_raw=j.get("employment_type") or None,
                description_text=html_to_text(j.get("description")),
                apply_url=j.get("url") or j["shortlink"],
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL.format(slug=board.slug), {"details": "true"}), board)
