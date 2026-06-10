from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from phd_shortlist import __version__
from phd_shortlist.config import RuntimeConfig
from phd_shortlist.countries import country_name, normalize_country_to_iso2
from phd_shortlist.data_sources.openalex import OpenAlexAuthor, OpenAlexClient
from phd_shortlist.models.schema import (
    EvidenceItem,
    ProgramLink,
    ShortlistMetadata,
    ShortlistOutput,
    StudentProfile,
    SupervisorRecommendation,
)
from phd_shortlist.outcomes import OutcomeSignals, outcome_adjustment
from phd_shortlist.quality import evidence_relevance, infer_quality_flags
from phd_shortlist.scoring import assign_tier, score_candidate


class ShortlistBuilder:
    def __init__(self, config: RuntimeConfig, outcome_signals: OutcomeSignals):
        self.config = config
        self.openalex = OpenAlexClient(config)
        self.outcome_signals = outcome_signals

    def build(self, profile: StudentProfile) -> ShortlistOutput:
        country_codes = [normalize_country_to_iso2(country) for country in profile.target_countries]
        candidates: dict[str, OpenAlexAuthor] = {}
        warnings: list[str] = []

        for area in profile.research_interests:
            for author in self.openalex.search_authors(
                query=area,
                country_codes=country_codes,
                per_page=self.config.per_area_candidate_limit,
            ):
                if author.country_code not in country_codes:
                    continue
                if not author.institution:
                    continue
                candidates[author.id] = author
            if len(candidates) < self.config.min_recommendations:
                for author in self.openalex.search_authors_from_works(
                    query=area,
                    country_codes=country_codes,
                    per_page=self.config.per_area_candidate_limit,
                ):
                    if author.country_code not in country_codes:
                        continue
                    if not author.institution:
                        continue
                    candidates[author.id] = author

        recommendations = [
            rec
            for author in candidates.values()
            if (rec := self._recommendation_for_author(profile, author)) is not None
        ]
        recommendations.sort(key=lambda rec: rec.score, reverse=True)
        recommendations = self._spread_across_areas(recommendations, profile)[: self.config.max_recommendations]

        if len(recommendations) < self.config.min_recommendations:
            warnings.append(
                f"Only {len(recommendations)} recommendations produced. "
                "Increase per-area limits, broaden profile terms, or enable more data sources."
            )

        return ShortlistOutput(
            student_id=profile.student_id,
            metadata=ShortlistMetadata(
                generated_at=datetime.now(timezone.utc),
                generator_version=__version__,
                data_sources=["OpenAlex authors/works API"],
                target_countries=[country_name(code) for code in country_codes],
                requested_min=self.config.min_recommendations,
                requested_max=self.config.max_recommendations,
                total_recommendations=len(recommendations),
                warnings=warnings,
            ),
            recommendations=recommendations,
        )

    def _recommendation_for_author(
        self, profile: StudentProfile, author: OpenAlexAuthor
    ) -> SupervisorRecommendation | None:
        works = self.openalex.author_works(author.id, self.config.works_per_candidate)
        evidence = self._evidence_for_works(profile, works)
        flags = infer_quality_flags(
            works_count=author.works_count,
            name=author.display_name,
            evidence_count=len(evidence),
            institution_verified=bool(author.institution and author.country_code),
            profile_text=" ".join(author.concepts),
        )
        if flags.career_stage_risk and author.works_count < 8:
            return None
        if not evidence:
            return None

        matched_areas = self._matched_areas(profile, author.concepts, [item.title for item in evidence])
        adjustment = outcome_adjustment(
            self.outcome_signals,
            supervisor_id=author.id,
            institution=author.institution or "",
            areas=matched_areas,
        )
        score = score_candidate(
            profile,
            concepts=author.concepts,
            evidence_titles=[item.title for item in evidence],
            works_count=author.works_count,
            cited_by_count=author.cited_by_count,
            career_stage_risk=flags.career_stage_risk,
            same_name_risk=flags.same_name_risk,
            outcome_adjustment=adjustment,
        )
        if score.total < 0.22:
            return None

        return SupervisorRecommendation(
            supervisor_id=author.id.rsplit("/", 1)[-1],
            name=author.display_name,
            institution=author.institution or "Unknown institution",
            country=country_name(author.country_code),
            contact_email=None,
            profile_url=author.id,
            research_focus=author.concepts[:8] or matched_areas,
            matched_student_areas=matched_areas,
            evidence=evidence[:3],
            why_match=self._why_match(profile, author, evidence, matched_areas),
            tier=assign_tier(score.total, score.authority),
            score=round(score.total, 4),
            linked_programs_or_positions=[
                ProgramLink(
                    title=f"{author.institution} doctoral programs",
                    url=self._institution_search_url(author.institution or "", "PhD program"),
                    source="Institution web search URL",
                    eligibility_note="Verify intake, funding, and citizenship restrictions before outreach.",
                )
            ],
            quality_flags=flags,
            source_metadata={
                "openalex_author_id": author.id,
                "works_count": author.works_count,
                "cited_by_count": author.cited_by_count,
                "score_breakdown": score.__dict__,
            },
        )

    def _evidence_for_works(self, profile: StudentProfile, works: list[dict[str, Any]]) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        for work in works:
            title = work.get("display_name")
            if not title:
                continue
            abstract = _reconstruct_abstract(work.get("abstract_inverted_index") or {})
            relevance = evidence_relevance(profile, title, abstract)
            if relevance < 0.03:
                continue
            url = work.get("doi") or work.get("id") or work.get("primary_location", {}).get("landing_page_url")
            if not url:
                continue
            evidence.append(
                EvidenceItem(
                    type="paper",
                    title=title,
                    year=work.get("publication_year"),
                    url=url,
                    source="OpenAlex",
                    relevance_reason=f"Overlaps with profile interests at relevance={relevance:.2f}.",
                )
            )
        return evidence

    def _matched_areas(
        self, profile: StudentProfile, concepts: list[str], evidence_titles: list[str]
    ) -> list[str]:
        text = " ".join(concepts + evidence_titles).lower()
        matched = [
            area
            for area in profile.research_interests
            if any(term in text for term in area.lower().split())
        ]
        return matched or profile.research_interests[:1]

    def _why_match(
        self,
        profile: StudentProfile,
        author: OpenAlexAuthor,
        evidence: list[EvidenceItem],
        matched_areas: list[str],
    ) -> str:
        student_anchor = profile.projects[0].title if profile.projects else profile.research_interests[0]
        paper = evidence[0].title
        area = matched_areas[0]
        return (
            f"{author.display_name}'s work on “{paper}” is relevant to the student's interest in "
            f"{area}. The match is strongest because the student's background includes {student_anchor}, "
            f"which can be positioned around the methods/themes visible in this publication record."
        )

    def _spread_across_areas(
        self, recommendations: list[SupervisorRecommendation], profile: StudentProfile
    ) -> list[SupervisorRecommendation]:
        if not recommendations:
            return []
        per_area: dict[str, list[SupervisorRecommendation]] = {
            area: [rec for rec in recommendations if area in rec.matched_student_areas]
            for area in profile.research_interests
        }
        interleaved: list[SupervisorRecommendation] = []
        seen: set[str] = set()
        index = 0
        while len(interleaved) < len(recommendations):
            progressed = False
            for area in profile.research_interests:
                bucket = per_area.get(area, [])
                if index < len(bucket):
                    rec = bucket[index]
                    if rec.supervisor_id not in seen:
                        interleaved.append(rec)
                        seen.add(rec.supervisor_id)
                        progressed = True
            if not progressed:
                break
            index += 1
        for rec in recommendations:
            if rec.supervisor_id not in seen:
                interleaved.append(rec)
        return interleaved

    @staticmethod
    def _institution_search_url(institution: str, query: str) -> str:
        from urllib.parse import quote_plus

        return f"https://www.google.com/search?q={quote_plus(institution + ' ' + query)}"


def _reconstruct_abstract(index: dict[str, list[int]]) -> str:
    if not index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            words.append((position, word))
    return " ".join(word for _, word in sorted(words))
