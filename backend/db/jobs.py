"""Storage-agnostic contract for persisting scored job descriptions.

The API layer only ever talks to a `JobStore`; it never imports Supabase or
SQLite directly. Swapping databases later means writing one new implementation
of this protocol, not hunting down scattered queries.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from employer_match.rubric_store import COMPETENCY_ORDER, Rubric, load_rubric

# Human-readable labels keyed by competency_id. Kept here (rather than imported
# from employer_match.web_app) so the storage layer stays free of heavy scoring
# imports such as sentence-transformers.
COMPETENCY_LABELS: dict[str, str] = {
    "career_self_development": "Career & Self-Development",
    "communication": "Communication",
    "critical_thinking": "Critical Thinking",
    "equity_inclusion": "Equity & Inclusion",
    "leadership": "Leadership",
    "professionalism": "Professionalism",
    "teamwork": "Teamwork",
    "technology": "Technology",
}

VALID_STATUSES = ("draft", "published", "archived")


class JobValidationError(ValueError):
    """Raised when a job payload cannot be persisted as-is."""


@runtime_checkable
class JobStore(Protocol):
    """Minimal interface every storage backend must satisfy."""

    def create_job(
        self,
        *,
        title: str,
        jd_text: str,
        weights: dict[str, float],
        score: dict[str, Any] | None = None,
        status: str = "published",
    ) -> dict[str, Any]:
        ...

    def list_jobs(self, *, status: str | None = "published", limit: int = 100) -> list[dict[str, Any]]:
        ...

    def get_job(self, job_id: str) -> dict[str, Any]:
        ...


def normalize_status(status: str | None, *, default: str = "published") -> str:
    value = (status or default).strip().lower()
    if value not in VALID_STATUSES:
        raise JobValidationError(
            f"status must be one of {', '.join(VALID_STATUSES)}; got {status!r}"
        )
    return value


def validate_weights(weights: dict[str, Any], *, tolerance: float = 1.0) -> dict[str, float]:
    """Ensure weights cover the 8 NACE competencies and sum to ~100."""
    if not isinstance(weights, dict):
        raise JobValidationError("weights must be an object mapping competency_id -> number.")

    missing = [cid for cid in COMPETENCY_ORDER if cid not in weights]
    if missing:
        raise JobValidationError(f"weights is missing competencies: {', '.join(missing)}")

    unknown = [cid for cid in weights if cid not in COMPETENCY_ORDER]
    if unknown:
        raise JobValidationError(f"weights has unknown competencies: {', '.join(unknown)}")

    cleaned: dict[str, float] = {}
    for cid in COMPETENCY_ORDER:
        try:
            cleaned[cid] = float(weights[cid])
        except (TypeError, ValueError):
            raise JobValidationError(f"weight for {cid} must be a number; got {weights[cid]!r}")

    total = sum(cleaned.values())
    if abs(total - 100.0) > tolerance:
        raise JobValidationError(f"weights must sum to ~100 (got {round(total, 2)}).")

    return cleaned


def build_competencies(
    weights: dict[str, float],
    score: dict[str, Any] | None = None,
    *,
    rubric: Rubric | None = None,
) -> list[dict[str, Any]]:
    """Merge flat `weights` with rubric label + description and matched levels.

    The matching teammate gets human-readable context (label + definition)
    without having to load the rubric file separately.
    """
    rubric = rubric or load_rubric()
    score = score or {}

    matched_levels: dict[str, Any] = {}
    for comp in score.get("competencies", []) or []:
        cid = comp.get("competency_id")
        if cid:
            matched_levels[cid] = comp.get("matched_level")

    competencies: list[dict[str, Any]] = []
    for cid in COMPETENCY_ORDER:
        definition = rubric.raw.get(cid, {}).get("definition", "")
        competencies.append(
            {
                "competency_id": cid,
                "label": COMPETENCY_LABELS.get(cid, cid.replace("_", " ").title()),
                "description": definition,
                "weight": weights.get(cid, 0),
                "matched_level": matched_levels.get(cid),
            }
        )
    return competencies
