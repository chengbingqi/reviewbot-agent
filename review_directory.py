import argparse
import json
import time
from pathlib import Path
from typing import Any

import requests

from core_graph import app as agent_workflow, create_initial_state
from report_exporter import create_report_metadata, export_report


IGNORED_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules"}
DEFAULT_API_URL = "http://127.0.0.1:8000/review-files"


def collect_python_files(
    root: Path, max_files: int = 20, max_chars_per_file: int = 20_000
) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if len(files) >= max_files:
            break
        content = path.read_text(encoding="utf-8", errors="replace")[:max_chars_per_file]
        files.append({"path": path.relative_to(root).as_posix(), "content": content})
    return files


def _parse_sse_report(text: str) -> str:
    report = ""
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if payload.get("event") == "done":
            data: dict[str, Any] = payload.get("data") or {}
            report = data.get("report", report)
    return report


def review_directory(
    path: str,
    api_url: str = DEFAULT_API_URL,
    max_files: int = 20,
    max_chars_per_file: int = 20_000,
    local: bool = False,
) -> str:
    root = Path(path).resolve()
    files = collect_python_files(root, max_files=max_files, max_chars_per_file=max_chars_per_file)
    if not files:
        return "# Code Review Report\n\nNo Python files found."
    if local:
        combined = "\n\n".join(f"# File: {item['path']}\n{item['content']}" for item in files)
        state = agent_workflow.invoke(create_initial_state(combined, review_files=files))
        return state.get("final_report", "")
    response = requests.post(api_url, json={"files": files}, timeout=300)
    response.raise_for_status()
    return _parse_sse_report(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a local Python directory via ReviewBot API.")
    parser.add_argument("--path", required=True, help="Directory to review.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="ReviewBot /review-files endpoint.")
    parser.add_argument("--max-files", type=int, default=20)
    parser.add_argument("--max-chars-per-file", type=int, default=20_000)
    parser.add_argument("--local", action="store_true", help="Run local graph logic without calling FastAPI.")
    parser.add_argument("--save-report", action="store_true")
    args = parser.parse_args()

    started_at = time.perf_counter()
    files = collect_python_files(
        Path(args.path).resolve(),
        max_files=args.max_files,
        max_chars_per_file=args.max_chars_per_file,
    )
    report = review_directory(
        args.path,
        api_url=args.api_url,
        max_files=args.max_files,
        max_chars_per_file=args.max_chars_per_file,
        local=args.local,
    )
    print(report)
    if args.save_report:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        exported = export_report(
            report,
            prefix="directory_review",
            metadata=create_report_metadata(
                mode="directory-local" if args.local else "directory-api",
                target=str(Path(args.path).resolve()),
                file_count=len(files),
                duration_ms=duration_ms,
            ),
        )
        print(f"\nSaved Markdown: {exported.markdown_path}")
        print(f"Saved HTML: {exported.html_path}")


if __name__ == "__main__":
    main()
