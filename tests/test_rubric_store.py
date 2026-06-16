import copy
import json
from pathlib import Path

import pytest

from employer_match.rubric_store import (
    COMPETENCY_ORDER,
    RubricValidationError,
    collect_level_texts,
    load_rubric,
)


def test_loads_provided_rubric_in_fixed_order():
    rubric = load_rubric(Path("employer_match/data/rubric.json"))

    assert rubric.competency_order == COMPETENCY_ORDER
    assert len(rubric.level_descriptions) == 36
    assert rubric.level_descriptions[0].competency_id == "effective_communicator"
    assert rubric.level_descriptions[0].level == 0


def test_rejects_missing_level_key(tmp_path):
    source = json.loads(Path("employer_match/data/rubric.json").read_text())
    broken = copy.deepcopy(source)
    del broken["effective_communicator"]["levels"]["5"]
    rubric_path = tmp_path / "broken_rubric.json"
    rubric_path.write_text(json.dumps(broken))

    with pytest.raises(RubricValidationError, match="levels"):
        load_rubric(rubric_path)


def test_collect_level_texts_excludes_definitions_and_meta():
    rubric = load_rubric(Path("employer_match/data/rubric.json"))
    level_texts = collect_level_texts(rubric)

    assert len(level_texts) == 36
    assert rubric.raw["_meta"]["purpose"] not in level_texts
    for competency_id in COMPETENCY_ORDER:
        assert rubric.raw[competency_id]["definition"] not in level_texts
