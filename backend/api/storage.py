from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".data" / "employer_match.db"


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            jd_text TEXT NOT NULL,
            score_json TEXT NOT NULL,
            matches_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def save_check(
    title: str,
    jd_text: str,
    score: dict[str, Any],
    matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO checks (title, jd_text, score_json, matches_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                title.strip() or "Untitled JD",
                jd_text,
                json.dumps(score),
                json.dumps(matches) if matches is not None else None,
            ),
        )
        connection.commit()
        return get_check(cursor.lastrowid, connection)


def get_check(check_id: int, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    owns_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        row = connection.execute("SELECT * FROM checks WHERE id = ?", (check_id,)).fetchone()
        if row is None:
            raise KeyError(check_id)
        return row_to_check(row)
    finally:
        if owns_connection:
            connection.close()


def list_checks(limit: int = 25) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM checks ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [row_to_check(row) for row in rows]


def row_to_check(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "jd_text": row["jd_text"],
        "score": json.loads(row["score_json"]),
        "matches": json.loads(row["matches_json"]) if row["matches_json"] else None,
        "created_at": row["created_at"],
    }
