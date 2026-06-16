from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    embedding_model: str = "nomic-embed-text:v1.5"
    ollama_base_url: str = "http://localhost:11434"
    weight_budget: float = 100.0
    llm_provider: str = "off"
    cache_dir: Path = Path(".cache/employer_match")
    calibration_baselines: dict[str, float] = field(default_factory=dict)


DEFAULT_CONFIG = Config()
