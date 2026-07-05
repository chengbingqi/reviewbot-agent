from report_exporter import export_report


def test_export_report_writes_markdown_and_html(tmp_path):
    exported = export_report("# Title\n\nBody", output_dir=tmp_path, prefix="test")
    assert exported.markdown_path.exists()
    assert exported.html_path.exists()
    assert exported.markdown_path.read_text(encoding="utf-8").startswith("# ReviewBot Report")
    assert "ReviewBot Report" in exported.html_path.read_text(encoding="utf-8")
