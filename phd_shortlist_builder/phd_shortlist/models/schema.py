from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Tier(str, Enum):
    reach = "reach"
    target = "target"
    safety = "safety"


class Degree(BaseModel):
    degree: str
    institution: str
    field: str | None = None
    grade: str | None = None
    thesis: str | None = None


class Publication(BaseModel):
    title: str
    venue: str | None = None
    year: int | None = None
    url: str | None = None


class Project(BaseModel):
    title: str
    description: str
    skills: list[str] = Field(default_factory=list)


class StudentProfile(BaseModel):
    student_id: str
    education: list[Degree] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    research_interests: list[str] = Field(min_length=1)
    target_countries: list[str] = Field(min_length=1)
    target_intake: str
    intro_call_summary: str = ""
    raw_resume_text: str = ""
    citizenship: str | None = None

    @field_validator("target_countries", "research_interests", "skills")
    @classmethod
    def strip_nonempty(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            raise ValueError("field must contain at least one non-empty value")
        return cleaned


class EvidenceItem(BaseModel):
    type: str = Field(pattern="^(paper|grant|position)$")
    title: str
    year: int | None = None
    url: str
    source: str
    relevance_reason: str


class ProgramLink(BaseModel):
    title: str
    url: str
    source: str
    eligibility_note: str | None = None


class QualityFlags(BaseModel):
    same_name_risk: bool = False
    career_stage_risk: bool = False
    weak_evidence_risk: bool = False
    eligibility_risk: bool = False
    notes: list[str] = Field(default_factory=list)


class SupervisorRecommendation(BaseModel):
    supervisor_id: str
    name: str
    institution: str
    country: str
    contact_email: str | None = None
    profile_url: str | None = None
    research_focus: list[str]
    matched_student_areas: list[str]
    evidence: list[EvidenceItem] = Field(min_length=1)
    why_match: str
    tier: Tier
    score: float = Field(ge=0.0, le=1.0)
    linked_programs_or_positions: list[ProgramLink] = Field(default_factory=list)
    quality_flags: QualityFlags = Field(default_factory=QualityFlags)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class ShortlistMetadata(BaseModel):
    generated_at: datetime
    generator_version: str
    data_sources: list[str]
    target_countries: list[str]
    requested_min: int
    requested_max: int
    total_recommendations: int
    warnings: list[str] = Field(default_factory=list)


class ShortlistOutput(BaseModel):
    student_id: str
    schema_version: str = "1.0"
    metadata: ShortlistMetadata
    recommendations: list[SupervisorRecommendation]

    @field_validator("recommendations")
    @classmethod
    def unique_supervisors(cls, recs: list[SupervisorRecommendation]) -> list[SupervisorRecommendation]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for rec in recs:
            if rec.supervisor_id in seen:
                duplicates.append(rec.supervisor_id)
            seen.add(rec.supervisor_id)
        if duplicates:
            raise ValueError(f"duplicate supervisor_id values: {duplicates}")
        return recs
