"""
Stable entry point for resume-only seeker passport scoring.

When the pipeline changes, replace passport_agent/ internals and update this
file only. The employer_match backend imports score_from_resume() and expects
six matcher competency keys (0-100) in the returned dict.

Contract:
  score_from_resume(pdf_path, student_name, email=None) -> {
    "scores": { effective_communicator, global_citizen, ... },
    "details": { ... optional reasoning/coverage per key ... },
    "raw": { ... optional debug payload ... },
  }
"""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

PASSPORT_ROOT = Path(__file__).resolve().parent
AGENT3_ROOT = PASSPORT_ROOT / "agent3"
AGENT4_ROOT = PASSPORT_ROOT / "agent4"
FIELD_REGISTRY = PASSPORT_ROOT / "agent1" / "config" / "field_registry.json"

MATCHER_KEYS = (
    "effective_communicator",
    "global_citizen",
    "creative_innovator",
    "critical_thinker",
    "reflective_future_focused",
    "career_ready",
)

PASSPORT_TO_MATCHER = {
    "EC": "effective_communicator",
    "GC": "global_citizen",
    "CI": "creative_innovator",
    "CT": "critical_thinker",
    "RFF": "reflective_future_focused",
    "CR": "career_ready",
}

COMPETENCY_LABELS = {
    "effective_communicator": "Effective Communicator",
    "global_citizen": "Global Citizen",
    "creative_innovator": "Creative Innovator",
    "critical_thinker": "Critical Thinker",
    "reflective_future_focused": "Reflective Future-Focused",
    "career_ready": "Career Ready",
}


class SeekerScoringError(RuntimeError):
    pass


def _ensure_gemini_env() -> None:
    if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]


def _load_package(name: str, path: Path) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    module.__path__ = [str(path)]  # type: ignore[attr-defined]
    module.__package__ = name
    sys.modules[name] = module
    return module


def _import_agent3_resume_parser():
    _load_package("agent3tools", AGENT3_ROOT / "tools")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agent3tools.resume_parser",
        AGENT3_ROOT / "tools" / "resume_parser.py",
    )
    if spec is None or spec.loader is None:
        raise SeekerScoringError("Could not load resume parser.")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "agent3tools"
    sys.modules["agent3tools.resume_parser"] = module
    spec.loader.exec_module(module)
    return module.parse_resume


def _import_agent4_tools():
    _load_package("agent4tools", AGENT4_ROOT / "tools")
    import importlib.util

    tool_names = [
        "gemini_client",
        "resume_section_extractor",
        "ec_enricher",
        "gc_enricher",
        "rff_enricher",
        "cr_enricher",
        "score_merger",
        "ct_scorer",
        "ci_scorer",
        "pillar_reasoner",
    ]
    modules = {}
    for name in tool_names:
        spec = importlib.util.spec_from_file_location(
            f"agent4tools.{name}",
            AGENT4_ROOT / "tools" / f"{name}.py",
        )
        if spec is None or spec.loader is None:
            raise SeekerScoringError(f"Could not load agent4 tool: {name}")
        module = importlib.util.module_from_spec(spec)
        module.__package__ = "agent4tools"
        sys.modules[f"agent4tools.{name}"] = module
        spec.loader.exec_module(module)
        modules[name] = module
    return modules


def _load_canonical_fields() -> list[str]:
    if not FIELD_REGISTRY.exists():
        return []
    data = json.loads(FIELD_REGISTRY.read_text(encoding="utf-8"))
    names: list[str] = []
    for pillar_fields in data.values():
        if not isinstance(pillar_fields, dict):
            continue
        for field_def in pillar_fields.values():
            if isinstance(field_def, dict) and field_def.get("canonical"):
                names.append(field_def["canonical"])
    return names


def _build_docs_data(student_name: str, pdf_path: Path, parse_resume) -> dict:
    parsed = parse_resume(str(pdf_path))
    raw_text = (parsed.get("raw_text") or "").strip()
    if len(raw_text) < 50:
        raise SeekerScoringError("Could not extract enough text from the resume PDF.")

    return {
        "student_name": student_name,
        "sources_found": ["resume"],
        "resume": {
            "raw_text": raw_text,
            "sections": parsed.get("sections") or {},
        },
        "linkedin": None,
        "github": None,
    }


def _empty_survey_scores() -> dict:
    empty = {"score": 0, "sub_scores": {}, "data_coverage": 0.0, "source": "docs"}
    return {"EC": dict(empty), "GC": dict(empty), "RFF": dict(empty), "CR": dict(empty)}


def score_from_resume(
    pdf_path: str | Path,
    student_name: str,
    email: str | None = None,
) -> dict:
    """Score six competencies from a resume PDF. Returns matcher-keyed scores."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise SeekerScoringError(f"Resume not found: {pdf_path}")

    _ensure_gemini_env()
    if not os.environ.get("GEMINI_API_KEY"):
        raise SeekerScoringError("GEMINI_API_KEY or GOOGLE_API_KEY is required for passport scoring.")

    parse_resume = _import_agent3_resume_parser()
    tools = _import_agent4_tools()
    docs_data = _build_docs_data(student_name, pdf_path, parse_resume)

    resume = docs_data.get("resume") or {}
    sections = resume.get("sections") or {}
    if resume.get("raw_text"):
        llm_sections = tools["resume_section_extractor"].extract_sections(resume["raw_text"])
        for key, value in (llm_sections or {}).items():
            if value and str(value).strip() and len(str(sections.get(key) or "").strip()) < 30:
                sections[key] = value

    canonical_fields = _load_canonical_fields()
    missing_fields = set(canonical_fields)
    raw_fields = {
        name: {"value": None, "status": "missing", "pillar": "unknown"}
        for name in canonical_fields
    }
    survey_scores = _empty_survey_scores()

    enriched: dict = {}
    enriched.update(tools["ec_enricher"].enrich_ec(docs_data, missing_fields, cpc_session_text=""))
    enriched.update(tools["gc_enricher"].enrich_gc(docs_data, missing_fields))
    enriched.update(tools["rff_enricher"].enrich_rff(docs_data, missing_fields, cpc_session_text=""))
    enriched.update(tools["cr_enricher"].enrich_cr(docs_data, missing_fields))

    merged = tools["score_merger"].merge_and_rescore(
        raw_fields,
        enriched,
        missing_fields,
        survey_scores,
    )

    cr = merged["cr"]
    if cr["sub_scores"].get("C4", 0) == 0 and len(resume.get("raw_text", "")) > 300:
        call_gemini = tools["gemini_client"].call_gemini
        parse_json = tools["gemini_client"].parse_json_resp
        prompt = (
            "Does the following text represent a real, complete student resume "
            "with substantive content?\n\nRESUME TEXT:\n"
            f"{resume['raw_text'][:1200]}\n\n"
            'Respond ONLY: {"resume_built": true} or {"resume_built": false}'
        )
        parsed = parse_json(call_gemini(prompt))
        if parsed and str(parsed.get("resume_built", "")).lower() in ("true", "1", "yes"):
            cr["sub_scores"]["C4"] = 100
            cr["score"] = round(sum(cr["sub_scores"].values()) / len(cr["sub_scores"]), 1)

    ct_result = tools["ct_scorer"].score_ct(docs_data, student_name)
    ct_arc = ct_result.get("thinking_arc", "")
    ci_result = tools["ci_scorer"].score_ci(docs_data, student_name, ct_arc=ct_arc)

    prior_notes = [ct_arc] if ct_arc else []
    for key, result in [
        ("EC", merged["ec"]),
        ("GC", merged["gc"]),
        ("RFF", merged["rff"]),
        ("CR", merged["cr"]),
    ]:
        result["reasoning"] = tools["pillar_reasoner"].generate_reasoning(
            key,
            result,
            docs_data,
            student_name,
            raw_fields,
            prior_notes=list(prior_notes),
        )
        if result["reasoning"]:
            prior_notes.append(result["reasoning"])

    ct_result["reasoning"] = ct_result.get("thinking_arc", "")
    ci_result["reasoning"] = ci_result.get("innovation_arc", "")

    enriched_output = {
        "student_name": student_name,
        "email": email,
        "scores": {
            "EC": merged["ec"],
            "GC": merged["gc"],
            "RFF": merged["rff"],
            "CR": merged["cr"],
            "CT": ct_result,
            "CI": ci_result,
        },
    }

    scores: dict[str, float] = {}
    details: dict[str, dict] = {}
    for code, matcher_id in PASSPORT_TO_MATCHER.items():
        pillar = enriched_output["scores"][code]
        scores[matcher_id] = round(float(pillar.get("score", 0)))
        details[matcher_id] = {
            "label": COMPETENCY_LABELS[matcher_id],
            "source": pillar.get("source", "docs"),
            "data_coverage": pillar.get("data_coverage", 0.0),
            "reasoning": pillar.get("reasoning", ""),
        }

    return {
        "scores": scores,
        "details": details,
        "raw": enriched_output,
    }
