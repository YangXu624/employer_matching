from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from employer_match.config import Config, DEFAULT_CONFIG
from employer_match.rubric_store import COMPETENCY_ORDER, LEVEL_KEYS, Rubric


@dataclass(frozen=True)
class CompetencyScore:
    competency_id: str
    level_similarities: dict[int, float]
    matched_level: int
    peak_similarity: float
    raw_weight: float


@dataclass(frozen=True)
class ScoreResult:
    weights: dict[str, float]
    competencies: list[CompetencyScore]
    used_uniform_fallback: bool
    fallback_reason: str | None = None


def l2_normalize_matrix(vectors: np.ndarray) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return np.divide(matrix, norms, out=np.zeros_like(matrix, dtype=float), where=norms != 0)


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_normalized = l2_normalize_matrix(np.asarray(left, dtype=float))[0]
    right_normalized = l2_normalize_matrix(np.asarray(right, dtype=float))[0]
    return float(np.dot(left_normalized, right_normalized))


def split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return [part.strip() for part in re.findall(r"[^.!?]+[.!?]?", normalized) if part.strip()]


def normalize_weights(
    raw_weights: dict[str, float], budget: float
) -> tuple[dict[str, float], bool]:
    keys = list(raw_weights)
    total = sum(max(weight, 0.0) for weight in raw_weights.values())
    if total <= 0:
        equal_weight = budget / len(raw_weights)
        weights = {key: equal_weight for key in keys}
    else:
        weights = {key: max(raw_weights[key], 0.0) / total * budget for key in keys}

    if keys:
        weights[keys[-1]] += budget - sum(weights.values())
    return weights, total <= 0


def uniform_result(reason: str, budget: float = DEFAULT_CONFIG.weight_budget) -> ScoreResult:
    weights, _ = normalize_weights({key: 0.0 for key in COMPETENCY_ORDER}, budget)
    competencies = [
        CompetencyScore(
            competency_id=competency_id,
            level_similarities={int(level): 0.0 for level in LEVEL_KEYS},
            matched_level=0,
            peak_similarity=0.0,
            raw_weight=0.0,
        )
        for competency_id in COMPETENCY_ORDER
    ]
    return ScoreResult(
        weights=weights,
        competencies=competencies,
        used_uniform_fallback=True,
        fallback_reason=reason,
    )


def score_job_description(
    jd_text: str,
    rubric: Rubric,
    embedder,
    config: Config = DEFAULT_CONFIG,
    rubric_index=None,
) -> ScoreResult:
    sentences = split_sentences(jd_text)
    if not sentences:
        return uniform_result("empty_jd", config.weight_budget)

    if rubric_index is None:
        from employer_match.embedder import build_rubric_index

        rubric_index = build_rubric_index(rubric, embedder, config)

    sentence_vectors = l2_normalize_matrix(embedder.embed_texts(sentences))
    competency_scores: list[CompetencyScore] = []
    raw_weights: dict[str, float] = {}

    for competency_id in rubric.competency_order:
        level_similarities = {}
        for level in range(6):
            level_vector = rubric_index.vectors[competency_id][level]
            similarities = sentence_vectors @ level_vector
            level_similarities[level] = float(np.max(similarities))

        matched_level = max(
            level_similarities, key=lambda level: (level_similarities[level], level)
        )
        peak_similarity = level_similarities[matched_level]
        baseline = config.calibration_baselines.get(competency_id, 0.0)
        raw_weight = matched_level * max(peak_similarity - baseline, 0.0)
        raw_weights[competency_id] = raw_weight
        competency_scores.append(
            CompetencyScore(
                competency_id=competency_id,
                level_similarities=level_similarities,
                matched_level=matched_level,
                peak_similarity=peak_similarity,
                raw_weight=raw_weight,
            )
        )

    weights, used_fallback = normalize_weights(raw_weights, config.weight_budget)
    return ScoreResult(
        weights=weights,
        competencies=competency_scores,
        used_uniform_fallback=used_fallback,
        fallback_reason="zero_signal" if used_fallback else None,
    )
