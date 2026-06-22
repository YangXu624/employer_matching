import json
from pathlib import Path

from employer_match.scorer import CompetencyScore, ScoreResult
from employer_match.web_app import load_sample_jds, match_candidates, score_text_payload
from employer_match.rubric_store import COMPETENCY_ORDER


def fake_score_text(jd_text):
    assert "Coordinate" in jd_text
    weights = {competency_id: 12.5 for competency_id in COMPETENCY_ORDER}
    return (
        ScoreResult(
            weights=weights,
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
    assert payload["competencies"][0]["label"] == "Career & Self-Development"
    assert payload["competencies"][0]["weight"] == 12.5


def test_score_text_payload_is_json_serializable():
    payload = score_text_payload(
        "Coordinate teams.",
        title="Coordinator",
        score_text=fake_score_text,
    )

    assert json.loads(json.dumps(payload))["title"] == "Coordinator"


def test_match_candidates_includes_user_facing_explanations():
    weights = {
        "career_self_development": 10,
        "communication": 20,
        "critical_thinking": 20,
        "equity_inclusion": 5,
        "leadership": 10,
        "professionalism": 15,
        "teamwork": 10,
        "technology": 10,
    }

    matches = match_candidates(weights)

    assert matches
    first = matches[0]
    assert first["match_reason"]
    assert len(first["strengths"]) == 2
    assert len(first["gaps"]) == 2
    assert {"competency_id", "label", "score", "impact"} <= set(first["strengths"][0])
    assert {"competency_id", "label", "score", "gap"} <= set(first["gaps"][0])
