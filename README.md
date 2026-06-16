# Employer Match

Phase 0 builds the deterministic employer weight extraction core for the
PathCredits employer matching layer.

The package reads a job description, compares it against the six fixed
PathCredits competency rubrics, and prints a 100-point employer weight vector
with per-competency scoring details.

## Phase 0 Scope

Included:

- Python CLI package named `employer_match`.
- Local Ollama embeddings with `nomic-embed-text:v1.5`.
- Rubric loading and validation.
- Rubric vector caching.
- Deterministic cosine-similarity scoring.
- Uniform fallback for empty or zero-signal inputs.

Excluded until later phases:

- API.
- UI.
- Candidate ranking.
- Optional LLM review providers.
- Calibration baselines beyond the zero default.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
brew install ollama
brew services start ollama
ollama pull nomic-embed-text:v1.5
```

The scorer calls the local Ollama HTTP API at `http://localhost:11434` by
default. The embedding model is `nomic-embed-text:v1.5`.

## Usage

```bash
python -m employer_match.cli --jd examples/sample_jd.txt
```

JSON output:

```bash
python -m employer_match.cli --jd examples/sample_jd.txt --json
```

`--llm off` is accepted for future compatibility. Any other LLM value is
rejected in Phase 0.

## Cache

Rubric embeddings are cached under `.cache/employer_match/` by default. The cache
key includes the Ollama embedding model name and a hash of the rubric level
descriptions.

## Quality Gates

```bash
pytest
ruff check .
ruff format --check .
python -m employer_match.cli --jd examples/sample_jd.txt
```

## Known Limits

The Phase 0 scorer is deterministic and embedding-only. It can miss negation or
relative emphasis in subtle job descriptions. Treat outputs as decision support
until later calibration and optional LLM review phases are implemented.
