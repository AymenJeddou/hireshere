"""SmartRecruiters list endpoint is paginated and has no description (see DECISIONS.md)."""

from pipeline.http import FetchError, get_json
from pipeline.models import Board, Job

URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
PAGE = 100
MAX_PAGES = 10  # bigger boards are on-site corporates; skipping them keeps us polite


def _location(loc: dict) -> str:
    if loc.get("fullLocation"):
        return loc["fullLocation"]
    return ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)


def parse(data: dict, board: Board) -> list[Job]:
    jobs = []
    for j in data["content"]:
        loc = j.get("location") or {}
        flag = "remote" if loc.get("remote") else "hybrid" if loc.get("hybrid") else "onsite"
        jobs.append(
            Job(
                source="smartrecruiters",
                board_slug=board.slug,
                source_job_id=str(j["id"]),
                company_name=board.company_name,
                title=j["name"].strip(),
                location_raw=_location(loc),
                remote_flag_raw=flag,
                department=(j.get("department") or {}).get("label")
                or (j.get("function") or {}).get("label"),
                employment_type_raw=(j.get("typeOfEmployment") or {}).get("label"),
                apply_url=f"https://jobs.smartrecruiters.com/{board.slug}/{j['id']}",
            )
        )
    return jobs


async def fetch(client, board: Board) -> list[Job]:
    jobs: list[Job] = []
    url = URL.format(slug=board.slug)
    for page in range(MAX_PAGES):
        data = await get_json(client, url, {"limit": PAGE, "offset": page * PAGE})
        jobs += parse(data, board)
        if (page + 1) * PAGE >= data.get("totalFound", 0):
            return jobs
    raise FetchError(f"more than {MAX_PAGES * PAGE} postings")
