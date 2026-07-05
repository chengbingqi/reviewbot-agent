import review_directory


def test_collect_python_files_ignores_common_dirs(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("print('no')", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.py").write_text("print('no')", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.py").write_text("print('no')", encoding="utf-8")

    files = review_directory.collect_python_files(tmp_path)
    assert files == [{"path": "app/main.py", "content": "print('ok')"}]


def test_review_directory_local_does_not_request_backend(monkeypatch, tmp_path):
    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")

    def fail_post(*args, **kwargs):
        raise AssertionError("requests.post should not be called in local mode")

    class FakeGraph:
        def invoke(self, state):
            assert state["review_files"][0]["path"] == "main.py"
            return {"final_report": "# ReviewBot Report\n\nlocal"}

    monkeypatch.setattr(review_directory.requests, "post", fail_post)
    monkeypatch.setattr(review_directory, "agent_workflow", FakeGraph())

    report = review_directory.review_directory(str(tmp_path), local=True)
    assert "local" in report
