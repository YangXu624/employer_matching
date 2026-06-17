# Scorer Boundary

The current scorer implementation still lives in the top-level `employer_match`
package so the existing CLI, tests, and local MVP keep working during the first
deployment split.

For now, `backend/api/server.py` imports:

- `employer_match.web_app.score_text_payload`
- `employer_match.web_app.match_candidates`
- `employer_match.web_app.load_sample_jds`

When the deployment split is stable, move the scorer-only modules here:

- `config.py`
- `rubric_store.py`
- `embedder.py`
- `scorer.py`
- `pipeline.py`
- `data/rubric.json`
- `data/candidates.csv`

Keep heavy dependencies such as `sentence-transformers`, `transformers`, and
`torch` on the backend/scorer side only. The Vercel frontend should never install
them.
