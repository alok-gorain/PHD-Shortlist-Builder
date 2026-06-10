from datetime import datetime, timezone

from phd_shortlist.models.schema import (
    EvidenceItem,
    ShortlistMetadata,
    ShortlistOutput,
    SupervisorRecommendation,
    Tier,
)
from phd_shortlist.validate import validate_shortlist


def test_validate_shortlist_accepts_minimal_valid_record():
    output = ShortlistOutput(
        student_id="s1",
        metadata=ShortlistMetadata(
            generated_at=datetime.now(timezone.utc),
            generator_version="test",
            data_sources=["unit-test"],
            target_countries=["Canada"],
            requested_min=1,
            requested_max=1,
            total_recommendations=1,
        ),
        recommendations=[
            SupervisorRecommendation(
                supervisor_id="A1",
                name="Jane Doe",
                institution="University of Example",
                country="Canada",
                research_focus=["hydrogels"],
                matched_student_areas=["hydrogel drug delivery"],
                evidence=[
                    EvidenceItem(
                        type="paper",
                        title="Hydrogel drug delivery for wound healing",
                        year=2024,
                        url="https://doi.org/10.0000/example",
                        source="OpenAlex",
                        relevance_reason="Direct topical overlap.",
                    )
                ],
                why_match="The student can reference this professor's hydrogel paper.",
                tier=Tier.target,
                score=0.7,
            )
        ],
    )

    assert validate_shortlist(output) == []
