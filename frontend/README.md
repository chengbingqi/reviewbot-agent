# ReviewBot Frontend

## Prerequisites

Start the FastAPI backend first:

```bash
cd /d D:\code\reviewbot-agent
conda activate reviewbot-agent
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

## Install

```bash
cd /d D:\code\reviewbot-agent\frontend
npm install
copy .env.example .env
```

## Configure API URL

`.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_AUTH_TOKEN=
```

Leave `VITE_AUTH_TOKEN` empty when backend auth is disabled. If backend
`AUTH_ENABLED=true`, set it to the same private token. The page only shows
whether a token is configured; it does not display the token.

## Start Dev Server

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Test And Build

```bash
npm audit
npx tsc --noEmit
npm test
npm run build
```

## E2E Tests

Start the backend first, then run:

```bash
npm run e2e
npm run e2e:smoke
```

Interactive Playwright UI:

```bash
npm run e2e:ui
```

Install Playwright browsers if needed:

```bash
npx playwright install
```

## Production Build Preview

Production builds read `VITE_API_BASE_URL` and optional `VITE_AUTH_TOKEN` from
`.env.production`.

```bash
copy .env.production.example .env.production
npm run build
npm run preview
```

Open:

```text
http://127.0.0.1:4173
```

`dev` starts the Vite development server, `build` generates `dist/`, and
`preview` serves the built frontend locally.

## Features

- Backend health check.
- Single code review.
- Multi-file `.py` review with selected-file list, preview, remove, and clear actions.
- POST SSE stream parsing with realtime events.
- Per-file progress display.
- Markdown report rendering with GFM tables, code blocks, links, copy, and download.
- Report history and report detail views.
- HTML report preview through the backend report endpoint.

## Common Issues

- Backend offline: start uvicorn on `127.0.0.1:8000`.
- CORS error: confirm the backend includes `http://127.0.0.1:5173`.
- 401 from backend: set `VITE_AUTH_TOKEN` when backend auth is enabled.
- Empty report history: save a report from the CLI or directory review first.
- HTML preview does not open: confirm the selected report has an `html_path` in history and that the backend can read `reports/`.
- SSE parse failure: keep the event timeline visible and check the backend stream payload in DevTools.
- Playwright browser missing: run `npx playwright install`.
- E2E connection failure: confirm backend is on `127.0.0.1:8000` and frontend can start on `127.0.0.1:5173`.
- Production preview API failure: check `VITE_API_BASE_URL` in `.env.production`.
- Missing model key: backend will still return fallback/tool-based results.
