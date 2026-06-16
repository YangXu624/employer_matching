from __future__ import annotations

from pathlib import Path

from employer_match.config import Config, DEFAULT_CONFIG
from employer_match.embedder import SentenceTransformerEmbedder
from employer_match.rubric_store import load_rubric
from employer_match.scorer import ScoreResult, score_job_description


def score_jd_file(
    jd_path: Path,
    rubric_path: Path | None = None,
    config: Config = DEFAULT_CONFIG,
) -> tuple[ScoreResult, Path]:
    jd_text = jd_path.read_text()
    return score_jd_text(jd_text, rubric_path, config)


def score_jd_text(
    jd_text: str,
    rubric_path: Path | None = None,
    config: Config = DEFAULT_CONFIG,
) -> tuple[ScoreResult, Path]:
    rubric = load_rubric(rubric_path)
    embedder = SentenceTransformerEmbedder(config.embedding_model)
    return score_job_description(jd_text, rubric, embedder, config), rubric_path or Path(
        "employer_match/data/rubric.json"
    )
