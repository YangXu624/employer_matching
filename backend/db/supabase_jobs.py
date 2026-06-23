"""Supabase-backed JobStore. The ONLY module that knows Supabase URLs/headers.

Talks to Supabase PostgREST over HTTPS using the service_role key, which lives
on the backend only and is never exposed to the browser. Uses the stdlib
`urllib` so no extra dependency (supabase SDK) is required.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.db.jobs import (
    JobValidationError,
    build_competencies,
    normalize_status,
    validate_weights,
)

_RETURNED_COLUMNS = (
    "id,title,jd_text,weights,competencies,score,status,created_at,updated_at"
)


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase credentials are missing or malformed."""


class SupabaseJobStore:
    def __init__(
        self,
        url: str | None = None,
        service_role_key: str | None = None,
        *,
        table: str = "jobs",
        timeout: float = 15.0,
    ) -> None:
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.service_role_key = service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.table = table
        self.timeout = timeout
        if not self.url or not self.service_role_key:
            raise SupabaseConfigError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use the "
                "Supabase job store."
            )

    def _endpoint(self, query: str = "") -> str:
        base = f"{self.url}/rest/v1/{self.table}"
        return f"{base}?{query}" if query else base

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, url: str, *, body: Any = None, headers=None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            url, data=data, method=method, headers=self._headers(headers)
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Supabase request failed ({exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach Supabase: {exc.reason}") from exc
        if not raw:
            return None
        return json.loads(raw)

    def create_job(
        self,
        *,
        title: str,
        jd_text: str,
        weights: dict[str, float],
        score: dict[str, Any] | None = None,
        status: str = "published",
    ) -> dict[str, Any]:
        clean_title = (title or "").strip() or "Untitled JD"
        if not (jd_text or "").strip():
            raise JobValidationError("jd_text must not be empty.")

        clean_weights = validate_weights(weights)
        clean_status = normalize_status(status)
        score = score or {}
        competencies = build_competencies(clean_weights, score)

        row = {
            "title": clean_title,
            "jd_text": jd_text,
            "weights": clean_weights,
            "competencies": competencies,
            "score": score,
            "status": clean_status,
        }
        result = self._request(
            "POST",
            self._endpoint(f"select={_RETURNED_COLUMNS}"),
            body=row,
            headers={"Prefer": "return=representation"},
        )
        if not result:
            raise RuntimeError("Supabase did not return the created job row.")
        return result[0]

    def list_jobs(
        self, *, status: str | None = "published", limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        params = [
            ("select", _RETURNED_COLUMNS),
            ("order", "created_at.desc"),
            ("limit", str(limit)),
        ]
        if status:
            params.append(("status", f"eq.{normalize_status(status)}"))
        query = urllib.parse.urlencode(params)
        result = self._request("GET", self._endpoint(query))
        return list(result or [])

    def get_job(self, job_id: str) -> dict[str, Any]:
        params = [
            ("select", _RETURNED_COLUMNS),
            ("id", f"eq.{job_id}"),
            ("limit", "1"),
        ]
        query = urllib.parse.urlencode(params)
        result = self._request("GET", self._endpoint(query))
        if not result:
            raise KeyError(job_id)
        return result[0]
