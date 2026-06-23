"""Local file-backed JobStore. Used when offline or when Supabase is down.

Mirrors the logical columns of the Supabase `jobs` table so the rest of the app
behaves identically regardless of which shelf the boxes sit on.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db.jobs import (
    JobValidationError,
    build_competencies,
    normalize_status,
    validate_weights,
)

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".data" / "jobs.db"


class SqliteJobStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                jd_text TEXT NOT NULL,
                weights_json TEXT NOT NULL,
                competencies_json TEXT NOT NULL,
                score_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'published',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        return connection

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

        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs
                    (id, title, jd_text, weights_json, competencies_json, score_json,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    clean_title,
                    jd_text,
                    json.dumps(clean_weights),
                    json.dumps(competencies),
                    json.dumps(score),
                    clean_status,
                    now,
                    now,
                ),
            )
            connection.commit()
        return self.get_job(job_id)

    def list_jobs(
        self, *, status: str | None = "published", limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT * FROM jobs WHERE status = ?
                    ORDER BY created_at DESC, id DESC LIMIT ?
                    """,
                    (normalize_status(status), limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [_row_to_job(row) for row in rows]

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            return _row_to_job(row)


def _row_to_job(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "jd_text": row["jd_text"],
        "weights": json.loads(row["weights_json"]),
        "competencies": json.loads(row["competencies_json"]),
        "score": json.loads(row["score_json"]) if row["score_json"] else {},
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
