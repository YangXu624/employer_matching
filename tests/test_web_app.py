import json
from pathlib import Path

from employer_match.scorer import CompetencyScore, ScoreResult
from employer_match.web_app import load_sample_jds, match_candidates, score_text_payload
from employer_match.rubric_store import COMPETENCY_ORDER


def fake_score_text(jd_text):
    assert "Coordinate" in jd_text
    return (
        ScoreResult(
            weights={
                "effective_communicator": 20.0,
                "global_citizen": 10.0,
                "creative_innovator": 10.0,
                "critical_thinker": 20.0,
                "reflective_future_focused": 20.0,
                "career_ready": 20.0,
            },
            competencies=[
                CompetencyScore(
                    competency_id=competency_id,
                    level_similarities={level: 0.1 * level for level in range(6)},
                    matched_level=5,
                    peak_similarity=0.5,
                    raw_weight=2.5,
                )
                for competency_id in COMPETENCY_ORDER
            ],
            used_uniform_fallback=False,
        ),
        Path("employer_match/data/rubric.json"),
    )


def test_load_sample_jds_reads_text_files(tmp_path):
    (tmp_path / "alpha.txt").write_text("# Alpha Role\nCoordinate teams.")
    (tmp_path / "beta.txt").write_text("Beta Role\nAnalyze data.")

    samples = load_sample_jds(tmp_path)

    assert [sample["id"] for sample in samples] == ["alpha", "beta"]
    assert samples[0]["title"] == "Alpha Role"
    assert samples[0]["body"] == "# Alpha Role\nCoordinate teams."


def test_score_text_payload_shapes_dashboard_response():
    payload = score_text_payload(
        "Coordinate teams.",
        title="Coordinator",
        score_text=fake_score_text,
    )

    assert payload["title"] == "Coordinator"
    assert payload["overall_score"] == 100
    assert round(sum(payload["weights"].values()), 6) == 100
    assert payload["competencies"][0]["label"] == "Effective Communicator"
    assert payload["competencies"][0]["weight"] == 20.0


def test_score_text_payload_is_json_serializable():
    payload = score_text_payload(
        "Coordinate teams.",
        title="Coordinator",
        score_text=fake_score_text,
    )

    assert json.loads(json.dumps(payload))["title"] == "Coordinator"


def test_match_candidates_includes_user_facing_explanations():
    weights = {
        "effective_communicator": 30,
        "global_citizen": 5,
        "creative_innovator": 5,
        "critical_thinker": 30,
        "reflective_future_focused": 10,
        "career_ready": 20,
    }

    matches = match_candidates(weights)

    assert matches
    first = matches[0]
    assert first["match_reason"]
    assert len(first["strengths"]) == 2
    assert len(first["gaps"]) == 2
    assert {"competency_id", "label", "score", "impact"} <= set(first["strengths"][0])
    assert {"competency_id", "label", "score", "gap"} <= set(first["gaps"][0])
