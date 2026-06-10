from __future__ import annotations

import math
from dataclasses import dataclass

from phd_shortlist.models.schema import StudentProfile, Tier
from phd_shortlist.text import keyword_set, phrase_overlap


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    topical_fit: float
    evidence_strength: float
    authority: float
    contamination_penalty: float
    outcome_adjustment: float = 0.0


def score_candidate(
    profile: StudentProfile,
    *,
    concepts: list[str],
    evidence_titles: list[str],
    works_count: int,
    cited_by_count: int,
    career_stage_risk: bool,
    same_name_risk: bool,
    outcome_adjustment: float = 0.0,
) -> ScoreBreakdown:
    student_text = " ".join(
        profile.research_interests
        + profile.skills
        + [profile.intro_call_summary, profile.raw_resume_text]
    )
    candidate_text = " ".join(concepts + evidence_titles)
    topical_fit = max(
        [phrase_overlap(area, candidate_text) for area in profile.research_interests] + [0.0]
    )
    topical_fit = max(topical_fit, _keyword_overlap(student_text, candidate_text))
    evidence_strength = min(1.0, len(evidence_titles) / 3)
    authority = min(1.0, (math.log1p(works_count) / math.log(200)) * 0.55 + (math.log1p(cited_by_count) / math.log(5000)) * 0.45)
    contamination_penalty = 0.0
    if career_stage_risk:
        contamination_penalty += 0.20
    if same_name_risk:
        contamination_penalty += 0.08
    total = (
        0.50 * topical_fit
        + 0.25 * evidence_strength
        + 0.20 * authority
        + outcome_adjustment
        - contamination_penalty
    )
    return ScoreBreakdown(
        total=max(0.0, min(1.0, total)),
        topical_fit=topical_fit,
        evidence_strength=evidence_strength,
        authority=authority,
        contamination_penalty=contamination_penalty,
        outcome_adjustment=outcome_adjustment,
    )


def assign_tier(score: float, authority: float) -> Tier:
    if score >= 0.72 and authority >= 0.55:
        return Tier.reach
    if score >= 0.45:
        return Tier.target
    return Tier.safety


def _keyword_overlap(a: str, b: str) -> float:
    a_terms = keyword_set([a], limit=120)
    b_terms = keyword_set([b], limit=160)
    if not a_terms or not b_terms:
        return 0.0
    return len(a_terms & b_terms) / max(10, len(a_terms))
