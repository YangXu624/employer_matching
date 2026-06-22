from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from employer_match.rubric_store import COMPETENCY_ORDER

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MATCHER_KEYS = tuple(COMPETENCY_ORDER)


class PassportScoringError(RuntimeError):
    pass


def resolve_passport_root() -> Path:
    configured = os.environ.get("PASSPORT_AGENT_ROOT", "").strip()
    if configured:
        root = Path(configured)
        if not root.is_absolute():
            root = PROJECT_ROOT / root
    else:
        root = PROJECT_ROOT / "passport_agent"
    return root.resolve()


def _load_score_from_resume(passport_root: Path):
    entry_path = passport_root / "seeker_entry.py"
    if not entry_path.is_file():
        raise PassportScoringError(
            f"Missing {entry_path.name} in {passport_root}. "
            "Add seeker_entry.py with score_from_resume() when replacing the pipeline."
        )

    module_name = "passport_agent_seeker_entry"
    spec = importlib.util.spec_from_file_location(module_name, entry_path)
    if spec is None or spec.loader is None:
        raise PassportScoringError(f"Could not load {entry_path}")

    if str(passport_root) not in sys.path:
        sys.path.insert(0, str(passport_root))

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    score_fn = getattr(module, "score_from_resume", None)
    if not callable(score_fn):
        raise PassportScoringError(
            f"{entry_path} must define score_from_resume(pdf_path, student_name, email=None)."
        )
    return score_fn


def _validate_result(result: dict) -> dict:
    if not isinstance(result, dict):
        raise PassportScoringError("score_from_resume must return a dict.")

    scores = result.get("scores")
    if not isinstance(scores, dict):
        raise PassportScoringError("score_from_resume must return scores dict.")

    missing = [key for key in MATCHER_KEYS if key not in scores]
    if missing:
        raise PassportScoringError(
            f"score_from_resume missing competency keys: {', '.join(missing)}"
        )

    normalized_scores = {key: round(float(scores[key])) for key in MATCHER_KEYS}
    return {
        "scores": normalized_scores,
        "details": result.get("details") if isinstance(result.get("details"), dict) else {},
        "raw": result.get("raw"),
    }


def score_passport_from_resume(
    pdf_path: str | Path,
    student_name: str,
    email: str | None = None,
) -> dict:
    """Load passport_agent seeker_entry.score_from_resume and validate output."""
    passport_root = resolve_passport_root()
    if not passport_root.is_dir():
        raise PassportScoringError(
            f"Passport agent folder not found: {passport_root}. "
            "Set PASSPORT_AGENT_ROOT or add passport_agent/ locally."
        )

    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise PassportScoringError(f"Resume not found: {pdf_path}")

    score_from_resume = _load_score_from_resume(passport_root)
    try:
        result = score_from_resume(str(pdf_path), student_name, email)
    except PassportScoringError:
        raise
    except Exception as exc:
        entry_error = getattr(exc, "__class__", type(exc))
        if entry_error.__name__ == "SeekerScoringError":
            raise PassportScoringError(str(exc)) from exc
        raise PassportScoringError(f"Passport scoring failed: {exc}") from exc

    return _validate_result(result)
