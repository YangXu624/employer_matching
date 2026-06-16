from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from employer_match.config import DEFAULT_CONFIG
from employer_match.pipeline import score_jd_file
from employer_match.rubric_store import default_rubric_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score an employer JD against PathCredits rubrics."
    )
    parser.add_argument(
        "--jd", required=True, type=Path, help="Path to a job description text file."
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        default=default_rubric_path(),
        help="Path to rubric JSON. Defaults to packaged PathCredits rubric.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--llm",
        default="off",
        choices=["off"],
        help="Future-compatible LLM switch. Phase 0 only supports 'off'.",
    )
    return parser


def score_result_to_payload(result, rubric_path: Path) -> dict:
    return {
        "model": DEFAULT_CONFIG.embedding_model,
        "rubric_path": str(rubric_path),
        "weights": result.weights,
        "used_uniform_fallback": result.used_uniform_fallback,
        "fallback_reason": result.fallback_reason,
        "competencies": [
            {
                **asdict(competency),
                "level_similarities": {
                    str(level): similarity
                    for level, similarity in competency.level_similarities.items()
                },
            }
            for competency in result.competencies
        ],
    }


def print_human_readable(payload: dict) -> None:
    if payload["used_uniform_fallback"]:
        print(f"Fallback: {payload['fallback_reason']}")
    print("Weights")
    for competency_id, weight in payload["weights"].items():
        print(f"  {competency_id}: {weight:.2f}")
    print("\nCompetency details")
    for competency in payload["competencies"]:
        print(
            f"  {competency['competency_id']}: "
            f"level={competency['matched_level']} "
            f"peak={competency['peak_similarity']:.4f} "
            f"raw={competency['raw_weight']:.4f}"
        )
        similarities = ", ".join(
            f"{level}:{similarity:.4f}"
            for level, similarity in competency["level_similarities"].items()
        )
        print(f"    similarities {similarities}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result, rubric_path = score_jd_file(
        jd_path=args.jd,
        rubric_path=args.rubric,
        config=DEFAULT_CONFIG,
    )
    payload = score_result_to_payload(result, rubric_path)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_human_readable(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
