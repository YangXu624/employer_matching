import pytest

from employer_match.rubric_store import COMPETENCY_ORDER, load_rubric
from employer_match.scorer import normalize_weights, uniform_result


def test_rubric_loads_fixed_competencies():
    rubric = load_rubric()

    assert rubric.competency_order == COMPETENCY_ORDER
    assert len(rubric.level_descriptions) == 36


def test_uniform_fallback_empty_jd_shape():
    result = uniform_result("empty_jd")

    assert len(result.weights) == 6
    assert len(result.competencies) == 6
    for weight in result.weights.values():
        assert weight == pytest.approx(100 / 6)


def test_weight_normalization_exact_budget():
    weights, used_fallback = normalize_weights(
        {
            "effective_communicator": 5,
            "global_citizen": 0,
            "creative_innovator": 0,
        },
        100,
    )

    assert used_fallback is False
    assert weights["effective_communicator"] == 100
    assert sum(weights.values()) == 100
