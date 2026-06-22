# Employer Match Frontend

This folder is the lightweight Vercel deploy target.

Static pages:

- `index.html` — landing (seeker vs employer)
- `login-seeker.html`, `login-employer.html` — Supabase auth
- `seeker.html` — resume upload + competency passport
- `employer.html` — JD scorer + match (requires employer login)
- `config.js` — API base URL + Supabase anon config

Shared assets:

- `static/app.js` — employer scorer UI
- `static/seeker.js` — seeker dashboard
- `static/auth.js`, `static/supabase-client.js`, `static/login.js`
- `static/styles.css`

Set in `config.js`:

```js
window.EMPLOYER_MATCH_API_BASE_URL = "https://your-backend-url.ngrok-free.app";
window.SUPABASE_URL = "https://your-project.supabase.co";
window.SUPABASE_ANON_KEY = "your-anon-key";
```

Run the SQL in [`../supabase/migration.sql`](../supabase/migration.sql) in your Supabase project before using login.

Vercel project root should be this `frontend/` folder.

Local dev (clean URLs like Vercel — use this instead of plain `http.server`):

```powershell
.\.venv\Scripts\python.exe frontend\serve.py --port 5500
```
