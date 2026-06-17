from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from employer_match.config import Config, DEFAULT_CONFIG
from employer_match.rubric_store import Rubric, collect_level_texts
from employer_match.scorer import l2_normalize_matrix


class EmbeddingDependencyError(RuntimeError):
    """Raised when the configured embedding provider cannot produce embeddings."""


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_CONFIG.embedding_model):
        self.model_name = model_name
        try:
            self._model = SentenceTransformer(model_name)
        except Exception as exc:
            raise EmbeddingDependencyError(
                f"Could not load sentence-transformers model {model_name!r}."
            ) from exc

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=float)
        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return np.asarray(vectors, dtype=float)


@dataclass(frozen=True)
class RubricEmbeddingIndex:
    model_name: str
    rubric_hash: str
    vectors: dict[str, dict[int, np.ndarray]]


def rubric_hash(rubric: Rubric) -> str:
    payload = [
        {
            "competency_id": description.competency_id,
            "level": description.level,
            "text": description.text,
        }
        for description in rubric.level_descriptions
    ]
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def cache_path(config: Config, model_name: str, rubric_digest: str) -> Path:
    safe_model = model_name.replace("/", "__").replace(":", "_")
    return config.cache_dir / f"rubric-{safe_model}-{rubric_digest[:16]}.json"


def build_rubric_index(
    rubric: Rubric, embedder, config: Config = DEFAULT_CONFIG
) -> RubricEmbeddingIndex:
    model_name = getattr(embedder, "model_name", config.embedding_model)
    digest = rubric_hash(rubric)
    path = cache_path(config, model_name, digest)
    if path.exists():
        return load_rubric_index(path)

    texts = collect_level_texts(rubric)
    vectors = l2_normalize_matrix(embedder.embed_texts(texts))
    by_competency: dict[str, dict[int, np.ndarray]] = {}
    for description, vector in zip(rubric.level_descriptions, vectors, strict=True):
        by_competency.setdefault(description.competency_id, {})[description.level] = vector

    index = RubricEmbeddingIndex(
        model_name=model_name,
        rubric_hash=digest,
        vectors=by_competency,
    )
    save_rubric_index(index, path)
    return index


def save_rubric_index(index: RubricEmbeddingIndex, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_name": index.model_name,
        "rubric_hash": index.rubric_hash,
        "vectors": {
            competency_id: {str(level): vector.tolist() for level, vector in level_vectors.items()}
            for competency_id, level_vectors in index.vectors.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def load_rubric_index(path: Path) -> RubricEmbeddingIndex:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RubricEmbeddingIndex(
        model_name=payload["model_name"],
        rubric_hash=payload["rubric_hash"],
        vectors={
            competency_id: {
                int(level): np.asarray(vector, dtype=float)
                for level, vector in level_vectors.items()
            }
            for competency_id, level_vectors in payload["vectors"].items()
        },
    )
