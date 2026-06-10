from __future__ import annotations

import re

from phd_shortlist.models.schema import QualityFlags, StudentProfile
from phd_shortlist.text import keyword_set, phrase_overlap

JUNIOR_TERMS = {
    "student",
    "doctoral",
    "phd candidate",
    "postdoctoral",
    "postdoc",
    "fellow",
    "research assistant",
}

ACADEMIC_PI_TERMS = {
    "professor",
    "associate professor",
    "assistant professor",
    "reader",
    "lecturer",
    "chair",
    "principal investigator",
    "group leader",
}

INELIGIBLE_PATTERNS = [
    r"\bhome fees?\b",
    r"\buk only\b",
    r"\beu residents? only\b",
    r"\bcitizens? of\b",
    r"\bpermanent residents? only\b",
]


def evidence_relevance(profile: StudentProfile, title: str, abstract: str = "") -> float:
    student_terms = keyword_set(
        profile.research_interests
        + profile.skills
        + [profile.intro_call_summary, profile.raw_resume_text],
        limit=100,
    )
    evidence_terms = keyword_set([title, abstract], limit=100)
    if not student_terms or not evidence_terms:
        return 0.0
    direct_area = max(phrase_overlap(area, f"{title} {abstract}") for area in profile.research_interests)
    return max(direct_area, len(student_terms & evidence_terms) / max(8, len(student_terms)))


def infer_quality_flags(
    *,
    works_count: int,
    name: str,
    evidence_count: int,
    institution_verified: bool,
    profile_text: str = "",
    eligibility_text: str = "",
) -> QualityFlags:
    notes: list[str] = []
    same_name_risk = not institution_verified or len(name.split()) <= 2
    if same_name_risk:
        notes.append("Common-name or weak-affiliation risk; retain only if evidence is strong.")

    lower_profile = profile_text.lower()
    career_stage_risk = works_count < 10 or any(term in lower_profile for term in JUNIOR_TERMS)
    if any(term in lower_profile for term in ACADEMIC_PI_TERMS):
        career_stage_risk = False
    if career_stage_risk:
        notes.append("Possible junior researcher; filtered/scored conservatively.")

    weak_evidence_risk = evidence_count < 1
    if weak_evidence_risk:
        notes.append("No usable evidence survived relevance filtering.")

    eligibility_risk = any(re.search(pattern, eligibility_text.lower()) for pattern in INELIGIBLE_PATTERNS)
    if eligibility_risk:
        notes.append("Linked position may contain citizenship/residency restrictions.")

    return QualityFlags(
        same_name_risk=same_name_risk,
        career_stage_risk=career_stage_risk,
        weak_evidence_risk=weak_evidence_risk,
        eligibility_risk=eligibility_risk,
        notes=notes,
    )
