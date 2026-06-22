from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from backend.seeker.resume_scorer import PassportScoringError, score_passport_from_resume
from employer_match.rubric_store import COMPETENCY_ORDER

PROJECT_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)

_active_jobs: dict[str, threading.Thread] = {}


class SupabaseConfigError(RuntimeError):
    pass


class AuthError(RuntimeError):
    pass


def _supabase_config() -> tuple[str, str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not service:
        raise SupabaseConfigError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    return url, anon, service


def _service_headers() -> dict[str, str]:
    url, _, service = _supabase_config()
    return {
        "apikey": service,
        "Authorization": f"Bearer {service}",
        "Content-Type": "application/json",
    }


def verify_access_token(access_token: str) -> dict[str, Any]:
    url, anon, _ = _supabase_config()
    if not anon:
        raise SupabaseConfigError("SUPABASE_ANON_KEY must be set in .env")
    headers = {
        "apikey": anon,
        "Authorization": f"Bearer {access_token}",
    }
    response = httpx.get(f"{url}/auth/v1/user", headers=headers, timeout=20)
    if response.status_code != 200:
        raise AuthError("Invalid or expired session.")
    return response.json()


def _rest(method: str, path: str, *, params: dict | None = None, json_body: dict | None = None) -> Any:
    url, _, _ = _supabase_config()
    response = httpx.request(
        method,
        f"{url}/rest/v1/{path}",
        headers=_service_headers(),
        params=params,
        json=json_body,
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(response.text or f"Supabase REST error {response.status_code}")
    if not response.content:
        return None
    return response.json()


def get_profile(user_id: str) -> dict | None:
    rows = _rest(
        "GET",
        "profiles",
        params={"id": f"eq.{user_id}", "select": "id,role,display_name"},
    )
    return rows[0] if rows else None


def get_seeker_passport(user_id: str) -> dict | None:
    rows = _rest(
        "GET",
        "seeker_passports",
        params={"user_id": f"eq.{user_id}", "select": "*"},
    )
    return rows[0] if rows else None


def get_latest_job(user_id: str) -> dict | None:
    rows = _rest(
        "GET",
        "passport_jobs",
        params={
            "user_id": f"eq.{user_id}",
            "select": "*",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def _download_resume(storage_path: str) -> Path:
    url, _, service = _supabase_config()
    response = httpx.get(
        f"{url}/storage/v1/object/resumes/{storage_path}",
        headers={"apikey": service, "Authorization": f"Bearer {service}"},
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Could not download resume: {response.text}")
    temp_dir = Path(tempfile.mkdtemp(prefix="seeker_resume_"))
    pdf_path = temp_dir / "resume.pdf"
    pdf_path.write_bytes(response.content)
    return pdf_path


def _update_passport(user_id: str, payload: dict) -> None:
    _rest(
        "PATCH",
        "seeker_passports",
        params={"user_id": f"eq.{user_id}"},
        json_body={**payload, "updated_at": datetime.now(timezone.utc).isoformat()},
    )


def _update_job(job_id: str, payload: dict) -> None:
    _rest("PATCH", "passport_jobs", params={"id": f"eq.{job_id}"}, json_body=payload)


def _run_job(job_id: str, user_id: str, resume_path: str, display_name: str, email: str | None) -> None:
    pdf_path: Path | None = None
    short_user = user_id[:8]
    try:
        logger.info("Passport job %s started for user %s…", job_id[:8], short_user)
        _update_job(job_id, {"status": "running"})
        _update_passport(user_id, {"status": "processing", "resume_path": resume_path})
        logger.info("Passport job %s: downloading resume from storage…", job_id[:8])
        pdf_path = _download_resume(resume_path)
        logger.info(
            "Passport job %s: scoring resume for %s (this may take 1–2 min)…",
            job_id[:8],
            display_name or "Seeker",
        )
        result = score_passport_from_resume(pdf_path, display_name or "Seeker", email)
        logger.info("Passport job %s: scoring complete for user %s", job_id[:8], short_user)
        _update_passport(
            user_id,
            {
                "status": "complete",
                "scores": result["scores"],
                "details": result["details"],
                "resume_path": resume_path,
            },
        )
        _update_job(
            job_id,
            {"status": "complete", "finished_at": datetime.now(timezone.utc).isoformat(), "error": None},
        )
    except Exception as exc:
        message = str(exc)
        logger.exception("Passport job %s failed for user %s: %s", job_id[:8], short_user, message)
        _update_passport(user_id, {"status": "failed"})
        _update_job(
            job_id,
            {
                "status": "failed",
                "error": message,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    finally:
        if pdf_path is not None:
            shutil.rmtree(pdf_path.parent, ignore_errors=True)
        _active_jobs.pop(job_id, None)


def ensure_seeker_passport(user_id: str) -> None:
    existing = get_seeker_passport(user_id)
    if existing:
        return
    _rest(
        "POST",
        "seeker_passports",
        json_body={
            "user_id": user_id,
            "status": "idle",
            "scores": {},
            "details": {},
        },
    )


def enqueue_passport_job(user_id: str, resume_path: str, email: str | None = None) -> dict:
    profile = get_profile(user_id)
    if not profile or profile.get("role") != "seeker":
        raise AuthError("Only seekers can generate passports.")

    ensure_seeker_passport(user_id)

    job_id = str(uuid.uuid4())
    _rest(
        "POST",
        "passport_jobs",
        json_body={
            "id": job_id,
            "user_id": user_id,
            "status": "queued",
        },
    )
    _update_passport(user_id, {"status": "processing", "resume_path": resume_path})
    logger.info("Queued passport job %s for user %s (%s)", job_id[:8], user_id[:8], resume_path)

    thread = threading.Thread(
        target=_run_job,
        args=(
            job_id,
            user_id,
            resume_path,
            profile.get("display_name") or "Seeker",
            email,
        ),
        daemon=True,
    )
    _active_jobs[job_id] = thread
    thread.start()
    return {"job_id": job_id, "status": "queued"}


def reconcile_orphaned_job(user_id: str, job: dict | None) -> dict | None:
    """Mark jobs left queued/running after a server restart as failed."""
    if not job or job.get("status") not in ("queued", "running"):
        return job
    job_id = job["id"]
    if job_id in _active_jobs and _active_jobs[job_id].is_alive():
        return job

    message = "Scoring was interrupted (server restarted or job crashed). Upload your resume again."
    logger.warning("Orphaned passport job %s for user %s — marking failed", job_id[:8], user_id[:8])
    _update_job(
        job_id,
        {
            "status": "failed",
            "error": message,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    passport = get_seeker_passport(user_id)
    if passport and passport.get("status") == "processing":
        _update_passport(user_id, {"status": "failed"})
    return get_latest_job(user_id)


def passport_status_payload(user_id: str) -> dict:
    job = reconcile_orphaned_job(user_id, get_latest_job(user_id))
    passport = get_seeker_passport(user_id) or {"status": "idle", "scores": {}, "details": {}}
    return {"passport": passport, "job": job}


def load_supabase_candidates() -> list[dict]:
    try:
        _supabase_config()
    except SupabaseConfigError:
        return []

    try:
        rows = _rest(
            "GET",
            "seeker_passports",
            params={
                "status": "eq.complete",
                "select": "user_id,scores,details",
            },
        )
    except RuntimeError:
        return []

    profiles_by_id: dict[str, str] = {}
    try:
        profile_rows = _rest("GET", "profiles", params={"role": "eq.seeker", "select": "id,display_name"})
        for profile in profile_rows or []:
            profiles_by_id[profile["id"]] = profile.get("display_name") or "Seeker"
    except RuntimeError:
        profiles_by_id = {}

    candidates: list[dict] = []
    for row in rows or []:
        scores = row.get("scores") or {}
        if not scores:
            continue
        user_id = row.get("user_id")
        name = profiles_by_id.get(user_id) or f"Seeker {str(user_id or '')[:8]}"
        candidate_scores = {
            competency_id: float(scores.get(competency_id, 0)) for competency_id in COMPETENCY_ORDER
        }
        candidates.append(
            {
                "name": name,
                "source": "seeker",
                "user_id": user_id,
                "scores": candidate_scores,
            }
        )
    return candidates


def load_demo_seekers() -> list[dict]:
    try:
        _supabase_config()
    except SupabaseConfigError:
        return []

    try:
        rows = _rest("GET", "demo_seekers", params={"select": "name,scores"})
    except RuntimeError:
        return []

    candidates: list[dict] = []
    for row in rows or []:
        scores = row.get("scores") or {}
        if not scores:
            continue
        candidates.append(
            {
                "name": row.get("name") or "Demo seeker",
                "source": "demo",
                "scores": {
                    competency_id: float(scores.get(competency_id, 0))
                    for competency_id in COMPETENCY_ORDER
                },
            }
        )
    return candidates
