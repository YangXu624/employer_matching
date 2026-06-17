from __future__ import annotations

import argparse
import csv
import json
import mimetypes
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from employer_match.pipeline import score_jd_text
from employer_match.rubric_store import COMPETENCY_ORDER

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_SAMPLE_DIRS = [PROJECT_ROOT / "examples", PROJECT_ROOT / "examples" / "jds"]

COMPETENCY_LABELS = {
    "effective_communicator": "Effective Communicator",
    "global_citizen": "Global Citizen",
    "creative_innovator": "Creative Innovator",
    "critical_thinker": "Critical Thinker",
    "reflective_future_focused": "Reflective Future-Focused",
    "career_ready": "Career Ready",
}


def title_from_sample(path: Path, body: str) -> str:
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip()
    if first_line:
        return first_line[:80]
    return path.stem.replace("_", " ").replace("-", " ").title()


def load_sample_jds(sample_dir: Path | None = None) -> list[dict]:
    paths: list[Path] = []
    if sample_dir is not None:
        paths.extend(sorted(sample_dir.glob("*.txt")))
    else:
        for directory in DEFAULT_SAMPLE_DIRS:
            if directory.exists():
                paths.extend(sorted(directory.glob("*.txt")))

    samples = []
    seen_ids = set()
    for path in paths:
        sample_id = path.stem
        if sample_id in seen_ids:
            continue
        body = path.read_text()
        try:
            display_path = str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            display_path = str(path)
        samples.append(
            {
                "id": sample_id,
                "title": title_from_sample(path, body),
                "body": body,
                "path": display_path,
            }
        )
        seen_ids.add(sample_id)
    return samples


def score_text_payload(
    jd_text: str,
    title: str = "Untitled JD",
    score_text: Callable = score_jd_text,
) -> dict:
    result, rubric_path = score_text(jd_text)
    competency_payloads = []
    for competency in result.competencies:
        weight = result.weights.get(competency.competency_id, 0.0)
        competency_payloads.append(
            {
                **asdict(competency),
                "label": COMPETENCY_LABELS.get(
                    competency.competency_id, competency.competency_id.replace("_", " ").title()
                ),
                "weight": weight,
                "level_similarities": {
                    str(level): similarity
                    for level, similarity in competency.level_similarities.items()
                },
            }
        )

    overall_score = 0.0
    if result.weights:
        overall_score = sum(
            result.weights.get(competency.competency_id, 0.0) * (competency.matched_level / 5)
            for competency in result.competencies
        )

    return {
        "title": title.strip() or "Untitled JD",
        "overall_score": round(overall_score),
        "model": "BAAI/bge-base-en-v1.5",
        "rubric_path": str(rubric_path),
        "weights": {
            competency_id: result.weights[competency_id] for competency_id in COMPETENCY_ORDER
        },
        "used_uniform_fallback": result.used_uniform_fallback,
        "fallback_reason": result.fallback_reason,
        "competencies": competency_payloads,
    }


def load_candidates() -> list[dict]:
    candidates_path = PROJECT_ROOT / "employer_match" / "data" / "candidates.csv"
    candidates = []
    if candidates_path.exists():
        with open(candidates_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidates.append({
                    "name": row["name"],
                    "scores": {
                        "effective_communicator": float(row["effective_communicator"]),
                        "global_citizen": float(row["global_citizen"]),
                        "creative_innovator": float(row["creative_innovator"]),
                        "critical_thinker": float(row["critical_thinker"]),
                        "reflective_future_focused": float(row["reflective_future_focused"]),
                        "career_ready": float(row["career_ready"])
                    }
                })
    return candidates

def match_candidates(weights: dict[str, float]) -> list[dict]:
    candidates = load_candidates()
    total_weight = sum(weights.values())
    
    for cand in candidates:
        match_score = 0.0
        if total_weight > 0:
            match_score = sum(weights.get(c, 0) * cand["scores"].get(c, 0) for c in COMPETENCY_ORDER) / total_weight
        cand["match_score"] = round(match_score, 1)
        
    # Sort descending by match_score
    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return candidates[:5]


class EmployerMatchHandler(BaseHTTPRequestHandler):
    server_version = "EmployerMatchMVP/0.1"

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self.serve_static("index.html")
            return
        if self.path == "/api/samples":
            self.write_json({"samples": load_sample_jds()})
            return
        if self.path.startswith("/static/"):
            self.serve_static(self.path.removeprefix("/static/"))
            return
        self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/match":
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                weights = payload.get("weights", {})
                matches = match_candidates(weights)
                self.write_json({"matches": matches})
            except Exception as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path != "/api/score":
            self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.write_json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return

        jd_text = str(payload.get("jd_text", ""))
        title = str(payload.get("title", "Untitled JD"))
        try:
            self.write_json(score_text_payload(jd_text, title))
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def serve_static(self, relative_path: str) -> None:
        path = (STATIC_DIR / relative_path).resolve()
        if not path.is_file() or STATIC_DIR.resolve() not in path.parents:
            self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), EmployerMatchHandler)
    print(f"Employer Match UI running at http://{host}:{port}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Employer Match MVP web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args(argv)
    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
