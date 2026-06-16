import json
from pathlib import Path

from employer_match.cli import main
from employer_match.scorer import CompetencyScore, ScoreResult


def test_cli_exits_successfully_with_sentence_transformer_pipeline(monkeypatch, capsys):
    def fake_score_jd_file(jd_path, rubric_path, config):
        assert jd_path == Path("sample_jd.txt")
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
                        competency_id="effective_communicator",
                        level_similarities={level: 0.1 * level for level in range(6)},
                        matched_level=5,
                        peak_similarity=0.5,
                        raw_weight=2.5,
                    )
                ],
                used_uniform_fallback=False,
            ),
            Path("employer_match/data/rubric.json"),
        )

    monkeypatch.setattr("employer_match.cli.score_jd_file", fake_score_jd_file)

    exit_code = main(["--jd", "sample_jd.txt", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["weights"]) == 6
    assert round(sum(payload["weights"].values()), 6) == 100
    assert len(payload["competencies"]) == 1
    assert Path(payload["rubric_path"]).name == "rubric.json"
    assert payload["model"] == "BAAI/bge-base-en-v1.5"
