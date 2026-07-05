from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from config import get_config
from report_store import (
    load_json_index,
    list_reports as list_sqlite_reports,
    upsert_report,
)


REPORTS_DIR = Path("reports")
INDEX_FILE = "index.json"
MAX_HISTORY = 100


@dataclass(frozen=True)
class ReportMetadata:
    review_id: str
    created_at: str
    mode: str = "single"
    target: str = "code-snippet"
    file_count: int = 1
    duration_ms: int | None = None
    model_name: str = field(default_factory=lambda: get_config().model_name)


@dataclass(frozen=True)
class ExportedReport:
    review_id: str
    markdown_path: Path
    html_path: Path
    metadata: ReportMetadata


def create_report_metadata(
    mode: str = "single",
    target: str = "code-snippet",
    file_count: int = 1,
    duration_ms: int | None = None,
    review_id: str | None = None,
) -> ReportMetadata:
    created_at = datetime.now().replace(microsecond=0).isoformat()
    rid = review_id or f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return ReportMetadata(
        review_id=rid,
        created_at=created_at,
        mode=mode,
        target=target,
        file_count=file_count,
        duration_ms=duration_ms,
    )


def _ensure_report_structure(markdown: str, metadata: ReportMetadata) -> str:
    if "## Metadata" in markdown and "## Tool Summary" in markdown:
        return markdown

    metadata_lines = [
        "## Metadata",
        "",
        f"- review_id: {metadata.review_id}",
        f"- created_at: {metadata.created_at}",
        f"- mode: {metadata.mode}",
        f"- target: {metadata.target}",
        f"- file_count: {metadata.file_count}",
        f"- duration_ms: {metadata.duration_ms if metadata.duration_ms is not None else 'unknown'}",
        f"- model_name: {metadata.model_name}",
    ]
    sections = [
        "# ReviewBot Report",
        "## Summary",
        "Generated review report.",
        "## File Overview",
        f"- Target: {metadata.target}",
        f"- File count: {metadata.file_count}",
        "## Findings",
        markdown.strip() or "No findings were generated.",
        "## Suggestions",
        "Review the findings and tool output above.",
        "\n".join(metadata_lines),
    ]
    return "\n\n".join(sections) + "\n"


def _status_class(line: str) -> str:
    lower = line.lower()
    if "fail" in lower:
        return "status-fail"
    if "pass" in lower:
        return "status-pass"
    if "skipped" in lower:
        return "status-skipped"
    return ""


def _markdown_to_simple_html(markdown: str) -> str:
    body_lines: list[str] = []
    in_code = False
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            body_lines.append("</ul>")
            in_list = False

    for line in markdown.splitlines():
        escaped = html.escape(line)
        if line.startswith("```"):
            close_list()
            body_lines.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
        elif in_code:
            body_lines.append(escaped)
        elif line.startswith("# "):
            close_list()
            body_lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            close_list()
            section = html.escape(line[3:].strip())
            body_lines.append(f"<section class=\"report-section\"><h2>{section}</h2>")
        elif line.startswith("### "):
            close_list()
            body_lines.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            if not in_list:
                body_lines.append("<ul>")
                in_list = True
            css_class = _status_class(line)
            class_attr = f' class="{css_class}"' if css_class else ""
            body_lines.append(f"<li{class_attr}>{html.escape(line[2:].strip())}</li>")
        elif line.strip():
            close_list()
            body_lines.append(f"<p>{escaped}</p>")
        else:
            close_list()
            body_lines.append("")
    close_list()
    if in_code:
        body_lines.append("</code></pre>")
    return "\n".join(body_lines)


def _summary_from_markdown(markdown: str, max_chars: int = 180) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("- "):
            return stripped[:max_chars]
    return "Review report generated."


def _relative(path: Path) -> str:
    try:
        return path.as_posix()
    except ValueError:
        return str(path)


def load_report_index(output_dir: str | Path = REPORTS_DIR) -> list[dict[str, Any]]:
    sqlite_records = list_sqlite_reports(output_dir, limit=MAX_HISTORY)
    if sqlite_records:
        return sqlite_records
    return load_json_index(output_dir)


def update_report_index(
    exported: ExportedReport,
    summary: str,
    output_dir: str | Path = REPORTS_DIR,
) -> list[dict[str, Any]]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    index_path = target_dir / INDEX_FILE
    records = load_report_index(target_dir)
    record = {
        **asdict(exported.metadata),
        "markdown_path": _relative(exported.markdown_path),
        "html_path": _relative(exported.html_path),
        "summary": summary,
    }
    upsert_report(record, target_dir)
    records = [item for item in records if item.get("review_id") != exported.review_id]
    records.insert(0, record)
    records = records[:MAX_HISTORY]
    index_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def export_report(
    markdown: str,
    output_dir: str | Path = REPORTS_DIR,
    prefix: str = "review",
    metadata: ReportMetadata | None = None,
    update_index: bool = True,
) -> ExportedReport:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    metadata = metadata or create_report_metadata(review_id=f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    structured_markdown = _ensure_report_structure(markdown, metadata)
    markdown_path = target_dir / f"{metadata.review_id}.md"
    html_path = target_dir / f"{metadata.review_id}.html"

    markdown_path.write_text(structured_markdown, encoding="utf-8")
    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>ReviewBot Report - {html.escape(metadata.review_id)}</title>
  <style>
    :root {{ color-scheme: light; --border: #d0d7de; --muted: #57606a; --bg: #f6f8fa; }}
    body {{ font-family: Arial, sans-serif; line-height: 1.55; max-width: 1080px; margin: 32px auto; padding: 0 18px; color: #24292f; }}
    h1 {{ border-bottom: 1px solid var(--border); padding-bottom: 12px; }}
    h2 {{ margin-top: 28px; }}
    .metadata {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; padding: 12px; background: var(--bg); border: 1px solid var(--border); }}
    .report-section {{ border-top: 1px solid var(--border); margin-top: 22px; }}
    pre {{ background: var(--bg); padding: 12px; overflow-x: auto; border: 1px solid var(--border); }}
    code {{ font-family: Consolas, monospace; }}
    li {{ margin: 4px 0; }}
    .status-pass {{ color: #1a7f37; font-weight: 600; }}
    .status-fail {{ color: #cf222e; font-weight: 600; }}
    .status-skipped {{ color: #9a6700; font-weight: 600; }}
    .muted {{ color: var(--muted); }}
  </style>
</head>
<body>
<div class=\"metadata\">
  <div><strong>Review ID</strong><br>{html.escape(metadata.review_id)}</div>
  <div><strong>Created</strong><br>{html.escape(metadata.created_at)}</div>
  <div><strong>Mode</strong><br>{html.escape(metadata.mode)}</div>
  <div><strong>Target</strong><br>{html.escape(metadata.target)}</div>
  <div><strong>Files</strong><br>{metadata.file_count}</div>
  <div><strong>Duration</strong><br>{metadata.duration_ms if metadata.duration_ms is not None else 'unknown'} ms</div>
</div>
{_markdown_to_simple_html(structured_markdown)}
</body>
</html>
"""
    html_path.write_text(html_doc, encoding="utf-8")
    exported = ExportedReport(
        review_id=metadata.review_id,
        markdown_path=markdown_path,
        html_path=html_path,
        metadata=metadata,
    )
    if update_index:
        update_report_index(exported, _summary_from_markdown(structured_markdown), target_dir)
    return exported
