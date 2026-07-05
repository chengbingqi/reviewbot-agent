# Deployment Notes

This document covers local production-style runs for `reviewbot-agent`. It does
not include cloud hosting, HTTPS, or domain setup.

## Local Development

Backend:

```bash
cd /d D:\code\reviewbot-agent
conda activate reviewbot-agent
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd /d D:\code\reviewbot-agent\frontend
npm run dev
```

## Environment Variables

Copy `.env.example` to `.env` and edit values:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
AUTH_ENABLED=false
AUTH_TOKEN=change_me
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=20
```

Security features are off by default for local development.

Enable API token auth:

```env
AUTH_ENABLED=true
AUTH_TOKEN=replace_with_a_private_token
```

Clients must send:

```text
Authorization: Bearer <token>
```

Enable in-memory request limiting:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=20
```

Rate limiting applies only to `POST /review` and `POST /review-files`.

## Frontend Production Build

Create production env:

```bash
cd /d D:\code\reviewbot-agent\frontend
copy .env.production.example .env.production
```

Set the backend URL:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_AUTH_TOKEN=
```

Build and preview:

```bash
npm run build
npm run preview
```

Open:

```text
http://127.0.0.1:4173
```

## Docker Backend

Build and run the FastAPI backend:

```bash
docker build -t reviewbot-agent .
docker run --env-file .env -p 8000:8000 -v %cd%\reports:/app/reports reviewbot-agent
```

## Docker Compose Backend

```bash
cd /d D:\code\reviewbot-agent
docker compose up --build
```

The compose file starts only the FastAPI backend and mounts:

```text
./reports:/app/reports
```

This keeps Markdown, HTML, `index.json`, and `report_history.db` available after
container restarts.

## SQLite Report History

Saved reports are indexed in:

```text
reports/report_history.db
```

The legacy file remains supported:

```text
reports/index.json
```

Migrate old JSON history into SQLite:

```bash
python migrate_reports.py
```

The migration is idempotent and can be re-run.

## Common Issues

- Backend returns 401: `AUTH_ENABLED=true` and the client did not send the bearer token.
- Backend returns 429: request limiting is enabled and the per-minute limit was reached.
- Frontend production preview cannot reach API: verify `VITE_API_BASE_URL`.
- Reports disappear in Docker: confirm `./reports:/app/reports` is mounted.
- First RAG run is slow: embedding model download may happen on first use.
