import json

from fastapi.testclient import TestClient

import api_server


def _payloads(chunks):
    payloads = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                payloads.append(json.loads(line[6:]))
    return payloads


def test_review_files_empty_list_returns_controlled_error():
    client = TestClient(api_server.app)
    response = client.post("/review-files", json={"files": []})
    assert response.status_code == 200
    payloads = _payloads([response.text])
    assert payloads[0]["event"] == "error"
    assert payloads[0]["node"] == "request"


def test_review_files_stream_contains_file_path_events(monkeypatch):
    class FakeWorkflow:
        def stream(self, state):
            yield {
                "summary": {
                    "errors": [],
                    "timings": {"summary": 0.1},
                    "final_report": "ok",
                    "rag_results": [],
                    "tool_results": {
                        "ruff": {"status": "pass"},
                        "bandit": {"status": "pass"},
                    },
                }
            }

    monkeypatch.setattr(api_server, "agent_workflow", FakeWorkflow())
    chunks = list(
        api_server.stream_review_files(
            "# File: app/main.py\nprint('ok')",
            [{"path": "app/main.py", "content": "print('ok')"}],
        )
    )
    payloads = _payloads(chunks)
    assert all({"event", "node", "message", "data", "error"} <= set(payload) for payload in payloads)
    assert any(payload["event"] == "file_start" for payload in payloads)
    assert any(payload.get("data", {}).get("file_path") == "app/main.py" for payload in payloads)
    assert any(payload["event"] == "review_complete" for payload in payloads)
