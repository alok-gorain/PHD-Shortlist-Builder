from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from phd_shortlist.models.schema import StudentProfile

T = TypeVar("T", bound=BaseModel)


def read_student_profile(path: Path) -> StudentProfile:
    with path.open("r", encoding="utf-8") as handle:
        return StudentProfile.model_validate(json.load(handle))


def write_json_model(model: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(model.model_dump_json(indent=2, exclude_none=True))
        handle.write("\n")


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
