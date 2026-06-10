from pathlib import Path

from phd_shortlist.outcomes import load_outcome_signals, outcome_adjustment


def test_outcome_adjustment_penalizes_wrong_person(tmp_path: Path):
    csv_path = tmp_path / "outcomes.csv"
    csv_path.write_text(
        "student_id,supervisor_id,institution,area,sent_at,outcome\n"
        "s1,A1,Example University,hydrogels,2026-01-01,WRONG_PERSON\n",
        encoding="utf-8",
    )
    signals = load_outcome_signals(csv_path)

    assert outcome_adjustment(
        signals,
        supervisor_id="A1",
        institution="Example University",
        areas=["hydrogels"],
    ) < -0.3
