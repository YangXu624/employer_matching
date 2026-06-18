# Employer Match Backend

This folder is the backend deployment boundary.

For the demo, the backend API runs as one Python service and calls the existing
top-level `employer_match` scorer package.

Run the API locally:

```powershell
.\.venv\Scripts\python.exe -m backend.api.server
```

Default URL:

```text
http://127.0.0.1:8766
```

Expose it for a Vercel frontend demo:

```powershell
ngrok http 8766
```

Then put the ngrok URL in `frontend/config.js`.

Current routes:

- `GET /health`
- `GET /api/samples`
- `POST /api/score`
- `POST /api/match`
- `POST /api/audit` (AI weight auditor, requires `GOOGLE_API_KEY`)
- `GET /api/checks`
- `POST /api/checks`

SQLite demo data is stored in `.data/employer_match.db` at the repo root.

## AI Weight Auditor (Gemini + LangGraph)

`POST /api/audit` runs a LangGraph agent that reviews the 6 embedding-derived
competency weights for a JD and corrects them: it lowers weights where the JD
context/negation contradicts a keyword match (e.g. "no client communication"),
and raises weights for competencies that are clearly implied but unstated. Every
change comes with a reason and JD evidence.

Install the agent dependencies (already in `.venv`):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[agent]"
```

Set the Gemini API key before running the server. It is read from a gitignored
`.env` file at the repo root (or the environment):

```text
# .env  (never commit this)
GOOGLE_API_KEY=your-key-here
# optional, defaults to gemini-2.5-flash
GEMINI_MODEL=gemini-2.5-flash
```

Get a free key from Google AI Studio: https://aistudio.google.com/app/apikey

If `GOOGLE_API_KEY` is missing, `/api/audit` returns a 400 with a clear message
and the rest of the app keeps working.
