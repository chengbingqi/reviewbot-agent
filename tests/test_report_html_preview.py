import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api_server
from report_exporter import create_report_metadata, export_report


def test_report_html_preview_returns_html(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metadata = create_report_metadata(review_id="review_html_ok")
    export_report("# Example\n\n- pass", output_dir=tmp_path, metadata=metadata)
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)

    client = TestClient(api_server.app)
    response = client.get("/reports/review_html_ok/html")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ReviewBot Report" in response.text


def test_report_html_preview_returns_404_for_missing_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)

    client = TestClient(api_server.app)
    response = client.get("/reports/missing/html")

    assert response.status_code == 404


def test_report_html_preview_rejects_path_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside.html"
    outside.write_text("<html>outside</html>", encoding="utf-8")
    index = [
        {
            "review_id": "bad_path",
            "created_at": "2026-07-05T12:00:00",
            "mode": "single",
            "target": "code-snippet",
            "file_count": 1,
            "markdown_path": str(tmp_path / "bad_path.md"),
            "html_path": str(outside),
            "summary": "bad path",
        }
    ]
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)

    client = TestClient(api_server.app)
    response = client.get("/reports/bad_path/html")

    assert response.status_code == 400
