"""Build jobs one posting at a time, so one malformed posting does not fail a whole board."""

from collections.abc import Callable, Iterable

from pipeline.models import Job

BAD = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
)  # pydantic's ValidationError is a ValueError


def each(postings: Iterable[dict], build: Callable[[dict], Job | None]) -> list[Job]:
    """build() returns a Job, or None to skip on purpose. A posting that raises is dropped,
    unless every posting raises: then the feed itself changed shape, and the board must fail
    (an empty result would expire all its jobs)."""
    jobs, first = [], None
    for p in postings:
        try:
            job = build(p)
        except BAD as e:
            first = first or e
            continue
        if job:
            jobs.append(job)
    if first and not jobs:
        raise first
    return jobs
