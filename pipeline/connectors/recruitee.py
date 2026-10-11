from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text, iso_date

URL = "https://{slug}.recruitee.com/api/offers/"


def parse(data: dict, board: Board) -> list[Job]:
    jobs = []
    for j in data["offers"]:
        if j.get("status", "published") != "published":
            continue
        locs = [x.get("name") or "" for x in j.get("locations") or []] or [j.get("location") or ""]
        flag = (
            "remote"
            if j.get("remote")
            else "hybrid"
            if j.get("hybrid")
            else "onsite"
            if j.get("on_site")
            else None
        )
        sal = j.get("salary") or {}
        jobs.append(
            Job(
                source="recruitee",
                board_slug=board.slug,
                source_job_id=str(j["id"]),
                company_name=board.company_name,
                title=j["title"].strip(),
                location_raw="; ".join(x for x in [j.get("location") or "", *locs[1:]] if x),
                remote_flag_raw=flag,
                department=j.get("department"),
                employment_type_raw=j.get("employment_type_code"),
                salary_min=sal.get("min"),
                salary_max=sal.get("max"),
                salary_currency=sal.get("currency"),
                description_text=html_to_text(
                    f"{j.get('description') or ''}{j.get('requirements') or ''}"
                ),
                apply_url=j["careers_url"],
                posted_at=iso_date(j.get("published_at") or j.get("created_at")),
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL.format(slug=board.slug)), board)
