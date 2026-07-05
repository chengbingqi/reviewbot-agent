import json

from report_exporter import create_report_metadata, export_report, load_report_index
from report_store import get_report_record, list_reports, migrate_index_to_sqlite, upsert_report


def test_report_store_upsert_and_query(tmp_path):
    record = {
        "review_id": "review_sqlite",
        "created_at": "2026-07-05T12:00:00",
        "mode": "single",
        "target": "code-snippet",
        "file_count": 1,
        "duration_ms": 123,
        "model_name": "test-model",
        "markdown_path": "reports/review_sqlite.md",
        "html_path": "reports/review_sqlite.html",
        "summary": "summary",
    }

    upsert_report(record, tmp_path)

    records = list_reports(tmp_path)
    assert records[0]["review_id"] == "review_sqlite"
    assert get_report_record("review_sqlite", tmp_path)["model_name"] == "test-model"


def test_export_report_writes_sqlite_and_json_compatible_index(tmp_path):
    export_report(
        "# SQLite",
        output_dir=tmp_path,
        metadata=create_report_metadata(review_id="review_export_sqlite"),
    )

    records = load_report_index(tmp_path)

    assert records[0]["review_id"] == "review_export_sqlite"
    assert (tmp_path / "report_history.db").exists()
    assert (tmp_path / "index.json").exists()


def test_migrate_index_to_sqlite_is_idempotent(tmp_path):
    index = [
        {
            "review_id": "review_old",
            "created_at": "2026-07-05T12:00:00",
            "mode": "single",
            "target": "code-snippet",
            "file_count": 1,
            "duration_ms": None,
            "model_name": "test-model",
            "markdown_path": "reports/review_old.md",
            "html_path": "reports/review_old.html",
            "summary": "old summary",
        }
    ]
    (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")

    first = migrate_index_to_sqlite(tmp_path)
    second = migrate_index_to_sqlite(tmp_path)

    assert first == (1, 0)
    assert second == (0, 1)
    assert list_reports(tmp_path)[0]["review_id"] == "review_old"
