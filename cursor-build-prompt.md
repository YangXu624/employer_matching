# Cursor Build Prompt — Employer Match Layer

> **How to use:** paste everything below the line into Cursor as the task. Put the uploaded `pathcredits_rubric.json` at `employer_match/data/rubric.json` first. Build **Phase 0 only** to start; later phases are described so the scaffold leaves room for them.

---

## Goal

Build a Python package `employer_match` that reads an employer's **job description (JD)**, produces a **weight per competency** (how much this employer values each of six competencies), and later ranks candidates by combining those weights with candidate competency scores from the existing PathCredits pipeline.

There are six competencies, fixed, in this order: `effective_communicator`, `global_citizen`, `creative_innovator`, `critical_thinker`, `reflective_future_focused`, `career_ready`.

The core scoring runs **locally with no API calls**. An **optional LLM layer is switchable** between `off`, `ollama` (local), `gemini`, and `claude`, behind one interface.

## Stack & dependencies

- Python 3.11+
- `sentence-transformers` (local embeddings, in-process — do **not** use a daemon for embeddings)
- `numpy` (vectors, cosine similarity, normalization)
- `pandas` (read PathCredits competency CSVs — Phase 1)
- Optional, only imported when the matching provider is selected: `ollama`, `google-generativeai`, `anthropic`

## Project structure

```
employer_match/
├── data/
│   └── rubric.json          # the provided pathcredits_rubric.json
├── config.py                # defaults: model name, weight_budget, llm provider, thresholds
├── rubric_store.py          # load + validate rubric.json
├── embedder.py              # sentence-transformers; embeds + caches rubric level vectors
├── scorer.py                # similarity → matched level + peak → weight vector  (no AI)
├── llm/
│   ├── base.py              # LLMProvider interface + needs_llm() trigger
│   ├── ollama_provider.py
│   ├── gemini_provider.py
│   └── claude_provider.py
├── matcher.py               # W × S → ranked candidates   (Phase 1)
├── pipeline.py              # JD in → weights (+ ranking)  ties it together
└── cli.py                   # paste a JD, print weights + per-competency detail
```

## Data contracts

### `rubric.json` (already provided — do not invent your own)

```
{
  "_meta": { "competency_order": [ ...6 ids... ], ...notes... },
  "<competency_id>": {
    "definition": "human-only — DO NOT EMBED THIS",
    "levels": { "0": "...", "1": "...", "2": "...", "3": "...", "4": "...", "5": "..." }
  },
  ... 6 competencies
}
```

Embed **only** the six `levels` strings per competency. Never embed `definition` or `_meta`.

### Per-competency result (intermediate)

```
{
  "competency_id": "effective_communicator",
  "level_similarities": {"5": 0.34, "4": 0.30, "3": 0.24, "2": 0.18, "1": 0.12, "0": 0.08},
  "matched_level": 5,
  "peak_similarity": 0.34,
  "raw_weight": 1.70
}
```

### Weight vector `W` (this layer's output) — sums to `weight_budget`

```
{ "effective_communicator": 23.0, "global_citizen": 12.0, ... }
```

### Candidate scores `S` (Phase 1 input, from PathCredits CSVs) — 0–100 each

```
{ "student_id": "abc@x.com", "scores": { "effective_communicator": 78, ... } }
```

### Match output (Phase 1)

```
[ { "student_id": "...", "match_score": 81.4 }, ... ]   # Σ(W·S)/ΣW, sorted desc
```

## Algorithms

### Embedding (`embedder.py`)
- Load a sentence-transformers model named in config (default `BAAI/bge-base-en-v1.5`).
- Embed the 36 rubric level descriptions once and cache (e.g. pickle keyed by model name + rubric hash).
- L2-normalize all vectors so cosine similarity is a dot product.
- Treat JD text and level descriptions **symmetrically** — apply the same prefix/instruction (or none) to both sides. No asymmetric query/document prefixes.

### Scoring (`scorer.py`, deterministic, no AI)
1. Split the JD into sentences; embed each sentence.
2. For each competency `c` and level `L`: `sim(c, L) = max over JD sentences of cosine(sentence, level_vec[c][L])`.
3. `matched_level[c] = argmax_L sim(c, L)`; `peak[c] = max_L sim(c, L)`.
4. `raw_weight[c] = matched_level[c] * max(peak[c] - baseline[c], 0)`.
   - `baseline[c]` defaults to `0.0` (identity). It is a **calibration hook** filled in Phase 4 from reference JDs. Keep the subtraction in the code now, just with zero baselines.
5. Normalize across the six: `W[c] = raw_weight[c] / sum(raw_weight) * weight_budget`. If all raw weights are 0, fall back to uniform.

Return `W` plus the list of per-competency results.

### Conditional LLM firing (`llm/base.py`)
`needs_llm(results, config)` returns True if **any** competency is uncertain:
- `peak[c] < config.llm_trigger.min_peak_similarity` (weak match), OR
- `(top1_sim - top2_sim) < config.llm_trigger.max_margin` (two levels nearly tied).
- (Optional, nice-to-have) a regex negation cue near competency terms.

### LLM refine (provider, when selected and fired)
Input: JD text, the rubric levels, and the baseline `W` + matched levels. Ask the model to correct **only** negation and relative-emphasis errors, returning JSON: per competency an adjusted level (0–5), a one-line reason, and the JD sentence it relied on. Recombine and re-normalize exactly as in scoring. Always parse defensively; on any parse/error, fall back to the baseline `W`.

## LLM provider abstraction (the switch)

```python
# llm/base.py
class LLMProvider(ABC):
    @abstractmethod
    def refine(self, jd_text: str, rubric: dict, baseline: dict) -> dict: ...

def get_provider(config) -> LLMProvider | None:
    # "off" -> None ; "ollama"/"gemini"/"claude" -> the matching class
```

Selected by `config.llm_provider` and overridable by the CLI `--llm` flag. `off` is the default and means the cheap core only.

## Config defaults (`config.py`)

```python
CONFIG = {
    "embedding_model": "BAAI/bge-base-en-v1.5",
    "weight_budget":   100,
    "llm_provider":    "off",            # "off" | "ollama" | "gemini" | "claude"
    "ollama_model":    "llama3.1",
    "llm_trigger":     {"min_peak_similarity": 0.40, "max_margin": 0.05},
    "calibration":     None              # Phase 4: path to per-competency baselines
}
```

## CLI behaviour

```
python -m employer_match.cli --jd path/to/jd.txt [--llm off|ollama|gemini|claude]
```
Prints the weight vector and, per competency, the matched level, peak similarity, and all six level similarities. (Phase 1 adds `--scores path/to/scores.csv` to also print the ranked candidates.)

## Build phases

- **Phase 0 (build now):** `rubric_store` + `embedder` + `scorer` + `cli`. Output: paste a JD, see the weights and detail. Cache rubric vectors. No LLM, no matching.
- **Phase 1:** `matcher` + wire `pipeline` to PathCredits competency CSVs (join by student email/id; competency scores already 0–100). Output: ranked candidates.
- **Phase 2:** the `llm/` providers + conditional firing.
- **Phase 3:** employer form/UI (paste JD → preview weights on sliders → adjust → confirm).
- **Phase 4:** calibration — populate `baseline[c]` from a set of reference JDs.

## Hard constraints

- Embed `levels` only; never `definition` or `_meta`.
- L2-normalize vectors; symmetric treatment of JD vs level text.
- Keep the scoring core free of any network/LLM calls — it must run fully offline.
- Missing or empty JD sections must not crash; degrade gracefully (uniform fallback).
- Keep the `baseline[c]` subtraction in the formula from day one even though it's zero, so calibration drops in later with no refactor.

## Definition of done (Phase 0)

Running the CLI on a sample JD prints a six-entry weight vector summing to 100, plus the per-competency level/peak/similarities, with rubric vectors cached after the first run — and nothing reaches out to a network.
