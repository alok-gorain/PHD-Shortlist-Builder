from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime knobs kept explicit for reproducibility and easy CLI overrides."""

    min_recommendations: int = 50
    max_recommendations: int = 200
    per_area_candidate_limit: int = 80
    works_per_candidate: int = 8
    cache_dir: Path = Path(".cache/phd_shortlist")
    openalex_mailto: str | None = None
    request_timeout_seconds: int = 25
    offline: bool = False
    include_outcome_learning: bool = True
    insecure_skip_tls_verify: bool = False
