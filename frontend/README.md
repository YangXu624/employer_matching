# Employer Match Frontend

This folder is the lightweight Vercel deploy target.

It contains only static browser assets:

- `index.html`
- `config.js`
- `static/app.js`
- `static/styles.css`

The frontend calls the backend API through `window.EMPLOYER_MATCH_API_BASE_URL`
from `config.js`.

For local all-in-one testing, leave it empty:

```js
window.EMPLOYER_MATCH_API_BASE_URL = "";
```

For Vercel plus ngrok or Render, set it to the public backend URL:

```js
window.EMPLOYER_MATCH_API_BASE_URL = "https://your-backend-url.ngrok-free.app";
```

Vercel project root should be this `frontend/` folder so Vercel never installs
the Python ML dependencies.
