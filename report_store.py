from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


INDEX_FILE = "index.json"
DB_FILE = "report_history.db"
MAX_HISTORY = 100


def get_db_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / DB_FILE


def init_report_store(output_dir: str | Path) -> Path:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = get_db_path(target_dir)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                review_id TEXT PRIMARY KEY,
                created_at TEXT,
                mode TEXT,
                target TEXT,
                file_count INTEGER,
                duration_ms INTEGER,
                model_name TEXT,
                markdown_path TEXT,
                html_path TEXT,
                summary TEXT
            )
            """
        )
        conn.commit()
    return db_path


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_id": record.get("review_id", ""),
        "created_at": record.get("created_at", ""),
        "mode": record.get("mode", "single"),
        "target": record.get("target", "code-snippet"),
        "file_count": int(record.get("file_count") or 0),
        "duration_ms": record.get("duration_ms"),
        "model_name": record.get("model_name"),
        "markdown_path": record.get("markdown_path", ""),
        "html_path": record.get("html_path", ""),
        "summary": record.get("summary", ""),
    }


def upsert_report(record: dict[str, Any], output_dir: str | Path) -> None:
    normalized = _normalize_record(record)
    if not normalized["review_id"]:
        return
    db_path = init_report_store(output_dir)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO reports (
                review_id, created_at, mode, target, file_count, duration_ms,
                model_name, markdown_path, html_path, summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(review_id) DO UPDATE SET
                created_at=excluded.created_at,
                mode=excluded.mode,
                target=excluded.target,
                file_count=excluded.file_count,
                duration_ms=excluded.duration_ms,
                model_name=excluded.model_name,
                markdown_path=excluded.markdown_path,
                html_path=excluded.html_path,
                summary=excluded.summary
            """,
            (
                normalized["review_id"],
                normalized["created_at"],
                normalized["mode"],
                normalized["target"],
                normalized["file_count"],
                normalized["duration_ms"],
                normalized["model_name"],
                normalized["markdown_path"],
                normalized["html_path"],
                normalized["summary"],
            ),
        )
        conn.commit()


def list_reports(output_dir: str | Path, limit: int = MAX_HISTORY) -> list[dict[str, Any]]:
    db_path = get_db_path(output_dir)
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT review_id, created_at, mode, target, file_count, duration_ms,
                   model_name, markdown_path, html_path, summary
            FROM reports
            ORDER BY created_at DESC, review_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_report_record(review_id: str, output_dir: str | Path) -> dict[str, Any] | None:
    db_path = get_db_path(output_dir)
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT review_id, created_at, mode, target, file_count, duration_ms,
                   model_name, markdown_path, html_path, summary
            FROM reports
            WHERE review_id = ?
            """,
            (review_id,),
        ).fetchone()
    return dict(row) if row else None


def load_json_index(output_dir: str | Path) -> list[dict[str, Any]]:
    index_path = Path(output_dir) / INDEX_FILE
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def migrate_index_to_sqlite(output_dir: str | Path) -> tuple[int, int]:
    records = load_json_index(output_dir)
    if not records:
        init_report_store(output_dir)
        return 0, 0

    existing_ids = {record["review_id"] for record in list_reports(output_dir, limit=10_000)}
    inserted = 0
    skipped = 0
    for record in records:
        review_id = record.get("review_id")
        if not review_id or review_id in existing_ids:
            skipped += 1
            continue
        upsert_report(record, output_dir)
        existing_ids.add(review_id)
        inserted += 1
    return inserted, skipped
