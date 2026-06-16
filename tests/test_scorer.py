import numpy as np

from employer_match.config import DEFAULT_CONFIG
from employer_match.embedder import SentenceTransformerEmbedder, build_rubric_index
from employer_match.rubric_store import COMPETENCY_ORDER, LevelDescription, Rubric
from employer_match.scorer import (
    cosine_similarity,
    normalize_weights,
    score_job_description,
    split_sentences,
)


class FakeEmbedder:
    def __init__(self):
        self.model_name = "fake-embedder"
        self.calls = 0
        self.vectors = {
            "communication": [1.0, 0.0],
            "analysis": [0.0, 1.0],
            "routine": [-1.0, 0.0],
            "The role requires communication and client presentations.": [1.0, 0.0],
            "It also requires structured analysis.": [0.0, 1.0],
        }

    def embed_texts(self, texts):
        self.calls += 1
        return np.array([self.vectors.get(text, [0.0, 0.0]) for text in texts], dtype=float)


def make_test_rubric():
    descriptions = []
    for competency_id in COMPETENCY_ORDER:
        descriptions.extend(
            [
                LevelDescription(competency_id, 1, "routine"),
                LevelDescription(competency_id, 2, "analysis"),
                LevelDescription(competency_id, 3, "analysis"),
                LevelDescription(competency_id, 4, "communication"),
                LevelDescription(competency_id, 5, "communication"),
            ]
        )
    return Rubric(
        raw={},
        competency_order=COMPETENCY_ORDER,
        level_descriptions=descriptions,
    )


def test_cosine_similarity_uses_normalized_vectors():
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 1.0
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == 0.0


def test_normalize_weights_sums_to_budget():
    weights, used_fallback = normalize_weights({"a": 1.0, "b": 3.0}, 100)

    assert used_fallback is False
    assert weights == {"a": 25.0, "b": 75.0}
    assert sum(weights.values()) == 100


def test_normalize_weights_returns_uniform_for_zero_signal():
    weights, used_fallback = normalize_weights({"a": 0.0, "b": 0.0}, 100)

    assert used_fallback is True
    assert weights == {"a": 50.0, "b": 50.0}


def test_empty_jd_returns_graceful_uniform_fallback():
    result = score_job_description("", make_test_rubric(), FakeEmbedder(), DEFAULT_CONFIG)

    assert result.used_uniform_fallback is True
    assert result.fallback_reason == "empty_jd"
    assert sum(result.weights.values()) == 100
    assert set(result.weights) == set(COMPETENCY_ORDER)


def test_scoring_returns_six_competency_results_with_weights():
    result = score_job_description(
        "The role requires communication and client presentations. It also requires structured analysis.",
        make_test_rubric(),
        FakeEmbedder(),
        DEFAULT_CONFIG,
    )

    assert result.used_uniform_fallback is False
    assert sum(result.weights.values()) == 100
    assert len(result.competencies) == 6
    assert result.competencies[0].matched_level == 5
    assert result.competencies[0].peak_similarity == 1.0
    assert set(result.competencies[0].level_similarities) == {1, 2, 3, 4, 5}


def test_split_sentences_handles_punctuation_and_whitespace():
    assert split_sentences(" One sentence. Two? Three! ") == [
        "One sentence.",
        "Two?",
        "Three!",
    ]


def test_rubric_index_is_reused_from_cache(tmp_path):
    config = DEFAULT_CONFIG.__class__(
        embedding_model=DEFAULT_CONFIG.embedding_model,
        weight_budget=DEFAULT_CONFIG.weight_budget,
        llm_provider=DEFAULT_CONFIG.llm_provider,
        cache_dir=tmp_path,
    )
    rubric = make_test_rubric()
    embedder = FakeEmbedder()

    first = build_rubric_index(rubric, embedder, config)
    second = build_rubric_index(rubric, embedder, config)

    assert embedder.calls == 1
    assert first.rubric_hash == second.rubric_hash
    assert (tmp_path / f"rubric-fake-embedder-{first.rubric_hash[:16]}.json").exists()


def test_default_embedder_uses_sentence_transformers_model(monkeypatch):
    created_models = []

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            created_models.append(model_name)

        def encode(self, texts, convert_to_numpy, normalize_embeddings):
            assert convert_to_numpy is True
            assert normalize_embeddings is False
            return np.array([[1.0, 2.0] for _ in texts])

    monkeypatch.setattr(
        "employer_match.embedder.SentenceTransformer",
        FakeSentenceTransformer,
    )

    embedder = SentenceTransformerEmbedder()

    assert created_models == ["BAAI/bge-base-en-v1.5"]
    assert embedder.model_name == "BAAI/bge-base-en-v1.5"
    assert embedder.embed_texts(["hello"]).tolist() == [[1.0, 2.0]]
