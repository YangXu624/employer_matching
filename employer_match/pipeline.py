from typing import Dict, List, Any, Tuple
from .rubric_store import RubricStore
from .embedder import Embedder
from .scorer import Scorer
from .config import CONFIG


class Pipeline:
    def __init__(self):
        self.rubric_store = RubricStore()
        self.embedder = Embedder(CONFIG["embedding_model"])

        # Pre-cache rubric vectors
        rubric_data = self.rubric_store.data
        self.rubric_vectors = self.embedder.get_rubric_embeddings(rubric_data)

        self.scorer = Scorer(self.rubric_vectors)

    def run(self, jd_text: str) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        """Runs the Phase 0 pipeline: JD -> Weights."""
        if not jd_text.strip():
            return self.scorer.score("", None)

        sentences = self.scorer.split_into_sentences(jd_text)
        jd_vectors = self.embedder.embed(sentences)

        return self.scorer.score(jd_text, jd_vectors)
