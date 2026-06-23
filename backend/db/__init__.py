"""Job storage package: pick the right shelf (Supabase / SQLite) via env.

Usage from the API layer::

    from backend.db import get_job_store
    job = get_job_store().create_job(title=..., jd_text=..., weights=...)

Selection rules for ``JOB_STORE``:
    - ``sqlite``   -> SqliteJobStore (local file) -- the default
    - ``supabase`` -> SupabaseJobStore (requires SUPABASE_URL + SERVICE_ROLE_KEY)
    - unset        -> SQLite

SQLite is the main store. Supabase is opt-in via ``JOB_STORE=supabase``.
"""

from __future__ import annotations

import os
from functools import lru_cache

from backend.db.jobs import (
    COMPETENCY_LABELS,
    JobStore,
    JobValidationError,
    build_competencies,
    validate_weights,
)

__all__ = [
    "JobStore",
    "JobValidationError",
    "COMPETENCY_LABELS",
    "build_competencies",
    "validate_weights",
    "get_job_store",
    "reset_job_store_cache",
]


def _resolve_backend() -> str:
    choice = os.getenv("JOB_STORE", "").strip().lower()
    if choice == "supabase":
        return "supabase"
    # SQLite is the default/main store; Supabase is opt-in only.
    return "sqlite"


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    backend = _resolve_backend()
    if backend == "supabase":
        from backend.db.supabase_jobs import SupabaseJobStore

        return SupabaseJobStore()

    from backend.db.sqlite_jobs import SqliteJobStore

    return SqliteJobStore()


def reset_job_store_cache() -> None:
    """Clear the cached store (used by tests after changing env vars)."""
    get_job_store.cache_clear()
