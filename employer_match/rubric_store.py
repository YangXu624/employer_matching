from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COMPETENCY_ORDER = [
    "effective_communicator",
    "global_citizen",
    "creative_innovator",
    "critical_thinker",
    "reflective_future_focused",
    "career_ready",
]

LEVEL_KEYS = ["0", "1", "2", "3", "4", "5"]


class RubricValidationError(ValueError):
    """Raised when the rubric file cannot be used for scoring."""


@dataclass(frozen=True)
class LevelDescription:
    competency_id: str
    level: int
    text: str


@dataclass(frozen=True)
class Rubric:
    raw: dict[str, Any]
    competency_order: list[str]
    level_descriptions: list[LevelDescription]


def default_rubric_path() -> Path:
    return Path(__file__).parent / "data" / "rubric.json"


def load_rubric(path: Path | str | None = None) -> Rubric:
    rubric_path = Path(path) if path is not None else default_rubric_path()
    raw = json.loads(rubric_path.read_text())
    return validate_rubric(raw)


def validate_rubric(raw: dict[str, Any]) -> Rubric:
    meta = raw.get("_meta")
    if not isinstance(meta, dict):
        raise RubricValidationError("Rubric must contain an _meta object.")

    competency_order = meta.get("competency_order")
    if competency_order != COMPETENCY_ORDER:
        raise RubricValidationError(
            "Rubric _meta.competency_order must match the fixed PathCredits order."
        )

    level_descriptions: list[LevelDescription] = []
    for competency_id in COMPETENCY_ORDER:
        competency = raw.get(competency_id)
        if not isinstance(competency, dict):
            raise RubricValidationError(f"Missing competency object: {competency_id}")

        levels = competency.get("levels")
        if not isinstance(levels, dict):
            raise RubricValidationError(f"Competency {competency_id} must contain levels.")

        missing = [level for level in LEVEL_KEYS if level not in levels]
        if missing:
            raise RubricValidationError(
                f"Competency {competency_id} is missing levels: {', '.join(missing)}"
            )

        for level_key in LEVEL_KEYS:
            text = levels[level_key]
            if not isinstance(text, str) or not text.strip():
                raise RubricValidationError(
                    f"Competency {competency_id} level {level_key} must be non-empty text."
                )
            level_descriptions.append(
                LevelDescription(
                    competency_id=competency_id,
                    level=int(level_key),
                    text=text.strip(),
                )
            )

    return Rubric(
        raw=raw,
        competency_order=list(COMPETENCY_ORDER),
        level_descriptions=level_descriptions,
    )


def collect_level_texts(rubric: Rubric) -> list[str]:
    return [description.text for description in rubric.level_descriptions]
