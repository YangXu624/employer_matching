from __future__ import annotations

import math
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from backend.agent.llm import DEFAULT_MODEL, get_llm
from employer_match.rubric_store import COMPETENCY_ORDER

COMPETENCY_LABELS = {
    "effective_communicator": "Effective Communicator",
    "global_citizen": "Global Citizen",
    "creative_innovator": "Creative Innovator",
    "critical_thinker": "Critical Thinker",
    "reflective_future_focused": "Reflective Future-Focused",
    "career_ready": "Career Ready",
}

COMPETENCY_GLOSSARY = {
    "effective_communicator": (
        "Conveys ideas clearly in writing and speech, listens, presents, and collaborates with "
        "stakeholders, clients, or teammates."
    ),
    "global_citizen": (
        "Works across cultures and diverse perspectives; global, ethical, social, or environmental "
        "awareness; languages; international or community contexts."
    ),
    "creative_innovator": (
        "Generates novel ideas, experiments, designs, and solves problems in inventive or "
        "entrepreneurial ways."
    ),
    "critical_thinker": (
        "Analyzes information, evaluates evidence, reasons logically, and makes data-driven "
        "decisions to solve complex problems."
    ),
    "reflective_future_focused": (
        "Self-aware, learns continuously, adapts, shows resilience, and plans for growth and the "
        "future."
    ),
    "career_ready": (
        "Job-specific technical and professional skills, tools, domain expertise, and general "
        "workplace readiness."
    ),
}

MAX_ITERATIONS = 3
WEIGHT_BUDGET = 100


class CompetencyCorrection(BaseModel):
    competency_id: str = Field(description="One of the six fixed competency ids.")
    weight: int = Field(description="Corrected importance weight from 0 to 100.")
    reason: str = Field(description="Short justification for the corrected weight.")
    evidence: str = Field(
        description=(
            "A short JD quote that supports the weight, the negation that lowers it, or "
            "'implied: ...' when the signal is inferred rather than stated."
        )
    )


class AuditOutput(BaseModel):
    corrections: list[CompetencyCorrection]
    summary: str = Field(description="One sentence describing the key changes made.")


class AuditState(TypedDict, total=False):
    jd_text: str
    baseline: dict[str, int]
    signals: dict[str, dict[str, float]]
    proposed: dict[str, int]
    reasons: dict[str, str]
    evidence: dict[str, str]
    summary: str
    errors: list[str]
    iterations: int


SYSTEM_PROMPT = (
    "You audit competency weightings for job descriptions. An embedding model produced baseline "
    "weights (summing to 100) across six fixed PathCredits competencies. That model is keyword- and "
    "surface-driven, so it makes two kinds of mistakes:\n"
    "1. False positives from context/negation: it scores a competency high just because a related "
    "word appears, even when the JD negates or de-emphasizes it (e.g. 'no communication with "
    "stakeholders is required' should make Effective Communicator low).\n"
    "2. Missed implied signals: it under-scores a competency that is clearly implied by the role but "
    "never named (e.g. coordinating overseas teams implies Global Citizen).\n\n"
    "Read the JD and correct the weights to reflect true importance to the role. Keep weights you "
    "agree with unchanged. Change a weight only when the JD justifies it, and you may change it by "
    "any amount (including down to 0). For every competency, return the corrected integer weight, a "
    "short reason, and evidence (a JD quote, the negation, or 'implied: ...'). Return all six "
    "competencies."
)


def _build_human_prompt(state: AuditState) -> str:
    lines: list[str] = []
    lines.append("Competency definitions:")
    for cid in COMPETENCY_ORDER:
        lines.append(f"- {cid} ({COMPETENCY_LABELS[cid]}): {COMPETENCY_GLOSSARY[cid]}")

    lines.append("\nEmbedding baseline weights and signals (matched_level 1-5, peak_similarity 0-1):")
    baseline = state.get("baseline", {})
    signals = state.get("signals", {})
    for cid in COMPETENCY_ORDER:
        sig = signals.get(cid, {})
        level = sig.get("matched_level", "?")
        sim = sig.get("peak_similarity", "?")
        lines.append(
            f"- {cid}: weight={baseline.get(cid, 0)}, matched_level={level}, peak_similarity={sim}"
        )

    errors = state.get("errors") or []
    if errors:
        lines.append(
            "\nYour previous answer was rejected for these reasons; fix them and answer again:"
        )
        for err in errors:
            lines.append(f"- {err}")

    lines.append("\nJob description:\n" + state.get("jd_text", "").strip())
    return "\n".join(lines)


def _normalize_ints(weights: dict[str, float], budget: int = WEIGHT_BUDGET) -> dict[str, int]:
    keys = COMPETENCY_ORDER
    vals = [max(0.0, float(weights.get(k, 0))) for k in keys]
    total = sum(vals)
    if total <= 0:
        base = budget // len(keys)
        out = {k: base for k in keys}
        out[keys[-1]] += budget - base * len(keys)
        return out

    scaled = [v / total * budget for v in vals]
    floors = [int(math.floor(s)) for s in scaled]
    remainder = budget - sum(floors)
    order = sorted(range(len(keys)), key=lambda i: scaled[i] - floors[i], reverse=True)
    for i in range(remainder):
        floors[order[i]] += 1
    return {keys[i]: floors[i] for i in range(len(keys))}


def _propose(state: AuditState) -> AuditState:
    llm = get_llm().with_structured_output(AuditOutput)
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", _build_human_prompt(state)),
    ]
    result: AuditOutput = llm.invoke(messages)

    proposed: dict[str, int] = {}
    reasons: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for item in result.corrections:
        cid = item.competency_id.strip()
        if cid in COMPETENCY_ORDER:
            proposed[cid] = int(item.weight)
            reasons[cid] = item.reason.strip()
            evidence[cid] = item.evidence.strip()

    return {
        **state,
        "proposed": proposed,
        "reasons": reasons,
        "evidence": evidence,
        "summary": result.summary.strip(),
        "iterations": state.get("iterations", 0) + 1,
    }


def _validate(state: AuditState) -> AuditState:
    baseline = state.get("baseline", {})
    proposed = state.get("proposed", {})
    reasons = state.get("reasons", {})
    evidence = state.get("evidence", {})
    errors: list[str] = []

    for cid in COMPETENCY_ORDER:
        if cid not in proposed:
            errors.append(f"Missing competency: {cid}")
            continue
        value = proposed[cid]
        if not isinstance(value, int) or value < 0 or value > 100:
            errors.append(f"{cid} weight must be an integer between 0 and 100.")
            continue
        if value != baseline.get(cid) and (not reasons.get(cid) or not evidence.get(cid)):
            errors.append(f"{cid} changed without a reason and evidence.")

    will_retry = bool(errors) and state.get("iterations", 0) < MAX_ITERATIONS
    if not will_retry:
        source = proposed if proposed else baseline
        state = {**state, "proposed": _normalize_ints(source)}

    return {**state, "errors": errors}


def _route(state: AuditState) -> str:
    if state.get("errors") and state.get("iterations", 0) < MAX_ITERATIONS:
        return "propose"
    return END


def _build_graph():
    graph = StateGraph(AuditState)
    graph.add_node("propose", _propose)
    graph.add_node("validate", _validate)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", "validate")
    graph.add_conditional_edges("validate", _route, {"propose": "propose", END: END})
    return graph.compile()


_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def audit_weights(
    jd_text: str,
    baseline: dict[str, Any],
    signals: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    clean_baseline = {cid: int(round(float(baseline.get(cid, 0)))) for cid in COMPETENCY_ORDER}
    initial: AuditState = {
        "jd_text": jd_text,
        "baseline": clean_baseline,
        "signals": signals or {},
        "errors": [],
        "iterations": 0,
    }

    final_state = _get_graph().invoke(initial)
    corrected = final_state.get("proposed", clean_baseline)
    reasons = final_state.get("reasons", {})
    evidence = final_state.get("evidence", {})

    competencies = []
    for cid in COMPETENCY_ORDER:
        base = clean_baseline[cid]
        new = int(corrected.get(cid, base))
        competencies.append(
            {
                "competency_id": cid,
                "label": COMPETENCY_LABELS[cid],
                "baseline": base,
                "corrected": new,
                "delta": new - base,
                "reason": reasons.get(cid, ""),
                "evidence": evidence.get(cid, ""),
            }
        )

    return {
        "model": DEFAULT_MODEL,
        "iterations": final_state.get("iterations", 0),
        "baseline": clean_baseline,
        "corrected": {cid: int(corrected.get(cid, clean_baseline[cid])) for cid in COMPETENCY_ORDER},
        "competencies": competencies,
        "summary": final_state.get("summary", ""),
    }
