# Jobs API

Read/write contract for stored, scored job descriptions. This is the canonical
store the **matching engine** consumes. The matching/ranking logic itself is out
of scope here — you read this list and rank candidates however you like.

- **Base URL (local):** `http://127.0.0.1:8766`
- **Auth:** none in v1.
- **Storage:** SQLite by default (local file at `.data/jobs.db`). Supabase is
  opt-in via `JOB_STORE=supabase`, in which case the backend uses the service
  role key and the browser never talks to Supabase directly.

## Data model

| Field | Type | Purpose |
|-------|------|---------|
| `id` | uuid (string) | Stable job id |
| `title` | string | Job label / display name |
| `jd_text` | string | Full pasted job description |
| `weights` | object | Flat map `competency_id -> weight`, sums to ~100 |
| `competencies` | array | Per-competency `label`, `description`, `weight`, `matched_level` |
| `score` | object | Full `/api/score` payload (audit/debug) |
| `status` | string | `draft` \| `published` \| `archived` |
| `created_at` | timestamp | Recency / sorting |
| `updated_at` | timestamp | Last modified |

The 8 `weights` keys are the NACE competencies (see
`employer_match/rubric_store.py` → `COMPETENCY_ORDER`):

```
career_self_development, communication, critical_thinking, equity_inclusion,
leadership, professionalism, teamwork, technology
```

Each `competencies` entry carries the rubric `label` + `description` (the
human-readable definition) so you do not need to load the rubric file
separately:

```json
{
  "competency_id": "technology",
  "label": "Technology",
  "description": "Demand the role places on using tools, software, and systems...",
  "weight": 19,
  "matched_level": 3
}
```

## `GET /api/jobs` — list jobs

Query params:

| Param | Default | Notes |
|-------|---------|-------|
| `status` | `published` | Use `all` (or empty) to include every status |
| `limit` | `100` | Capped at 1000 |

```bash
curl "http://127.0.0.1:8766/api/jobs?status=published&limit=100"
```

Response:

```json
{
  "jobs": [
    {
      "id": "uuid",
      "title": "Data Platform Engineer",
      "jd_text": "...",
      "weights": { "technology": 19, "communication": 8, "...": 0 },
      "competencies": [
        {
          "competency_id": "technology",
          "label": "Technology",
          "description": "...",
          "weight": 19,
          "matched_level": 3
        }
      ],
      "score": { "overall_score": 87, "competencies": [], "model": "..." },
      "status": "published",
      "created_at": "2026-06-23T00:00:00+00:00",
      "updated_at": "2026-06-23T00:00:00+00:00"
    }
  ]
}
```

## `GET /api/jobs/{id}` — single job

```bash
curl "http://127.0.0.1:8766/api/jobs/<uuid>"
```

Returns `{ "job": { ... } }`, or `404 { "error": "Job not found" }`.

## `POST /api/jobs` — save a scored JD

Used by the employer UI after Score + weight adjustment. The backend **derives
`competencies`** (label + description from the rubric + weight + matched_level
from `score`) before insert — clients do not send descriptions.

Request:

```json
{
  "title": "Data Platform Engineer",
  "jd_text": "...",
  "weights": { "career_self_development": 12, "communication": 8, "...": 0 },
  "score": { "overall_score": 87, "competencies": [], "model": "..." },
  "status": "published"
}
```

Validation: `weights` must contain all 8 competency keys and sum to ~100
(±1). On success returns `201 { "job": { "id": "...", ... } }`. Invalid input
returns `400 { "error": "..." }`.
