from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    weight_budget: float = 100.0
    llm_provider: str = "off"
    cache_dir: Path = Path(".cache/employer_match")
    calibration_baselines: dict[str, float] = field(default_factory=dict)


DEFAULT_CONFIG = Config()
