from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FRONTEND_DIR = PROJECT_ROOT / "frontend"

from backend.api.storage import list_checks, save_check  # noqa: E402
from backend.db import JobValidationError, get_job_store  # noqa: E402
from employer_match.web_app import llm_score_text_payload, load_sample_jds, match_candidates, score_text_payload  # noqa: E402


class EmployerMatchApiHandler(BaseHTTPRequestHandler):
    server_version = "EmployerMatchAPI/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.write_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self.write_json({"ok": True})
            return
        if path == "/api/samples":
            self.write_json({"samples": load_sample_jds()})
            return
        if path == "/api/checks":
            self.write_json({"checks": list_checks()})
            return
        if path == "/api/jobs":
            self.handle_list_jobs(parse_qs(parsed.query))
            return
        if path.startswith("/api/jobs/"):
            self.handle_get_job(path[len("/api/jobs/"):])
            return
        self.serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/score":
            payload = self.read_json()
            jd_text = str(payload.get("jd_text", ""))
            title = str(payload.get("title", "Untitled JD"))
            try:
                self.write_json(score_text_payload(jd_text, title))
            except Exception as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/llm-score":
            payload = self.read_json()
            jd_text = str(payload.get("jd_text", ""))
            title = str(payload.get("title", "Untitled JD"))
            try:
                self.write_json(llm_score_text_payload(jd_text, title))
            except Exception as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/match":
            payload = self.read_json()
            try:
                weights = payload.get("weights", {})
                self.write_json({"matches": match_candidates(weights)})
            except Exception as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/checks":
            payload = self.read_json()
            try:
                check = save_check(
                    title=str(payload.get("title", "Untitled JD")),
                    jd_text=str(payload.get("jd_text", "")),
                    score=dict(payload.get("score", {})),
                    matches=payload.get("matches"),
                )
                self.write_json({"check": check}, HTTPStatus.CREATED)
            except Exception as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/jobs":
            self.handle_create_job(self.read_json())
            return

        self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def handle_create_job(self, payload: dict) -> None:
        try:
            job = get_job_store().create_job(
                title=str(payload.get("title", "Untitled JD")),
                jd_text=str(payload.get("jd_text", "")),
                weights=payload.get("weights", {}),
                score=payload.get("score") or {},
                status=str(payload.get("status", "published")),
            )
            self.write_json({"job": job}, HTTPStatus.CREATED)
        except JobValidationError as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_list_jobs(self, query: dict[str, list[str]]) -> None:
        status_values = query.get("status", ["published"])
        status = status_values[0] if status_values else "published"
        if status.lower() in ("", "all"):
            status = None
        try:
            limit = int(query.get("limit", ["100"])[0])
        except (TypeError, ValueError):
            limit = 100
        try:
            jobs = get_job_store().list_jobs(status=status, limit=limit)
            self.write_json({"jobs": jobs})
        except JobValidationError as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_get_job(self, job_id: str) -> None:
        job_id = job_id.strip("/")
        if not job_id:
            self.write_json({"error": "Missing job id"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            job = get_job_store().get_job(job_id)
            self.write_json({"job": job})
        except KeyError:
            self.write_json({"error": "Job not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.write_json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return {}

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.write_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, ngrok-skip-browser-warning")

    def log_message(self, format: str, *args) -> None:
        return

    def serve_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        # Strip leading slash and resolve relative to frontend dir
        relative = path.lstrip("/")
        file_path = (FRONTEND_DIR / relative).resolve()
        # Prevent directory traversal
        if not file_path.is_file() or FRONTEND_DIR.resolve() not in file_path.parents:
            self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.write_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "127.0.0.1", port: int = 8766) -> None:
    server = ThreadingHTTPServer((host, port), EmployerMatchApiHandler)
    print(f"Employer Match API running at http://{host}:{port}", flush=True)
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Employer Match API service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8766, type=int)
    args = parser.parse_args(argv)
    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
