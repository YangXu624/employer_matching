# Employer Match

Phase 0 builds the deterministic employer weight extraction core for the
PathCredits employer matching layer.

The package reads a job description, compares it against the six fixed
PathCredits competency rubrics, and prints a 100-point employer weight vector
with per-competency scoring details.

## Phase 0 Scope

Included:

- Python CLI package named `employer_match`.
- In-process `sentence-transformers` embeddings.
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
```

Phase 0 uses the configured sentence-transformers model in-process. The default
model is `BAAI/bge-base-en-v1.5`; the first real scoring run downloads it if it
is not already present locally.

## Usage

```bash
# To analyze the main sample file:
python -m employer_match.cli --jd sample_jd.txt

# To analyze a specific job description from the jds/ folder:
python -m employer_match.cli --jd jds/fbi.txt
```

JSON output:

```bash
python -m employer_match.cli --jd sample_jd.txt --json
```

## MVP Web UI

Run the local dashboard:

```bash
python -m employer_match.web_app
```

Then open `http://127.0.0.1:8765`.

The UI lets you load sample JDs, paste new JDs, run the Phase 0 scorer, see an
overall score plus competency breakdown, and keep recent checks in browser
storage.

`--llm off` is accepted for future compatibility. Any other LLM value is
rejected in Phase 0.

## Cache

Rubric embeddings are cached under `.cache/employer_match/` by default. The cache
key includes the embedding model name and a hash of the rubric level
descriptions.

## Quality Gates

```bash
pytest
ruff check .
ruff format --check .
python -m employer_match.cli --jd sample_jd.txt
```

## Known Limits

The Phase 0 scorer is deterministic and embedding-only. It can miss negation or
relative emphasis in subtle job descriptions. Treat outputs as decision support
until later calibration and optional LLM review phases are implemented.

Ollama may be worth trying in a later phase as an alternate embedding provider,
but it is not part of the Phase 0 runtime.
