"""Workable's public widget endpoint returns every job with its description in one request."""

from pipeline.connectors._each import each
from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text, iso_date

URL = "https://apply.workable.com/api/v1/widget/accounts/{slug}"


def parse(data: dict, board: Board) -> list[Job]:
    def one(j: dict) -> Job | None:
        locs = j.get("locations") or []
        places = [", ".join(x for x in (loc.get("city"), loc.get("country")) if x) for loc in locs]
        if not places:
            places = [", ".join(x for x in (j.get("city"), j.get("country")) if x)]
        remote = j.get("telecommuting") is True
        return Job(
            source="workable",
            board_slug=board.slug,
            source_job_id=j["shortcode"],
            company_name=board.company_name,
            title=j["title"].strip(),
            location_raw="; ".join(["Remote"] * remote + [p for p in places if p]),
            remote_flag_raw="remote" if remote else None,
            department=j.get("department") or None,
            employment_type_raw=j.get("employment_type") or None,
            description_text=html_to_text(j.get("description")),
            apply_url=j.get("url") or j["shortlink"],
            posted_at=iso_date(j.get("published_on") or j.get("created_at")),
        )

    return each(data.get("jobs") or [], one)


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL.format(slug=board.slug), {"details": "true"}), board)
