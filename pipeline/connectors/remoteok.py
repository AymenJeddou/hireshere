"""Remote OK public feed (one board: ats=remoteok, slug=all).

Terms: link back to the job's Remote OK URL and name Remote OK as the source. apply_url is
their page, and the site credits them. The first array element is a legal notice, not a job.
"""

from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text

URL = "https://remoteok.com/api"


def parse(data: list, board: Board) -> list[Job]:
    jobs = []
    for j in data:
        if "id" not in j or "position" not in j:
            continue  # the legal notice
        jobs.append(
            Job(
                source="remoteok",
                board_slug=board.slug,
                source_job_id=str(j["id"]),
                company_name=(j.get("company") or "").strip() or board.company_name,
                title=j["position"].strip(),
                location_raw=("Remote; " + j["location"]) if j.get("location") else "Remote",
                remote_flag_raw="remote",
                salary_min=j.get("salary_min") or None,
                salary_max=j.get("salary_max") or None,
                salary_currency="USD" if j.get("salary_min") or j.get("salary_max") else None,
                description_text=html_to_text(j.get("description")),
                apply_url=j["url"],
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    return parse(await get_json(client, URL), board)
