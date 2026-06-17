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
- **Scoring Rationale (1-5 Scale):** The system evaluates competencies on a 1-5 scale (excluding level 0). This ensures that every competency receives a baseline non-zero weight, preventing "zero-signal" drop-offs for skills not explicitly detailed in short Job Descriptions.

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

# To analyze a specific job description from the examples/jds/ folder:
python -m employer_match.cli --jd examples/jds/fbi.txt
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

## Deployable Split

The repo now has deployment boundaries for a Vercel-friendly demo:

```text
frontend/          # static browser UI; deploy this folder to Vercel
backend/api/       # lightweight Python API, CORS, SQLite demo storage
backend/scorer/    # scorer boundary notes; current scorer code remains in employer_match/
employer_match/    # existing scorer package and local all-in-one web app
```

For a deployed demo, Vercel should use `frontend/` as the project root so it does
not install `sentence-transformers`, `transformers`, `torch`, or model files.
Run the Python API separately:

```bash
python -m backend.api.server
```

The API defaults to `http://127.0.0.1:8766` and exposes:

```text
GET /health
GET /api/samples
POST /api/score
POST /api/match
GET /api/checks
POST /api/checks
```

For a Vercel plus ngrok demo:

```bash
ngrok http 8766
```

Then set `window.EMPLOYER_MATCH_API_BASE_URL` in `frontend/config.js` to the
ngrok or hosted backend URL.

## Future Deployment Notes

Use Hack-Roll as a cautionary reference, not as proof of a completed production
deployment. The `wagmirep/Hack-Roll` repo appeared to have a partial
cloud-hybrid setup rather than a fully deployed online product.

Observed Hack-Roll deployment shape:

- Supabase was the clearly cloud-hosted component:
  `https://tamrgxhjyabdvtubseyu.supabase.co`.
- The mobile app was React Native/Expo and pointed to either a local backend or
  a future production backend through `EXPO_PUBLIC_API_URL`.
- The backend was FastAPI.
- `backend/fly.toml` existed with app name `lahstats-backend-wy`, region `iad`,
  internal port `8000`, and a 1 GB shared VM.
- A backend Dockerfile existed.
- Their task list still marked backend cloud deployment as incomplete/planned.

The useful lesson is that they avoided deploying heavy ML dependencies inside
the web backend. Their backend Dockerfile described a slim production image, and
`requirements-slim.txt` excluded heavy model packages such as `torch`,
`transformers`, and `pyannote.audio`. Heavy ML was expected to run externally,
likely through Colab or another API.

Apply that lesson here in later phases:

- Vercel is a good fit for a lightweight UI/API shell, but not for the current
  in-process `sentence-transformers` scorer because the Python embedding stack is
  too large for Vercel function limits.
- Render can be tested for an all-in-one MVP service hosting both the web UI and
  scorer, but expect possible memory and cold-start pressure on the free tier.
- If Render struggles, split the architecture:
  - lightweight web UI/API on Vercel or Render,
  - embedding/model inference in a separate worker or external inference service,
  - web backend calls that scorer service over HTTP.
- Keep deployment changes out of Phase 0 unless explicitly scoped, because
  Phase 0 remains CLI-first and embedding-only.

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
