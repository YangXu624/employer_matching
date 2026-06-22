"""Generate supabase/seed.sql from repo sample JDs and candidates.csv."""

from __future__ import annotations

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JD_DIR = PROJECT_ROOT / "examples" / "jds"
CSV_PATH = PROJECT_ROOT / "employer_match" / "data" / "candidates.csv"
OUT_PATH = PROJECT_ROOT / "supabase" / "seed.sql"

KEYS = [
    "effective_communicator",
    "global_citizen",
    "creative_innovator",
    "critical_thinker",
    "reflective_future_focused",
    "career_ready",
]


def sql_str(value: str) -> str:
    return value.replace("'", "''")


def main() -> None:
    lines = [
        "-- Run after migration.sql and migration_v2_jobs.sql",
        "truncate public.demo_seekers cascade;",
        "truncate public.sample_jds cascade;",
        "",
    ]

    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if index >= 5:
                break
            scores = {key: int(row[key]) for key in KEYS}
            name = sql_str(row["name"])
            lines.append(
                "insert into public.demo_seekers (name, scores) values "
                f"('{name}', '{json.dumps(scores)}'::jsonb);"
            )

    lines.append("")
    for index, path in enumerate(sorted(JD_DIR.glob("*.txt"))):
        body = path.read_text(encoding="utf-8")
        title = next((line.strip() for line in body.splitlines() if line.strip()), path.stem)
        lines.append(
            "insert into public.sample_jds (id, title, body, sort_order) values "
            f"('{sql_str(path.stem)}', '{sql_str(title[:200])}', $jd${body}$jd$, {index});"
        )

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
