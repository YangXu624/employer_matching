from __future__ import annotations
import json
from pathlib import Path
from employer_match.web_app import load_sample_jds, score_text_payload


def generate_sample_results():
    samples = load_sample_jds()
    results = {}

    better_titles = {
        "fbi": "FBI Police Officer",
        "moomoo": "Moomoo Financial CX Associate",
        "tiktok": "TikTok Technology Audit Lead",
    }

    for sample in samples:
        title = better_titles.get(sample["id"], sample["title"])
        print(f"Scoring {title}...")
        result = score_text_payload(sample["body"], title=title)
        results[sample["id"]] = result

    output_path = Path("employer_match/data/sample_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    generate_sample_results()
