import pytest

import api_server
from report_exporter import create_report_metadata, export_report, load_report_index


def test_export_report_updates_index_and_caps_history(tmp_path):
    for index in range(105):
        export_report(
            f"# Report {index}",
            output_dir=tmp_path,
            metadata=create_report_metadata(review_id=f"review_{index:03d}"),
        )

    records = load_report_index(tmp_path)
    assert len(records) == 100
    assert records[0]["review_id"] == "review_104"


def test_reports_endpoints_return_index_and_markdown(monkeypatch, tmp_path):
    exported = export_report(
        "# Example",
        output_dir=tmp_path,
        metadata=create_report_metadata(review_id="review_test"),
    )
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)

    records = api_server.list_reports()
    assert records[0]["review_id"] == "review_test"
    detail = api_server.get_report("review_test")
    assert "ReviewBot Report" in detail["markdown"]
    assert detail["html_path"] == str(exported.html_path)


def test_get_report_missing_raises_404(monkeypatch, tmp_path):
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)
    with pytest.raises(api_server.HTTPException) as exc:
        api_server.get_report("missing")
    assert exc.value.status_code == 404
