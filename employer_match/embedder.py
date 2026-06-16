from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from employer_match.config import Config, DEFAULT_CONFIG
from employer_match.rubric_store import Rubric, collect_level_texts
from employer_match.scorer import l2_normalize_matrix


class EmbeddingDependencyError(RuntimeError):
    """Raised when the configured embedding provider cannot produce embeddings."""


class OllamaEmbedder:
    def __init__(
        self,
        model_name: str = DEFAULT_CONFIG.embedding_model,
        base_url: str = DEFAULT_CONFIG.ollama_base_url,
        timeout_seconds: int = 120,
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=float)
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=json.dumps({"model": self.model_name, "input": texts}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise EmbeddingDependencyError(
                "Could not reach Ollama at "
                f"{self.base_url}. Start it with `brew services start ollama`."
            ) from exc

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise EmbeddingDependencyError(
                f"Ollama response did not include embeddings for model {self.model_name}."
            )
        return np.asarray(embeddings, dtype=float)


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
    payload = json.loads(path.read_text())
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
