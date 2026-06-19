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
NO_CHANGE_EVIDENCE = "no change"


class CompetencyCorrection(BaseModel):
    competency_id: str = Field(description="One of the six fixed competency ids.")
    weight: int = Field(description="Corrected importance weight from 0 to 100.")
    changed: bool = Field(
        description=(
            "True only when the embedding weight has a clear error and should be corrected. "
            "False when the baseline should be kept."
        )
    )
    reason: str = Field(description="Short justification for keeping or changing the weight.")
    evidence: str = Field(
        description=(
            "For changes: a JD quote, negation, or 'implied: ...'. For no change: use 'no change'."
        )
    )


class AuditOutput(BaseModel):
    corrections: list[CompetencyCorrection]
    summary: str = Field(
        description=(
            "One sentence summarizing corrections made, or stating that no corrections were needed."
        )
    )


class AuditState(TypedDict, total=False):
    jd_text: str
    baseline: dict[str, int]
    signals: dict[str, dict[str, float]]
    proposed: dict[str, int]
    changed_flags: dict[str, bool]
    reasons: dict[str, str]
    evidence: dict[str, str]
    summary: str
    errors: list[str]
    iterations: int


SYSTEM_PROMPT = (
    "You are a conservative second-opinion reviewer for competency weightings on job "
    "descriptions. An embedding model produced baseline weights (summing to 100) across six "
    "fixed PathCredits competencies.\n\n"
    "Your default is to KEEP each baseline weight unchanged. Only set changed=true when you find "
    "a CLEAR embedding error:\n"
    "1. Negation / de-emphasis false positive — a related word appears but the JD negates or "
    "de-emphasizes that competency (e.g. 'no communication with stakeholders is required').\n"
    "2. Strong implied signal — a competency is clearly central to the role but the embedding "
    "under-scored it (e.g. coordinating across offices in Japan, Germany, and Brazil implies "
    "Global Citizen).\n\n"
    "Do NOT change weights for minor wording differences, vague inference, or 'could be slightly "
    "higher/lower.' If unsure, keep changed=false and the baseline weight. Most JDs need 0–2 "
    "changes, not all six.\n\n"
    "For each competency return: weight, changed, reason, and evidence. "
    "If changed=false, weight MUST equal the baseline and evidence MUST be 'no change'. "
    "If changed=true, weight may differ by any amount and evidence must cite the JD or "
    "'implied: ...'. Return all six competencies."
)


def _build_human_prompt(state: AuditState) -> str:
    lines: list[str] = []
    lines.append("Competency definitions:")
    for cid in COMPETENCY_ORDER:
        lines.append(f"- {cid} ({COMPETENCY_LABELS[cid]}): {COMPETENCY_GLOSSARY[cid]}")

    lines.append(
        "\nEmbedding baseline weights and signals (matched_level 1-5, peak_similarity 0-1):"
    )
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
    keys = list(weights.keys())
    if not keys:
        return {}

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


def _finalize_weights(
    baseline: dict[str, int],
    proposed: dict[str, int],
    changed_flags: dict[str, bool],
) -> dict[str, int]:
    result = dict(baseline)
    changed_ids = [
        cid
        for cid in COMPETENCY_ORDER
        if changed_flags.get(cid) and proposed.get(cid, baseline[cid]) != baseline[cid]
    ]

    if not changed_ids:
        return result

    for cid in changed_ids:
        result[cid] = int(proposed[cid])

    pinned_sum = sum(result[cid] for cid in COMPETENCY_ORDER if cid not in changed_ids)
    changed_budget = WEIGHT_BUDGET - pinned_sum
    changed_weights = {cid: float(result[cid]) for cid in changed_ids}
    normalized_changed = _normalize_ints(changed_weights, budget=changed_budget)
    for cid in changed_ids:
        result[cid] = normalized_changed[cid]

    diff = WEIGHT_BUDGET - sum(result[cid] for cid in COMPETENCY_ORDER)
    if diff and changed_ids:
        result[changed_ids[0]] += diff

    return result


def _propose(state: AuditState) -> AuditState:
    llm = get_llm().with_structured_output(AuditOutput)
    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", _build_human_prompt(state)),
    ]
    result: AuditOutput = llm.invoke(messages)

    proposed: dict[str, int] = {}
    changed_flags: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for item in result.corrections:
        cid = item.competency_id.strip()
        if cid in COMPETENCY_ORDER:
            proposed[cid] = int(item.weight)
            changed_flags[cid] = bool(item.changed)
            reasons[cid] = item.reason.strip()
            evidence[cid] = item.evidence.strip()

    return {
        **state,
        "proposed": proposed,
        "changed_flags": changed_flags,
        "reasons": reasons,
        "evidence": evidence,
        "summary": result.summary.strip(),
        "iterations": state.get("iterations", 0) + 1,
    }


def _validate(state: AuditState) -> AuditState:
    baseline = state.get("baseline", {})
    proposed = state.get("proposed", {})
    changed_flags = state.get("changed_flags", {})
    reasons = state.get("reasons", {})
    evidence = state.get("evidence", {})
    errors: list[str] = []

    for cid in COMPETENCY_ORDER:
        if cid not in proposed:
            errors.append(f"Missing competency: {cid}")
            continue

        value = proposed[cid]
        base = baseline.get(cid, 0)
        changed = changed_flags.get(cid, False)

        if not isinstance(value, int) or value < 0 or value > 100:
            errors.append(f"{cid} weight must be an integer between 0 and 100.")
            continue

        ev = (evidence.get(cid) or "").strip().lower()
        if not changed:
            if value != base:
                errors.append(f"{cid} has changed=false but weight {value} != baseline {base}.")
            if ev != NO_CHANGE_EVIDENCE:
                errors.append(f"{cid} unchanged entries must use evidence 'no change'.")
            continue

        if not reasons.get(cid) or not evidence.get(cid):
            errors.append(f"{cid} changed=true requires a reason and evidence.")
        elif ev == NO_CHANGE_EVIDENCE:
            errors.append(f"{cid} changed=true cannot use evidence 'no change'.")
        elif value == base:
            errors.append(f"{cid} changed=true but weight equals baseline; set changed=false.")

    will_retry = bool(errors) and state.get("iterations", 0) < MAX_ITERATIONS
    if not will_retry:
        finalized = _finalize_weights(baseline, proposed, changed_flags)
        state = {**state, "proposed": finalized}

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
    changed_flags = final_state.get("changed_flags", {})

    competencies = []
    changes_count = 0
    for cid in COMPETENCY_ORDER:
        base = clean_baseline[cid]
        new = int(corrected.get(cid, base))
        changed = bool(changed_flags.get(cid)) and new != base
        if changed:
            changes_count += 1
        competencies.append(
            {
                "competency_id": cid,
                "label": COMPETENCY_LABELS[cid],
                "baseline": base,
                "corrected": new,
                "delta": new - base,
                "changed": changed,
                "reason": reasons.get(cid, ""),
                "evidence": evidence.get(cid, ""),
            }
        )

    summary = final_state.get("summary", "")
    if changes_count == 0:
        summary = "No corrections suggested — embedding weights look reasonable for this JD."

    return {
        "model": DEFAULT_MODEL,
        "iterations": final_state.get("iterations", 0),
        "changes_count": changes_count,
        "baseline": clean_baseline,
        "corrected": {
            cid: int(corrected.get(cid, clean_baseline[cid])) for cid in COMPETENCY_ORDER
        },
        "competencies": competencies,
        "summary": summary,
    }
