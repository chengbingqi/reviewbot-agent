# reviewbot-agent

`reviewbot-agent` is an AI code review engineering prototype. It provides a
FastAPI backend, LangGraph workflow, LangChain model calls, sqlite-vec RAG rule
retrieval, Ruff/Bandit tool scans, report export, lightweight evals, and a React
Ink terminal UI.

The project is designed for local development and repeatable engineering demos.
It is not a replacement for a production security scanner.

## Core Flow

```text
code or files
-> FastAPI /review or /review-files
-> LangGraph planner/coordinator/checker/summary nodes
-> Ruff and Bandit scans
-> sqlite-vec RAG rule retrieval
-> ChatOpenAI-compatible model call when OPENAI_API_KEY is configured
-> SSE progress events and Markdown report
```

## Tech Stack

- Python 3.10 or 3.11 recommended.
- FastAPI, Uvicorn, Pydantic.
- LangChain, LangGraph, langchain-openai.
- sqlite-vec, langchain-huggingface, sentence-transformers.
- Ruff, Bandit, pytest.
- TypeScript, React Ink, tsx.
- Docker and GitHub Actions CI.

## Directory Structure

```text
reviewbot-agent/
|-- api_server.py
|-- core_graph.py
|-- rag_db.py
|-- ingest_rules.py
|-- review_directory.py
|-- report_exporter.py
|-- test_client.py
|-- config.py
|-- tools.py
|-- prompts/
|-- rules/
|-- evals/
|-- tests/
|-- cli-tui/
|-- Dockerfile
|-- .github/workflows/ci.yml
`-- ROADMAP.md
```

## Environment Setup

Anaconda:

```bash
cd /d D:\code\reviewbot-agent

conda create -n reviewbot-agent python=3.10 -y
conda activate reviewbot-agent

pip install -r requirements.txt

copy .env.example .env
```

Edit `.env` and fill in your own key:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
AUTH_ENABLED=false
AUTH_TOKEN=change_me
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=20
```

Do not commit `.env`.

Optional API token authentication and request limiting are disabled by default.
Enable them only when you need production-style local hardening:

```env
AUTH_ENABLED=true
AUTH_TOKEN=replace_with_a_private_token
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=20
```

When auth is enabled, clients must send `Authorization: Bearer <token>`.

## RAG Rule Import

Initialize or migrate the sqlite-vec database:

```bash
python rag_db.py
```

Import sample Markdown rules:

```bash
python ingest_rules.py --file rules/security_rules.md
python ingest_rules.py --dir rules
```

Rules are deduplicated by `content_hash`. Re-importing the same files reports
skipped records instead of inserting duplicates.

## Start Backend

```bash
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Single Snippet Review

```bash
python test_client.py
python test_client.py --save-report
```

`--save-report` writes Markdown and HTML files to `reports/`.

## Multi-file Review API

`POST /review-files` accepts multiple Python files while preserving file paths:

```json
{
  "files": [
    {"path": "app/main.py", "content": "def hello():\n    print('hello')"},
    {"path": "app/utils.py", "content": "def add(a,b):\n    return a+b"}
  ]
}
```

Limits are enforced in `api_server.py` to avoid very large requests.

The endpoint emits file-level SSE events such as `review_start`, `file_start`,
`file_progress`, `file_end`, `tool_end`, `review_complete`, and `done`. See
[docs/frontend_api.md](docs/frontend_api.md) for the event contract intended for
future React frontend work.

## Directory Review

Review a local directory through the running backend:

```bash
python review_directory.py --path D:\code\some-project --max-files 20
python review_directory.py --path D:\code\some-project --save-report
```

Run without a backend by using local mode:

```bash
python review_directory.py --path D:\code\some-project --local --max-files 20
python review_directory.py --path D:\code\some-project --local --save-report
```

The script reads `.py` files only and ignores `.venv`, `venv`, `__pycache__`,
`.git`, and `node_modules`.

## Report Export

Reports are exported by `report_exporter.py`:

```text
reports/review_YYYYMMDD_HHMMSS.md
reports/review_YYYYMMDD_HHMMSS.html
```

The HTML output is intentionally simple and local-friendly.

Exported reports are normalized toward this structure:

```text
ReviewBot Report
|-- Summary
|-- File Overview
|-- Tool Summary
|-- RAG References
|-- Findings
|-- Suggestions
`-- Metadata
```

Each saved report updates `reports/report_history.db` and keeps
`reports/index.json` as a compatibility file. The backend keeps the latest 100
records.
The backend exposes report history through:

```text
GET /reports
GET /reports/{review_id}
GET /reports/{review_id}/html
```

Migrate old `reports/index.json` data into SQLite:

```bash
python migrate_reports.py
```

## Evals

Run lightweight local evals:

```bash
python evals/run_evals.py --min-pass-rate 0.8
```

Run evals through a running backend:

```bash
python evals/run_evals.py --use-api
```

Results are written to:

```text
evals/eval_results.csv
```

The eval runner does not require a real LLM key; without one, it evaluates the
fallback/tool-based report.

The command exits with a non-zero code when the pass rate is below the threshold.

## React Ink TUI

```bash
cd /d D:\code\reviewbot-agent\cli-tui
npm install
npm audit
npx tsx ui.tsx
```

The current TUI sends built-in demo code to the backend.

## React Web Frontend

Terminal 1: start the backend.

```bash
cd /d D:\code\reviewbot-agent
conda activate reviewbot-agent
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2: start the React frontend.

```bash
cd /d D:\code\reviewbot-agent\frontend
npm install
copy .env.example .env
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The web UI supports backend health checks, single code review, multi-file review,
SSE progress, file progress, report viewing, report history, Markdown download,
and HTML report preview.

The report viewer renders Markdown with headings, lists, tables, links, and code
blocks. Rendered Markdown is sanitized on the frontend. Multi-file review also
supports a selected-file list, file-size and line-count display, content preview,
single-file removal, and clearing all selected files before submitting.

Frontend checks:

```bash
cd /d D:\code\reviewbot-agent\frontend
npm audit
npx tsc --noEmit
npm test
npm run build
```

Playwright E2E checks require the backend to be running:

```bash
cd /d D:\code\reviewbot-agent\frontend
npm run e2e
npm run e2e:smoke
```

If Playwright browsers are missing:

```bash
npx playwright install
```

Production build and local preview:

```bash
copy .env.production.example .env.production
npm run build
npm run preview
```

`dev` is for local development, `build` writes `dist/`, and `preview` serves the
production build locally. Configure `VITE_API_BASE_URL` for the backend address
used by the built frontend.

Manual end-to-end checks are listed in
[docs/manual_test_checklist.md](docs/manual_test_checklist.md).

## Tests

```bash
cd /d D:\code\reviewbot-agent
pytest -q
```

Tests do not require a real LLM key and do not require the backend to be running.

Playwright E2E tests do require a running backend on `127.0.0.1:8000`, but still
work with the backend fallback path when no real LLM key is configured.

## Docker

Build and run the FastAPI backend:

```bash
docker build -t reviewbot-agent .
docker run --env-file .env -p 8000:8000 reviewbot-agent
```

The image does not copy `.env`. `sentence-transformers` may download the
embedding model at runtime or during first RAG use.

Docker Compose backend run with report persistence:

```bash
docker compose up --build
```

The compose file mounts `./reports:/app/reports`.

More deployment notes are in [docs/deployment.md](docs/deployment.md).

## CI

GitHub Actions workflow is defined in:

```text
.github/workflows/ci.yml
```

It installs dependencies on Python 3.11, runs syntax checks, executes
`pytest -q`, runs evals, installs frontend dependencies, runs npm audit,
TypeScript checks, Vitest, frontend build, and Playwright smoke E2E:

```bash
python evals/run_evals.py --min-pass-rate 0.8
npm run e2e:smoke
```

CI does not require `OPENAI_API_KEY`.

## Logging

Runtime logs are written to:

```text
logs/reviewbot.log
```

Logs include request lifecycle, node timing, RAG hit counts, tool status, and
recoverable errors. API keys are not logged.

## Common Issues

- `OPENAI_API_KEY is not configured`: copy `.env.example` to `.env` and fill in
  your key.
- `sqlite_vec` import error: install dependencies in the active conda environment.
- First RAG use is slow: the embedding model may be downloading.
- Ruff or Bandit skipped: ensure the environment scripts directory is on `PATH`.
- `401 Authentication required`: `AUTH_ENABLED=true`; configure the bearer token
  in your client or frontend `.env`.
- `429 Rate limit exceeded`: lower request volume or increase
  `RATE_LIMIT_PER_MINUTE`.
- Old report history missing: run `python migrate_reports.py`.
- PowerShell blocks `npm.ps1`: use `cmd /c npm ...` or adjust execution policy.
- Docker slim image builds can be slow because ML dependencies are large.

More engineering plans are tracked in [ROADMAP.md](ROADMAP.md).
