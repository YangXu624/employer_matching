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
- `GET /api/checks`
- `POST /api/checks`

SQLite demo data is stored in `.data/employer_match.db` at the repo root.
