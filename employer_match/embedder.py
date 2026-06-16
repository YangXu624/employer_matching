import os
import pickle
import hashlib
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed texts and L2-normalize the vectors."""
        if not texts:
            return np.array([])

        # sentence-transformers can normalize during encode
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings

    def get_rubric_embeddings(
        self, rubric_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Embed all rubric level descriptions and cache them.
        Structure: {comp_id: {level_str: vector}}
        """
        # Create a hash of the rubric levels to detect changes
        rubric_content = ""
        competencies = sorted(rubric_data.keys())
        if "_meta" in competencies:
            competencies.remove("_meta")

        for comp_id in competencies:
            levels = rubric_data[comp_id]["levels"]
            for level in sorted(levels.keys()):
                rubric_content += levels[level]

        rubric_hash = hashlib.md5(rubric_content.encode()).hexdigest()
        safe_model_name = self.model_name.replace("/", "_")
        cache_file = os.path.join(
            self.cache_dir, f"rubric_vectors_{safe_model_name}_{rubric_hash}.pkl"
        )

        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)

        # Otherwise, compute and cache
        result = {}
        for comp_id in competencies:
            levels = rubric_data[comp_id]["levels"]
            level_texts = [levels[str(i)] for i in range(6)]
            vectors = self.embed(level_texts)
            result[comp_id] = {str(i): vectors[i] for i in range(6)}

        with open(cache_file, "wb") as f:
            pickle.dump(result, f)

        return result
