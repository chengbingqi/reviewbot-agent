# Manual Test Checklist

Use this checklist for final local integration checks before a demo or release.

## 1. Start Backend

```bash
cd /d D:\code\reviewbot-agent
conda activate reviewbot-agent
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

## 2. Start Frontend

```bash
cd /d D:\code\reviewbot-agent\frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## 3. Web UI Checks

- [ ] Backend status shows `Backend Online`.
- [ ] Single code review accepts demo code and starts review.
- [ ] Realtime Events area receives SSE events.
- [ ] Report area displays Markdown-rendered output or a clear fallback/error.
- [ ] Copy Report works.
- [ ] Download Markdown creates a `.md` file.
- [ ] Multi-file review accepts at least two `.py` files.
- [ ] File list shows file name, size, line count, and status.
- [ ] File preview preserves indentation and line breaks.
- [ ] Remove File removes one selected file.
- [ ] Clear Files removes all selected files.
- [ ] Reports tab shows report history or empty state.
- [ ] Report detail shows metadata and Markdown content.
- [ ] HTML Preview opens the exported HTML report when available.
- [ ] If `AUTH_ENABLED=true`, protected endpoints reject missing token and work with the configured bearer token.
- [ ] If `RATE_LIMIT_ENABLED=true`, repeated review requests eventually return 429.

## 4. Backend Entry Checks

- [ ] FastAPI docs opens: `http://127.0.0.1:8000/docs`.
- [ ] Health endpoint returns `{"status":"ok"}`.
- [ ] Report history endpoint returns JSON: `http://127.0.0.1:8000/reports`.

## 5. CLI And Tooling Checks

```bash
python test_client.py
python review_directory.py --path D:\code\reviewbot-agent --local --max-files 3
python evals/run_evals.py --min-pass-rate 0.8
python migrate_reports.py
```

## 6. TUI Checks

```bash
cd /d D:\code\reviewbot-agent\cli-tui
npm audit
npx tsc --noEmit
```

## 7. Frontend Production Preview

```bash
cd /d D:\code\reviewbot-agent\frontend
npm run build
npm run preview
```

Open:

```text
http://127.0.0.1:4173
```

Confirm the production preview can still reach the backend configured by
`VITE_API_BASE_URL`.

## 8. Docker Compose Backend

```bash
cd /d D:\code\reviewbot-agent
docker compose up --build
```

- [ ] Backend starts on `http://127.0.0.1:8000`.
- [ ] `./reports` is mounted and persists generated reports.
