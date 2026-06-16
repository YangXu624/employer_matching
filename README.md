# Employer Match Layer (Phase 0)

This repository contains the foundation for an automated system designed to match student talent to Job Descriptions (JDs). It calculates an employer's preference weights across six core competencies by analyzing the semantic similarity between the JD text and a predefined rubric.

## What has been done (Phase 0)

In Phase 0, we have established the deterministic core of the system. It operates entirely locally with no external API calls, focusing on high-quality text embeddings and mathematical scoring.

### Core Technologies
- **Embedding Model:** Uses `BAAI/bge-base-en-v1.5` via the `sentence-transformers` library. This model was chosen for its strong performance in retrieval and semantic similarity tasks.
- **Local Caching:** Rubric vectors are embedded once and cached locally (using MD5 hashing of content) to ensure near-instant startup after the first run.
- **Vector Math:** Utilizes `numpy` for L2-normalization and dot-product calculations (efficient cosine similarity).

### Scoring Algorithm
1. **Sentence Splitting:** The input Job Description is split into individual sentences.
2. **Symmetric Embedding:** Both the JD sentences and the rubric level descriptions (Levels 0-5) are embedded and L2-normalized.
3. **Max Similarity:** For each competency, we calculate the similarity of every JD sentence against every rubric level. The system identifies the "peak similarity" (the highest match) to determine the most relevant proficiency level.
4. **Weight Calculation:**
   - `raw_weight = matched_level * max(peak_similarity - baseline, 0)`
   - This ensures that higher proficiency requirements and stronger semantic matches result in higher weights.
5. **Normalization:** The raw weights are normalized to sum exactly to a 100-point budget.

## Repository Structure

```text
employer_match/          # Core Python package
├── data/                # Data files
│   └── rubric.json      # The PathCredits competency rubric
├── .cache/              # Cached embedding vectors (generated at runtime)
├── config.py            # Model names, weight budgets, and calibration baselines
├── rubric_store.py      # Rubric loading and validation logic
├── embedder.py          # sentence-transformers wrapper & caching logic
├── scorer.py            # The mathematical scoring engine
├── pipeline.py          # Coordinates JD -> Embedding -> Scoring
└── cli.py               # Command-line interface
examples/                # Sample Job Descriptions for testing
tests/                   # Unit tests for core logic and math
docs/                    # Project documentation and plans
pyproject.toml           # Project dependencies and metadata
```

## Getting Started

### Prerequisites
- Python 3.11+

### Installation
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install .
   ```

### Usage
Analyze a Job Description and see the weight breakdown:
```bash
PYTHONPATH=. python3 -m employer_match.cli --jd examples/sample_jd.txt
```

## What's Left to Be Done

- **Phase 1: Candidate Matching:** Implement `matcher.py` to ingest candidate scores (from PathCredits CSVs) and calculate the final "Employer Match Score" using the formula: `Σ(W * S) / ΣW`.
- **Phase 2: LLM Refinement:** Add an optional LLM layer (Gemini, Claude, or Ollama) to handle complex nuances like negation (e.g., "we do NOT require X") that embeddings might miss.
- **Phase 3: Interactive UI:** Build a front-end form where employers can paste their JD, see the generated weights on sliders, and manually adjust them.
- **Phase 4: Calibration:** Analyze a corpus of reference JDs to fine-tune the `baseline` values in `config.py`, ensuring the weights accurately reflect industry standards.
