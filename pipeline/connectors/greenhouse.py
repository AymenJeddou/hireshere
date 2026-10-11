from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text, iso_date

URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def _meta(job: dict, name: str) -> str | None:
    for m in job.get("metadata") or []:
        if (m.get("name") or "").lower() == name and m.get("value"):
            v = m["value"]
            return ", ".join(v) if isinstance(v, list) else str(v)
    return None


def parse(data: dict, board: Board) -> list[Job]:
    jobs = []
    for j in data["jobs"]:
        depts = j.get("departments") or []
        jobs.append(
            Job(
                source="greenhouse",
                board_slug=board.slug,
                source_job_id=str(j["id"]),
                company_name=board.company_name,
                title=j["title"].strip(),
                location_raw=((j.get("location") or {}).get("name") or "").strip(),
                department=depts[0]["name"] if depts else None,
                employment_type_raw=_meta(j, "employment type"),
                description_text=html_to_text(j.get("content"), escaped=True),
                apply_url=j["absolute_url"],
                posted_at=iso_date(j.get("first_published")),
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL.format(slug=board.slug), {"content": "true"}), board)
