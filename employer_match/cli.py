import argparse
import json
import sys
from .pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description="Employer Match Phase 0 CLI")
    parser.add_argument(
        "--jd", type=str, required=True, help="Path to the Job Description text file"
    )
    parser.add_argument(
        "--llm",
        type=str,
        default="off",
        choices=["off"],
        help="LLM provider (Phase 0: only 'off' supported)",
    )

    args = parser.parse_args()

    try:
        with open(args.jd, "r") as f:
            jd_text = f.read()
    except Exception as e:
        print(f"Error reading JD file: {e}")
        sys.exit(1)

    pipeline = Pipeline()
    weights, details = pipeline.run(jd_text)

    print("\n=== Employer Weight Vector ===")
    print(json.dumps(weights, indent=2))

    print("\n=== Per-Competency Detail ===")
    for detail in details:
        comp_id = detail["competency_id"]
        print(f"\nCompetency: {comp_id}")
        print(f"  Matched Level:   {detail['matched_level']}")
        print(f"  Peak Similarity: {detail['peak_similarity']:.4f}")
        print("  Level Similarities:")
        for lvl in range(6):
            sim = detail["level_similarities"][str(lvl)]
            print(f"    Level {lvl}: {sim:.4f}")

    if (
        not jd_text.strip()
        or sum(w["raw_weight"] for w in details if "raw_weight" in w) == 0
    ):
        print("\nNote: JD was empty or no signal detected. Returned uniform weights.")


if __name__ == "__main__":
    main()
