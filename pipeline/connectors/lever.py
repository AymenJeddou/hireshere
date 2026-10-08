from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text

URL = "https://api.lever.co/v0/postings/{slug}"


def parse(data: list, board: Board) -> list[Job]:
    jobs = []
    for j in data:
        cat = j.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location") or ""]
        sections = [j.get("descriptionPlain") or ""]
        for item in j.get("lists") or []:
            sections.append(f"{item.get('text', '')}\n{html_to_text(item.get('content'))}")
        sections.append(j.get("additionalPlain") or "")
        sal = j.get("salaryRange") or {}
        jobs.append(
            Job(
                source="lever",
                board_slug=board.slug,
                source_job_id=j["id"],
                company_name=board.company_name,
                title=j["text"].strip(),
                location_raw="; ".join(x for x in locs if x),
                remote_flag_raw=j.get("workplaceType"),
                department=cat.get("department") or cat.get("team"),
                employment_type_raw=cat.get("commitment"),
                salary_min=sal.get("min"),
                salary_max=sal.get("max"),
                salary_currency=sal.get("currency"),
                description_text="\n\n".join(s.strip() for s in sections if s.strip()),
                apply_url=j["hostedUrl"],
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL.format(slug=board.slug), {"mode": "json"}), board)
