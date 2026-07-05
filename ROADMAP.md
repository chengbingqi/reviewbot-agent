# ROADMAP

## Completed

- [x] Remove hard-coded API keys and use environment configuration.
- [x] Add requirements.txt and .env.example.
- [x] Add FastAPI SSE error handling and health check.
- [x] Add pytest tests that do not require a real LLM key.
- [x] Add sqlite-vec RAG metadata support.
- [x] Add Ruff and Bandit scanning.
- [x] Move prompts into prompt files.
- [x] Add RAG Markdown rule import with content_hash deduplication.
- [x] Add multi-file review API.
- [x] Add local directory review script.
- [x] Add Markdown and HTML report export.
- [x] Add lightweight eval cases and runner.
- [x] Add Dockerfile.
- [x] Add GitHub Actions CI.
- [x] Add file-level SSE progress events for multi-file review.
- [x] Add eval pass-rate threshold for regression checks.
- [x] Add local directory review mode.
- [x] Add structured report metadata and HTML styling.
- [x] Add reports/index.json history.
- [x] Add report history API endpoints.
- [x] Add frontend API documentation.

## Todo

- [ ] Add request/session history storage.
- [ ] Add LangGraph state visualization.
- [ ] Add richer eval metrics and regression thresholds.
- [ ] Build optional React frontend using the documented API contract.
- [ ] Add streaming display for directory review progress.
- [ ] Add report templates and configurable output styling.
- [ ] Add authentication and permission controls for shared deployments.
- [ ] Move report history from JSON files to a durable database when needed.
- [ ] Add frontend deployment packaging.
