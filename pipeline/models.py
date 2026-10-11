import hashlib

from pydantic import BaseModel, computed_field


class Board(BaseModel):
    ats: str
    slug: str
    company_name: str
    website: str = ""
    source_of_entry: str = ""


class Job(BaseModel):
    source: str
    board_slug: str
    source_job_id: str
    company_name: str
    title: str
    location_raw: str = ""
    remote_flag_raw: str | None = None
    department: str | None = None
    employment_type_raw: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    description_text: str = ""
    apply_url: str
    posted_at: str | None = None  # when the employer published it, from the feed

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.source}:{self.board_slug}:{self.source_job_id}"

    @computed_field
    @property
    def content_hash(self) -> str:
        text = "\x1f".join([self.title, self.location_raw, self.description_text])
        return hashlib.sha256(text.encode()).hexdigest()[:16]


class FetchResult(BaseModel):
    board: Board
    ok: bool
    jobs: list[Job] = []
    error: str | None = None
