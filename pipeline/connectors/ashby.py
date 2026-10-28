from pipeline.connectors._each import each
from pipeline.http import get_json
from pipeline.models import Board, Job
from pipeline.text import html_to_text, iso_date

URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def parse(data: dict, board: Board) -> list[Job]:
    def one(j: dict) -> Job | None:
        if j.get("isListed") is False:
            return None
        locs = [j.get("location") or ""] + [
            s.get("location") or "" for s in j.get("secondaryLocations") or []
        ]
        comp = (j.get("compensation") or {}).get("summaryComponents") or []
        salary = next((c for c in comp if c.get("compensationType") == "Salary"), {})
        remote = j.get("workplaceType") or ("Remote" if j.get("isRemote") else None)
        return Job(
            source="ashby",
            board_slug=board.slug,
            source_job_id=j["id"],
            company_name=board.company_name,
            title=j["title"].strip(),
            location_raw="; ".join(x for x in locs if x),
            remote_flag_raw=remote,
            department=j.get("department") or j.get("team"),
            employment_type_raw=j.get("employmentType"),
            salary_min=salary.get("minValue"),
            salary_max=salary.get("maxValue"),
            salary_currency=salary.get("currencyCode"),
            description_text=j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
            apply_url=j["jobUrl"],
            posted_at=iso_date(j.get("publishedAt")),
        )

    return each(data["jobs"], one)


async def fetch(client, board: Board) -> list[Job]:
    url = URL.format(slug=board.slug)
    return parse(await get_json(client, url, {"includeCompensation": "true"}), board)
