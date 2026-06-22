from __future__ import annotations

import argparse
import json
import logging
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from backend.api.storage import list_checks, save_check  # noqa: E402
from backend.seeker.passport_service import (  # noqa: E402
    AuthError,
    SupabaseConfigError,
    enqueue_passport_job,
    get_seeker_passport,
    load_demo_seekers,
    load_supabase_candidates,
    passport_status_payload,
    verify_access_token,
)
from employer_match.web_app import load_sample_jds, match_candidates, score_text_payload  # noqa: E402


class EmployerMatchApiHandler(BaseHTTPRequestHandler):
    server_version = "EmployerMatchAPI/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.write_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self.write_json({"ok": True})
            return
        if path == "/api/samples":
            self.write_json({"samples": load_sample_jds()})
            return
        if path == "/api/checks":
            self.write_json({"checks": list_checks()})
            return
        if path == "/api/seeker/passport":
            self.handle_seeker_passport_get()
            return
        if path == "/api/seeker/passport/status":
            self.handle_seeker_passport_status()
            return
        self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

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

        if path == "/api/match":
            payload = self.read_json()
            try:
                weights = payload.get("weights", {})
                demo_candidates = load_demo_seekers()
                live_candidates = load_supabase_candidates()
                include_csv_demo = not demo_candidates
                extra = live_candidates + demo_candidates
                self.write_json(
                    {
                        "matches": match_candidates(
                            weights,
                            extra,
                            include_csv_demo=include_csv_demo,
                        )
                    }
                )
            except Exception as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/seeker/passport":
            self.handle_seeker_passport_post()
            return

        if path == "/api/audit":
            payload = self.read_json()
            try:
                from backend.agent.llm import MissingApiKeyError
                from backend.agent.weight_auditor import audit_weights

                jd_text = str(payload.get("jd_text", ""))
                weights = payload.get("weights", {})
                signals = {
                    str(c.get("competency_id")): {
                        "matched_level": c.get("matched_level"),
                        "peak_similarity": c.get("peak_similarity"),
                    }
                    for c in payload.get("competencies", [])
                    if c.get("competency_id")
                }
                self.write_json(audit_weights(jd_text, weights, signals))
            except MissingApiKeyError as exc:
                self.write_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
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

        self.write_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

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
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, ngrok-skip-browser-warning",
        )

    def read_bearer_token(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        return None

    def require_seeker_user(self) -> dict | None:
        token = self.read_bearer_token()
        if not token:
            self.write_json({"error": "Missing Authorization bearer token."}, HTTPStatus.UNAUTHORIZED)
            return None
        try:
            user = verify_access_token(token)
        except AuthError as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.UNAUTHORIZED)
            return None
        except SupabaseConfigError as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return None
        return user

    def handle_seeker_passport_get(self) -> None:
        user = self.require_seeker_user()
        if not user:
            return
        logging.getLogger("http").info("GET /api/seeker/passport user=%s", user["id"][:8])
        try:
            passport = get_seeker_passport(user["id"]) or {
                "status": "idle",
                "scores": {},
                "details": {},
            }
            if passport.get("status") == "processing":
                payload = passport_status_payload(user["id"])
                passport = payload["passport"]
            self.write_json({"passport": passport})
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_seeker_passport_status(self) -> None:
        user = self.require_seeker_user()
        if not user:
            return
        logging.getLogger("http").info("GET /api/seeker/passport/status user=%s", user["id"][:8])
        try:
            self.write_json(passport_status_payload(user["id"]))
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_seeker_passport_post(self) -> None:
        user = self.require_seeker_user()
        if not user:
            return
        payload = self.read_json()
        resume_path = str(payload.get("resume_path", "")).strip()
        logging.getLogger("http").info(
            "POST /api/seeker/passport user=%s resume=%s",
            user["id"][:8],
            resume_path or "(missing)",
        )
        if not resume_path:
            self.write_json({"error": "resume_path is required."}, HTTPStatus.BAD_REQUEST)
            return
        expected_prefix = f"{user['id']}/"
        if not resume_path.startswith(expected_prefix):
            self.write_json({"error": "Invalid resume_path for this user."}, HTTPStatus.FORBIDDEN)
            return
        try:
            job = enqueue_passport_job(user["id"], resume_path, user.get("email"))
            logging.getLogger("http").info(
                "POST /api/seeker/passport queued job=%s",
                job.get("job_id", "")[:8],
            )
            self.write_json(job, HTTPStatus.ACCEPTED)
        except AuthError as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
        except Exception as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args) -> None:
        logging.getLogger("http").info("%s - %s", self.address_string(), format % args)


def run_server(host: str = "127.0.0.1", port: int = 8766) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    server = ThreadingHTTPServer((host, port), EmployerMatchApiHandler)
    print(f"Employer Match API running at http://{host}:{port}", flush=True)
    print("Passport scoring logs appear here when a seeker uploads a resume.", flush=True)
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
