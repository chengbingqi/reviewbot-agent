# Frontend API Notes

This document describes the backend contract for a future React frontend.

The current Vite frontend runs at:

```text
http://127.0.0.1:5173
http://localhost:5173
```

The FastAPI backend allows these origins through CORS for local development.

## Optional Auth

Backend auth is disabled by default:

```env
AUTH_ENABLED=false
AUTH_TOKEN=change_me
```

When `AUTH_ENABLED=true`, protected endpoints require:

```text
Authorization: Bearer <AUTH_TOKEN>
```

Protected endpoints:

- `POST /review`
- `POST /review-files`
- `GET /reports`
- `GET /reports/{review_id}`
- `GET /reports/{review_id}/html`

The frontend reads `VITE_AUTH_TOKEN`. If the value is empty, it sends no
`Authorization` header. If set, it sends the bearer token on protected requests.
The UI may show `Auth: Token configured`, but must not display the token.

## Optional Rate Limiting

Backend rate limiting is also disabled by default:

```env
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=20
```

When enabled, it applies only to:

- `POST /review`
- `POST /review-files`

It does not apply to `/health`, `/docs`, or report history reads.

## Health

```http
GET /health
```

Response:

```json
{"status": "ok"}
```

## Single Snippet Review

```http
POST /review
Content-Type: application/json
```

Request:

```json
{"code": "def hello():\n    print('hello')"}
```

Response is Server-Sent Events with `data: {...}` payloads.

Because both `/review` and `/review-files` use POST requests, the frontend uses
`fetch` with `ReadableStream` parsing instead of `EventSource`, which only
supports GET without extra request bodies.

## Multi-file Review

```http
POST /review-files
Content-Type: application/json
```

Request:

```json
{
  "files": [
    {"path": "app/main.py", "content": "def hello():\n    print('hello')"},
    {"path": "app/utils.py", "content": "def add(a, b):\n    return a + b"}
  ]
}
```

## SSE Payload Shape

All SSE messages use the same top-level shape:

```json
{
  "event": "file_progress",
  "node": "review_files",
  "message": "ruff completed for app/main.py",
  "data": {
    "file_path": "app/main.py",
    "file_index": 1,
    "total_files": 2,
    "stage": "ruff",
    "status": "pass"
  },
  "error": null
}
```

## Common Events

- `review_start`: multi-file review accepted.
- `request_start`: single review accepted.
- `file_start`: a file entered review.
- `file_progress`: file-level tool progress.
- `file_end`: file review finished.
- `tool_start`: shared tool scan started.
- `tool_end`: shared tool scan finished.
- `node_end`: LangGraph node finished.
- `summary_end`: summary generation finished.
- `review_complete`: multi-file review finished with report data.
- `done`: compatibility event with final report payload.
- `error`: recoverable or terminal error.

## Error Event

```json
{
  "event": "error",
  "node": "request",
  "message": "The files field must contain at least one file.",
  "data": null,
  "error": "invalid_files"
}
```

Do not assume an error event always ends the stream. Some errors are recoverable
and the backend may still emit `done`.

## Report History

```http
GET /reports
```

Returns the JSON contents of `reports/index.json`.
New reports are indexed in SQLite at `reports/report_history.db`; `index.json`
is still maintained as a compatibility file.

```http
GET /reports/{review_id}
```

Returns:

```json
{
  "metadata": {
    "review_id": "review_20260705_153012",
    "created_at": "2026-07-05T15:30:12",
    "mode": "directory",
    "target": "D:\\code\\some-project",
    "file_count": 8,
    "duration_ms": 1200,
    "model_name": "deepseek-chat"
  },
  "markdown": "# ReviewBot Report\n...",
  "markdown_path": "reports/review_20260705_153012.md",
  "html_path": "reports/review_20260705_153012.html"
}
```

```http
GET /reports/{review_id}/html
```

Returns the exported HTML report as `text/html`. The backend resolves the
stored `html_path` through `reports/index.json`, restricts reads to the
`reports/` directory, rejects path traversal, and returns `404` when the report
or HTML file does not exist.

## Suggested Frontend Areas

- Input editor.
- File list.
- Real-time progress timeline.
- Tool Summary.
- RAG References.
- Findings and Suggestions.
- Report download links.
- Historical report list.

## Component Mapping

- `HealthStatus`: `GET /health`
- `CodeReviewPanel`: `POST /review`
- `MultiFileReviewPanel`: `POST /review-files`
- `EventTimeline`: SSE payloads from review endpoints
- `FileProgressList`: `file_start`, `file_progress`, `file_end`
- `ReportViewer`: final `done` or `review_complete` report
- `ReportHistory`: `GET /reports`
- `ReportDetail`: `GET /reports/{review_id}`

`ReportDetail` can open `GET /reports/{review_id}/html` in a new browser tab for
HTML preview.

Report detail views should display these fields when available, using `N/A` for
missing values:

- `review_id`
- `created_at`
- `mode`
- `target`
- `file_count`
- `duration_ms`
- `model_name`
- `markdown_path`
- `html_path`

If HTML preview fails, show a clear message rather than exposing local filesystem
details.

## Markdown Rendering

The React frontend renders report Markdown with `react-markdown`,
`remark-gfm`, and `rehype-sanitize`.

Supported display features:

- Headings and nested sections.
- Lists.
- Fenced code blocks.
- GFM tables.
- Links.

Do not render raw HTML from the report directly. If Markdown rendering fails,
fallback to a plain `<pre>` view so the user can still copy and download the
original report.

## Multi-file Preview

The frontend file picker keeps the `/review-files` request shape unchanged:

```json
{"files": [{"path": "main.py", "content": "print('hello')"}]}
```

Local-only UI metadata such as file size and line count is used only for display.
The page should warn on unsupported non-`.py` files, empty files, and too many
selected files. File preview should preserve whitespace, cap very long previews,
and never mutate the content submitted to the backend.

## SSE Parse Errors

The POST review endpoints stream `data: {...}` blocks. The frontend parser should
buffer partial chunks, split on blank lines, ignore keepalive/comment blocks, and
show a readable error when JSON parsing fails. A parse error should not erase the
previous timeline or report state.

## Frontend Tests

The frontend uses Vitest and React Testing Library:

```bash
cd /d D:\code\reviewbot-agent\frontend
npm test
```

Current tests cover SSE payload parsing, Markdown report rendering, report
history loading, health-check failure messaging, and multi-file list/preview
actions.

## Playwright E2E Tests

The frontend also includes Playwright tests:

```bash
cd /d D:\code\reviewbot-agent\frontend
npm run e2e
```

Coverage:

- App shell and health area.
- Reports tab empty/detail state.
- Single-code review flow using backend fallback behavior when no LLM key is set.
- Multi-file selection, preview, remove, and clear actions.

The E2E suite starts the Vite frontend automatically, but expects the FastAPI
backend to already be running at `VITE_API_BASE_URL` or
`http://127.0.0.1:8000`.

CI runs a smaller smoke subset with:

```bash
npm run e2e:smoke
```

The smoke subset avoids requiring a real LLM key.

## Production Build Configuration

The built frontend reads the backend base URL from:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For local production preview:

```bash
copy .env.production.example .env.production
npm run build
npm run preview
```

Set `VITE_API_BASE_URL` to the deployed backend address for non-local
environments.

## Common Frontend Errors

- Backend is not running: health check fails.
- CORS error: confirm frontend origin is `127.0.0.1:5173` or `localhost:5173`.
- `OPENAI_API_KEY` missing: backend may emit warning/error events but can still
  return fallback reports.
- SSE JSON parse failure: show the parse error and keep previous events visible.
- Empty report history: `reports/index.json` is created after saving reports.
- HTML preview fails: verify `/reports/{review_id}/html` returns `200` and the
  stored HTML path is still inside `reports/`.
