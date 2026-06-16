import json
import os
from typing import Dict, List, Any


class RubricStore:
    FIXED_COMPETENCY_ORDER = [
        "effective_communicator",
        "global_citizen",
        "creative_innovator",
        "critical_thinker",
        "reflective_future_focused",
        "career_ready",
    ]

    def __init__(self, rubric_path: str = None):
        if rubric_path is None:
            rubric_path = os.path.join(os.path.dirname(__file__), "data", "rubric.json")
        self.rubric_path = rubric_path
        self.data = self._load_and_validate()

    def _load_and_validate(self) -> Dict[str, Any]:
        if not os.path.exists(self.rubric_path):
            raise FileNotFoundError(f"Rubric file not found: {self.rubric_path}")

        with open(self.rubric_path, "r") as f:
            data = json.load(f)

        # Validate meta competency order
        meta_order = data.get("_meta", {}).get("competency_order", [])
        if meta_order != self.FIXED_COMPETENCY_ORDER:
            raise ValueError(
                f"Rubric _meta.competency_order mismatch.\n"
                f"Expected: {self.FIXED_COMPETENCY_ORDER}\n"
                f"Got: {meta_order}"
            )

        # Validate existence of all competencies and their levels
        for comp_id in self.FIXED_COMPETENCY_ORDER:
            if comp_id not in data:
                raise ValueError(f"Competency '{comp_id}' missing from rubric.")

            levels = data[comp_id].get("levels", {})
            required_levels = [str(i) for i in range(6)]
            for level in required_levels:
                if level not in levels:
                    raise ValueError(f"Competency '{comp_id}' missing level '{level}'.")

        return data

    def get_competency_ids(self) -> List[str]:
        return self.FIXED_COMPETENCY_ORDER

    def get_level_descriptions(self, competency_id: str) -> Dict[str, str]:
        """Returns a dict of level -> description for a competency."""
        return self.data[competency_id]["levels"]

    def get_all_level_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Returns all level descriptions for all competencies."""
        return {
            comp_id: self.get_level_descriptions(comp_id)
            for comp_id in self.FIXED_COMPETENCY_ORDER
        }
