import json

from api_server import health, sse_event, stream_agent_execution


def test_health_returns_ok():
    assert health() == {"status": "ok"}


def test_sse_event_shape():
    raw = sse_event("node_end", "done", node="planner", data={"x": 1})
    assert raw.startswith("data: ")
    payload = json.loads(raw.removeprefix("data: ").strip())
    assert payload["event"] == "node_end"
    assert payload["node"] == "planner"
    assert payload["data"] == {"x": 1}


def test_empty_code_returns_error_without_llm():
    chunks = list(stream_agent_execution("   "))
    assert any('"event": "error"' in chunk for chunk in chunks)
    assert any('"empty_code"' in chunk for chunk in chunks)
