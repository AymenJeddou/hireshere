"""Teamtailor career sites publish a JSON Feed with a schema.org JobPosting per item."""

from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text

URL = "https://{slug}.teamtailor.com/jobs.json"


def _place(p: dict) -> str:
    a = p.get("address") or {}
    return ", ".join(x for x in (a.get("addressLocality"), a.get("addressCountry")) if x)


def parse(data: dict, board: Board) -> list[Job]:
    jobs = []
    for it in data["items"]:
        jp = it.get("_jobposting") or {}
        places = jp.get("jobLocation") or []
        if isinstance(places, dict):
            places = [places]
        remote = jp.get("jobLocationType") == "TELECOMMUTE"
        req = jp.get("applicantLocationRequirements") or []
        if isinstance(req, dict):
            req = [req]
        location = "; ".join(
            [_place(p) for p in places if _place(p)]
            + [r.get("name", "") for r in req if r.get("name")]
        )
        emp = jp.get("employmentType")
        jobs.append(
            Job(
                source="teamtailor",
                board_slug=board.slug,
                source_job_id=str(it["id"]),
                company_name=board.company_name,
                title=it["title"].strip(),
                location_raw=("Remote; " if remote else "") + location
                if remote or location
                else "",
                remote_flag_raw="remote" if remote else None,
                employment_type_raw=", ".join(emp) if isinstance(emp, list) else emp,
                description_text=html_to_text(it.get("content_html")),
                apply_url=it["url"],
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL.format(slug=board.slug)), board)
