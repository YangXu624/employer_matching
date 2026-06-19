from __future__ import annotations

import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

from employer_match.rubric_store import Rubric, COMPETENCY_ORDER
from employer_match.scorer import normalize_weights, ScoreResult, CompetencyScore

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "your_gemini_api_key_here":
    genai.configure(api_key=api_key)


def build_prompt(jd_text: str, rubric: Rubric) -> str:
    prompt = "You are an expert HR analyst and competency scorer. Your task is to evaluate the provided Job Description against a list of 6 competencies.\n\n"
    prompt += "For each competency, you must assign a level from 1 to 5 based on how strongly the JD demands that competency. The scale is:\n"
    prompt += "1 = Basic/incidental engagement\n"
    prompt += "2 = Routine, expected part of the role\n"
    prompt += "3 = Regular and important part of the role\n"
    prompt += "4 = Central to the role, requires significant skill\n"
    prompt += "5 = Core of the role, requires expert-level skill and carries high stakes\n\n"
    prompt += "### COMPETENCY DEFINITIONS\n"

    for competency_id in rubric.competency_order:
        definition = rubric.raw.get(competency_id, {}).get("definition", "")
        prompt += f"\n- {competency_id}: {definition}\n"

    prompt += "\n### JOB DESCRIPTION\n"
    prompt += jd_text
    prompt += "\n\n### INSTRUCTIONS\n"
    prompt += "Evaluate the JD against each competency based *only* on the definitions provided. Return ONLY a valid JSON object matching this schema:\n"
    prompt += "{\n"
    prompt += '  "competencies": {\n'
    prompt += '    "effective_communicator": {"level": [1-5], "confidence": [0.0-1.0], "reasoning": "short explanation"},\n'
    prompt += '    "global_citizen": {"level": [1-5], "confidence": [0.0-1.0], "reasoning": "short explanation"},\n'
    prompt += '    "creative_innovator": {"level": [1-5], "confidence": [0.0-1.0], "reasoning": "short explanation"},\n'
    prompt += '    "critical_thinker": {"level": [1-5], "confidence": [0.0-1.0], "reasoning": "short explanation"},\n'
    prompt += '    "reflective_future_focused": {"level": [1-5], "confidence": [0.0-1.0], "reasoning": "short explanation"},\n'
    prompt += '    "career_ready": {"level": [1-5], "confidence": [0.0-1.0], "reasoning": "short explanation"}\n'
    prompt += "  }\n"
    prompt += "}\n"
    prompt += "Output strictly JSON, without markdown formatting."
    return prompt


def score_jd_with_llm(jd_text: str, rubric: Rubric, budget: float = 100.0) -> ScoreResult:
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not set in .env")

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
            "response_mime_type": "application/json",
        },
    )
    prompt = build_prompt(jd_text, rubric)

    response = model.generate_content(prompt)
    try:
        data = json.loads(response.text)
        comps = data.get("competencies", {})
    except json.JSONDecodeError:
        raise ValueError("Failed to decode JSON from LLM response.")

    raw_weights = {}
    competency_scores = []

    for comp_id in COMPETENCY_ORDER:
        details = comps.get(comp_id, {})
        matched_level = int(details.get("level", 1))
        confidence = float(details.get("confidence", 0.5))

        # We approximate peak_similarity as confidence for the UI.
        # Weight formula used in vector similarity: matched_level * max(peak_similarity - baseline, 0)
        # Here we just use matched_level * confidence as the raw weight signal.
        raw_weight = matched_level * confidence
        raw_weights[comp_id] = raw_weight

        level_similarities = {
            level: (confidence if level == matched_level else 0.0) for level in range(1, 6)
        }

        competency_scores.append(
            CompetencyScore(
                competency_id=comp_id,
                level_similarities=level_similarities,
                matched_level=matched_level,
                peak_similarity=confidence,
                raw_weight=raw_weight,
            )
        )

    weights, _ = normalize_weights(raw_weights, budget)
    return ScoreResult(
        weights=weights,
        competencies=competency_scores,
        used_uniform_fallback=False,
        fallback_reason=None,
    )
