import numpy as np
import re
from typing import List, Dict, Any, Tuple
from .config import CONFIG


class Scorer:
    def __init__(self, rubric_vectors: Dict[str, Dict[str, np.ndarray]]):
        self.rubric_vectors = rubric_vectors
        self.competency_order = [
            "effective_communicator",
            "global_citizen",
            "creative_innovator",
            "critical_thinker",
            "reflective_future_focused",
            "career_ready",
        ]

    def split_into_sentences(self, text: str) -> List[str]:
        """Simple sentence splitter."""
        if not text:
            return []
        # Split by ., !, ?, or newline, keeping some context
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [s.strip() for s in sentences if s.strip()]

    def score(
        self, jd_text: str, jd_vectors: np.ndarray
    ) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        """
        Computes weights and per-competency details.
        jd_vectors: matrix of (num_sentences, vector_dim)
        """
        results = []
        raw_weights = {}

        # If JD is empty or no vectors, return uniform
        if not jd_text.strip() or jd_vectors.size == 0:
            uniform_weight = CONFIG["weight_budget"] / len(self.competency_order)
            weights = {comp: uniform_weight for comp in self.competency_order}
            return weights, []

        for comp_id in self.competency_order:
            comp_vectors = self.rubric_vectors[comp_id]  # { "0": vec, ... }

            level_similarities = {}
            for level_str in [str(i) for i in range(6)]:
                level_vec = comp_vectors[level_str]
                # sim(c, L) = max over JD sentences of cosine(sentence, level_vec)
                # Since vectors are L2-normalized, cosine is dot product
                similarities = np.dot(jd_vectors, level_vec)
                level_similarities[level_str] = float(np.max(similarities))

            peak_similarity = max(level_similarities.values())
            # matched_level = argmax_L sim(c, L)
            matched_level = int(max(level_similarities, key=level_similarities.get))

            baseline = CONFIG.get("calibration", {}).get(comp_id, 0.0)
            # raw_weight = matched_level * max(peak_similarity - baseline, 0)
            raw_weight = matched_level * max(peak_similarity - baseline, 0)

            raw_weights[comp_id] = raw_weight

            results.append(
                {
                    "competency_id": comp_id,
                    "level_similarities": level_similarities,
                    "matched_level": matched_level,
                    "peak_similarity": peak_similarity,
                    "raw_weight": raw_weight,
                }
            )

        # Normalize weights
        total_raw = sum(raw_weights.values())
        budget = CONFIG["weight_budget"]

        if total_raw == 0:
            # Fallback to uniform if no signal
            uniform_weight = budget / len(self.competency_order)
            weights = {comp: uniform_weight for comp in self.competency_order}
        else:
            weights = {
                comp: (raw_weights[comp] / total_raw) * budget
                for comp in self.competency_order
            }

        return weights, results
