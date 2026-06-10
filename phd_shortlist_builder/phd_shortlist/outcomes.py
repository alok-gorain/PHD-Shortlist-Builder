from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

POSITIVE = {"ADMIT": 0.25, "INTERVIEW": 0.18, "POSITIVE_REPLY": 0.12}
NEGATIVE = {
    "WRONG_PERSON": -0.35,
    "NOT_RECRUITING": -0.18,
    "BOUNCE": -0.16,
    "REJECT": -0.06,
    "NO_REPLY": -0.03,
}


@dataclass(frozen=True)
class OutcomeSignals:
    supervisor_adjustments: dict[str, float]
    institution_adjustments: dict[str, float]
    area_adjustments: dict[str, float]


def load_outcome_signals(path: Path | None) -> OutcomeSignals:
    if not path:
        return OutcomeSignals({}, {}, {})
    supervisor_scores: dict[str, list[float]] = defaultdict(list)
    institution_scores: dict[str, list[float]] = defaultdict(list)
    area_scores: dict[str, list[float]] = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            outcome = (row.get("outcome") or "").strip().upper()
            value = POSITIVE.get(outcome, NEGATIVE.get(outcome, 0.0))
            if row.get("supervisor_id"):
                supervisor_scores[row["supervisor_id"].strip()].append(value)
            if row.get("institution"):
                institution_scores[row["institution"].strip().lower()].append(value / 2)
            if row.get("area"):
                area_scores[row["area"].strip().lower()].append(value / 2)
    return OutcomeSignals(
        supervisor_adjustments=_mean_dict(supervisor_scores),
        institution_adjustments=_mean_dict(institution_scores),
        area_adjustments=_mean_dict(area_scores),
    )


def outcome_adjustment(
    signals: OutcomeSignals,
    *,
    supervisor_id: str,
    institution: str,
    areas: list[str],
) -> float:
    value = signals.supervisor_adjustments.get(supervisor_id, 0.0)
    value += signals.institution_adjustments.get(institution.lower(), 0.0)
    for area in areas:
        value += signals.area_adjustments.get(area.lower(), 0.0) / max(1, len(areas))
    return max(-0.35, min(0.25, value))


def _mean_dict(values: dict[str, list[float]]) -> dict[str, float]:
    return {key: sum(items) / len(items) for key, items in values.items() if items}
