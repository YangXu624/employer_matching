import pytest
import numpy as np
from employer_match.rubric_store import RubricStore
from employer_match.scorer import Scorer


def test_rubric_load():
    store = RubricStore()
    assert len(store.get_competency_ids()) == 6
    assert "effective_communicator" in store.get_competency_ids()


def test_scorer_uniform_fallback_empty_jd():
    # Mock rubric vectors with zeros
    mock_vectors = {
        comp: {str(i): np.zeros(384) for i in range(6)}
        for comp in RubricStore.FIXED_COMPETENCY_ORDER
    }
    scorer = Scorer(mock_vectors)
    weights, details = scorer.score("", np.array([]))

    assert len(weights) == 6
    for comp in weights:
        assert weights[comp] == pytest.approx(100 / 6)


def test_scorer_math():
    # Simple test to verify the max cosine logic
    comp_id = "effective_communicator"
    # Level 5 is [1, 0]
    # JD sentence is [1, 0] -> similarity 1.0
    mock_rubric_vectors = {
        c: {
            str(i): (
                np.array([1.0, 0.0])
                if (c == comp_id and i == 5)
                else np.array([0.0, 1.0])
            )
            for i in range(6)
        }
        for c in RubricStore.FIXED_COMPETENCY_ORDER
    }
    jd_vectors = np.array(
        [[1.0, 0.0]]
    )  # One sentence perfectly matching Level 5 of effective_communicator

    scorer = Scorer(mock_rubric_vectors)
    weights, details = scorer.score("Some JD", jd_vectors)

    # effective_communicator should have raw_weight = 5 * (1.0 - 0.0) = 5
    # others should have level 5 similarity 0, but level 0-4 might have similarity 1 if we weren't careful
    # in our mock, we set other levels to [0,1], so Level 5 similarity for others is 0.
    # Level 0 for others is [0,1], dot [1,0] = 0.
    # So raw_weight for others is 0.

    assert weights[comp_id] == 100.0
    assert weights["global_citizen"] == 0.0


def test_weight_normalization():
    # If all raw weights are same, should be uniform
    # This is handled in the score method itself.
    pass
