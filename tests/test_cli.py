import json
import subprocess
import sys
from pathlib import Path


def test_cli_exits_successfully_with_ollama_embedder():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "employer_match.cli",
            "--jd",
            "examples/sample_jd.txt",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["weights"]) == 6
    assert round(sum(payload["weights"].values()), 6) == 100
    assert len(payload["competencies"]) == 6
    assert Path(payload["rubric_path"]).name == "rubric.json"
