"""What the model extracts from a posting. Provider-agnostic."""

import re
from typing import Literal

from pydantic import BaseModel, field_validator

REGIONS = [
    "Worldwide", "EMEA", "Europe", "EU", "Africa", "North Africa", "MENA", "Middle East",
    "Americas", "North America", "LATAM", "APAC", "Asia", "Oceania",
]  # fmt: skip


class Extraction(BaseModel):
    remote_type: Literal["fully_remote", "hybrid", "onsite", "unclear"]
    geo_scope: Literal["worldwide", "regions", "countries", "timezone_only", "unclear"]
    allowed_countries: list[str] = []
    excluded_countries: list[str] = []
    allowed_regions: list[str] = []
    timezone_requirement: str | None = None
    timezone_utc_min: float | None = None
    timezone_utc_max: float | None = None
    work_authorization_required: list[str] = []
    engagement: Literal["employee", "contractor", "either", "unclear"]
    languages_required: list[str] = []
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "unclear"]
    role_family: Literal[
        "engineering", "data", "design", "product", "marketing", "sales", "support", "ops", "other"
    ]
    evidence_quote: str
    confidence: Literal["high", "medium", "low"]

    @field_validator("allowed_countries", "excluded_countries", "work_authorization_required")
    @classmethod
    def _iso2(cls, v: list[str]) -> list[str]:
        out = []
        for c in v:
            c = c.strip().upper()
            c = {"UK": "GB"}.get(c, c)
            if re.fullmatch(r"[A-Z]{2}", c) and c not in out:
                out.append(c)
        return out

    @field_validator("allowed_regions")
    @classmethod
    def _regions(cls, v: list[str]) -> list[str]:
        return [r for r in v if r in REGIONS]

    @field_validator("languages_required")
    @classmethod
    def _langs(cls, v: list[str]) -> list[str]:
        return [x.strip().lower() for x in v if re.fullmatch(r"[a-zA-Z]{2}", x.strip())]

    @field_validator("timezone_requirement")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None

    @field_validator("evidence_quote")
    @classmethod
    def _quote(cls, v: str) -> str:
        return v.strip()[:200]


def _arr(items: dict | None = None) -> dict:
    return {"type": "array", "items": items or {"type": "string"}}


def _enum(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


# Hand-written so it stays inside the JSON Schema subset Gemini accepts.
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "remote_type": _enum("fully_remote", "hybrid", "onsite", "unclear"),
        "geo_scope": _enum("worldwide", "regions", "countries", "timezone_only", "unclear"),
        "allowed_countries": _arr(),
        "excluded_countries": _arr(),
        "allowed_regions": _arr(_enum(*REGIONS)),
        "timezone_requirement": {"type": ["string", "null"]},
        "timezone_utc_min": {"type": ["number", "null"]},
        "timezone_utc_max": {"type": ["number", "null"]},
        "work_authorization_required": _arr(),
        "engagement": _enum("employee", "contractor", "either", "unclear"),
        "languages_required": _arr(),
        "seniority": _enum("intern", "junior", "mid", "senior", "lead", "unclear"),
        "role_family": _enum(
            "engineering", "data", "design", "product", "marketing", "sales", "support", "ops",
            "other",
        ),
        "evidence_quote": {"type": "string"},
        "confidence": _enum("high", "medium", "low"),
    },
    "required": list(Extraction.model_fields),
}  # fmt: skip
