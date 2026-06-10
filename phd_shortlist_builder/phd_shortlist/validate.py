from __future__ import annotations

from collections import Counter

from phd_shortlist.models.schema import ShortlistOutput


def validate_shortlist(output: ShortlistOutput) -> list[str]:
    errors: list[str] = []
    target_countries = set(output.metadata.target_countries)
    for index, rec in enumerate(output.recommendations, start=1):
        prefix = f"recommendations[{index}] {rec.name}:"
        if rec.country not in target_countries:
            errors.append(f"{prefix} country {rec.country!r} not in target countries")
        if not rec.evidence:
            errors.append(f"{prefix} missing evidence")
        for item in rec.evidence:
            if not item.url:
                errors.append(f"{prefix} evidence {item.title!r} missing URL")
        if not rec.why_match or rec.why_match.lower().count("student") == 0:
            errors.append(f"{prefix} why_match is not personalized enough")
    duplicates = [
        supervisor_id
        for supervisor_id, count in Counter(rec.supervisor_id for rec in output.recommendations).items()
        if count > 1
    ]
    if duplicates:
        errors.append(f"duplicate supervisor IDs: {duplicates}")
    return errors
