import json
import hmac
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import get_config
from core_graph import AgentState, app as agent_workflow, create_initial_state
from logging_config import logger
from report_exporter import REPORTS_DIR, load_report_index


app = FastAPI(title="ReviewBot API Server", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str = Field(..., max_length=200_000)


class ReviewFile(BaseModel):
    path: str = Field(..., max_length=500)
    content: str = Field(..., max_length=50_000)


class ReviewFilesRequest(BaseModel):
    files: list[ReviewFile]


MAX_REVIEW_FILES = 20
MAX_TOTAL_REVIEW_CHARS = 200_000
_rate_limit_hits: dict[str, list[float]] = {}


def require_auth(authorization: str | None = Header(default=None)) -> None:
    config = get_config()
    if not config.auth_enabled:
        return

    expected = f"Bearer {config.auth_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def enforce_rate_limit(request: Request) -> None:
    config = get_config()
    if not config.rate_limit_enabled:
        return

    limit = max(1, config.rate_limit_per_minute)
    client_host = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60
    hits = [hit for hit in _rate_limit_hits.get(client_host, []) if hit >= window_start]
    if len(hits) >= limit:
        _rate_limit_hits[client_host] = hits
        logger.warning("rate limit exceeded client=%s limit_per_minute=%s", client_host, limit)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    hits.append(now)
    _rate_limit_hits[client_host] = hits


def sse_event(
    event: str,
    message: str,
    node: str | None = None,
    data: Any = None,
    error: str | None = None,
) -> str:
    payload = {
        "event": event,
        "node": node,
        "message": message,
        "data": data,
        "error": error,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream_agent_execution(code: str) -> Generator[str, None, None]:
    yield from stream_agent_state(code)


def stream_agent_state(
    code: str,
    review_files: list[dict[str, str]] | None = None,
    emit_done: bool = True,
    final_data: dict[str, Any] | None = None,
) -> Generator[str, None, None]:
    request_started_at = time.perf_counter()
    if not code.strip():
        logger.info("review request rejected: empty code")
        yield sse_event(
            event="error",
            node="request",
            message="The code field must not be empty.",
            error="empty_code",
        )
        if emit_done:
            yield sse_event(event="done", node="request", message="Review did not run.", data={"report": ""})
        return

    logger.info("review request start code_length=%s", len(code))
    final_state: AgentState | None = None
    seen_errors = 0

    try:
        initial_state = create_initial_state(code, review_files=review_files)
        yield sse_event(event="request_start", node="api", message="Review request accepted.")

        for output in agent_workflow.stream(initial_state):
            for node_name, state_update in output.items():
                final_state = state_update
                node_errors = state_update.get("errors", []) if isinstance(state_update, dict) else []
                new_errors = node_errors[seen_errors:]
                seen_errors = len(node_errors)

                for err in new_errors:
                    yield sse_event(
                        event="error",
                        node=err.get("node", node_name),
                        message=err.get("message", "Recoverable node error."),
                        error=err.get("error"),
                    )

                timing = None
                if isinstance(state_update, dict):
                    timing = state_update.get("timings", {}).get(node_name)
                yield sse_event(
                    event="node_end",
                    node=node_name,
                    message=f"Node {node_name} finished.",
                    data={"elapsed_seconds": timing},
                )

        report = final_state.get("final_report", "") if final_state else ""
        payload = {
            "report": report,
            "timings": final_state.get("timings", {}) if final_state else {},
            "rag_results": final_state.get("rag_results", []) if final_state else [],
            "tool_results": final_state.get("tool_results", {}) if final_state else {},
        }
        if final_data is not None:
            final_data.update(payload)
        if emit_done:
            yield sse_event(
                event="done",
                node="summary",
                message="Review completed.",
                data=payload,
            )
    except Exception as exc:
        logger.exception("review request failed: %s", exc)
        yield sse_event(
            event="error",
            node="workflow",
            message="Review workflow failed unexpectedly.",
            error="internal_error",
        )
        if emit_done:
            yield sse_event(event="done", node="workflow", message="Review stopped.", data={"report": ""})
    finally:
        elapsed = round(time.perf_counter() - request_started_at, 4)
        logger.info("review request end elapsed_seconds=%s", elapsed)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/review")
def review_code_endpoint(
    request: CodeRequest,
    _: None = Depends(require_auth),
    _rate: None = Depends(enforce_rate_limit),
) -> StreamingResponse:
    return StreamingResponse(
        stream_agent_execution(request.code),
        media_type="text/event-stream",
    )


def _combine_review_files(files: list[ReviewFile]) -> tuple[str, list[dict[str, str]], str | None]:
    if not files:
        return "", [], "The files field must contain at least one file."
    if len(files) > MAX_REVIEW_FILES:
        return "", [], f"Too many files. Limit is {MAX_REVIEW_FILES} files per request."

    normalized: list[dict[str, str]] = []
    chunks: list[str] = []
    total_chars = 0
    for file in files:
        content = file.content or ""
        total_chars += len(content)
        if total_chars > MAX_TOTAL_REVIEW_CHARS:
            return "", [], f"Total content is too large. Limit is {MAX_TOTAL_REVIEW_CHARS} characters."
        normalized.append({"path": file.path, "content": content})
        chunks.append(f"# File: {file.path}\n{content}")
    return "\n\n".join(chunks), normalized, None


def _tool_status(tool_results: dict[str, Any], tool_name: str) -> str:
    result = tool_results.get(tool_name) or {}
    return result.get("status", "unknown")


def stream_review_files(code: str, review_files: list[dict[str, str]]) -> Generator[str, None, None]:
    total = len(review_files)
    yield sse_event(
        event="review_start",
        node="review_files",
        message=f"Reviewing {total} files.",
        data={"total_files": total, "mode": "files"},
    )
    for index, item in enumerate(review_files, start=1):
        yield sse_event(
            event="file_start",
            node="review_files",
            message=f"Reviewing {item['path']}",
            data={
                "file_path": item["path"],
                "file_index": index,
                "total_files": total,
                "stage": "queued",
                "status": "running",
            },
        )

    yield sse_event(
        event="tool_start",
        node="review_files",
        message="Running Ruff and Bandit for submitted files.",
        data={"tools": ["ruff", "bandit"], "status": "running"},
    )

    final_data: dict[str, Any] = {}
    yield from stream_agent_state(
        code,
        review_files=review_files,
        emit_done=False,
        final_data=final_data,
    )

    tool_results = final_data.get("tool_results", {})
    for tool_name in ("ruff", "bandit"):
        yield sse_event(
            event="tool_end",
            node="review_files",
            message=f"{tool_name} finished.",
            data={
                "tool": tool_name,
                "status": _tool_status(tool_results, tool_name),
                "result": tool_results.get(tool_name),
            },
        )

    for index, item in enumerate(review_files, start=1):
        for tool_name in ("ruff", "bandit"):
            yield sse_event(
                event="file_progress",
                node="review_files",
                message=f"{tool_name} completed for {item['path']}",
                data={
                    "file_path": item["path"],
                    "file_index": index,
                    "total_files": total,
                    "stage": tool_name,
                    "status": _tool_status(tool_results, tool_name),
                },
            )
        yield sse_event(
            event="file_end",
            node="review_files",
            message=f"Finished {item['path']}",
            data={
                "file_path": item["path"],
                "file_index": index,
                "total_files": total,
                "stage": "complete",
                "status": "done",
            },
        )

    yield sse_event(
        event="summary_end",
        node="summary",
        message="Summary generated.",
        data={"has_report": bool(final_data.get("report"))},
    )
    yield sse_event(
        event="review_complete",
        node="review_files",
        message="File review completed.",
        data={
            "total_files": total,
            "report": final_data.get("report", ""),
            "timings": final_data.get("timings", {}),
            "rag_results": final_data.get("rag_results", []),
            "tool_results": tool_results,
        },
    )
    yield sse_event(
        event="done",
        node="review_files",
        message="Review completed.",
        data=final_data,
    )


@app.post("/review-files")
def review_files_endpoint(
    request: ReviewFilesRequest,
    _: None = Depends(require_auth),
    _rate: None = Depends(enforce_rate_limit),
) -> StreamingResponse:
    code, review_files, error = _combine_review_files(request.files)
    if error:
        return StreamingResponse(
            iter(
                [
                    sse_event(
                        event="error",
                        node="request",
                        message=error,
                        error="invalid_files",
                    ),
                    sse_event(event="done", node="request", message="Review did not run.", data={"report": ""}),
                ]
            ),
            media_type="text/event-stream",
        )
    return StreamingResponse(
        stream_review_files(code, review_files=review_files),
        media_type="text/event-stream",
    )


@app.get("/reports")
def list_reports(_: None = Depends(require_auth)) -> list[dict[str, Any]]:
    return load_report_index(REPORTS_DIR)


@app.get("/reports/{review_id}")
def get_report(review_id: str, _: None = Depends(require_auth)) -> dict[str, Any]:
    records = load_report_index(REPORTS_DIR)
    record = next((item for item in records if item.get("review_id") == review_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")

    reports_root = Path(REPORTS_DIR).resolve()
    markdown_path = Path(record.get("markdown_path", "")).resolve()
    html_path = Path(record.get("html_path", "")).resolve()
    if reports_root not in markdown_path.parents and markdown_path != reports_root:
        raise HTTPException(status_code=400, detail="Invalid report path.")
    if html_path.exists() and reports_root not in html_path.parents and html_path != reports_root:
        raise HTTPException(status_code=400, detail="Invalid report path.")
    if not markdown_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found.")
    return {
        "metadata": record,
        "markdown": markdown_path.read_text(encoding="utf-8"),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path) if html_path.exists() else None,
    }


@app.get("/reports/{review_id}/html", response_class=HTMLResponse)
def get_report_html(review_id: str, _: None = Depends(require_auth)) -> HTMLResponse:
    records = load_report_index(REPORTS_DIR)
    record = next((item for item in records if item.get("review_id") == review_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")

    reports_root = Path(REPORTS_DIR).resolve()
    html_path = Path(record.get("html_path", "")).resolve()
    if reports_root not in html_path.parents and html_path != reports_root:
        raise HTTPException(status_code=400, detail="Invalid report path.")
    if not html_path.exists() or html_path.suffix.lower() != ".html":
        raise HTTPException(status_code=404, detail="HTML report file not found.")

    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000)
