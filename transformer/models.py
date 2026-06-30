from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SourceName = Literal["ats_json", "recruiter_csv", "resume", "notes", "github"]
MethodName = Literal[
    "exact",
    "regex",
    "llm_extraction",
    "github_authored",
    "github_filesignal",
]


class Observation(BaseModel):
    field: str
    value: Any
    source: SourceName
    method: MethodName
    candidate_hint: str | None = None
    confidence_signals: dict[str, Any] = Field(default_factory=dict)


class ProvenanceEntry(BaseModel):
    field: str
    source: str
    method: str
    value: Any | None = None
    selected: bool = True


class Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None


class Links(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = Field(default_factory=list)


class Skill(BaseModel):
    name: str
    confidence: float = 0.0
    sources: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    summary: str | None = None


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    end_year: int | None = None


class FieldMeta(BaseModel):
    confidence: float = 0.0
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)


class CanonicalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    match_key: str | None = None
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)
    headline: str | None = None
    years_experience: float | None = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    field_meta: dict[str, FieldMeta] = Field(default_factory=dict, exclude=True)
    overall_confidence: float = 0.0
