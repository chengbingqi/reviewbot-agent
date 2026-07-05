import pytest
from fastapi.testclient import TestClient

import api_server
from config import get_config


@pytest.fixture(autouse=True)
def reset_runtime_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("AUTH_TOKEN", "change_me")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "20")
    get_config.cache_clear()
    api_server._rate_limit_hits.clear()
    yield
    get_config.cache_clear()
    api_server._rate_limit_hits.clear()


def test_auth_disabled_allows_reports(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)
    client = TestClient(api_server.app)

    response = client.get("/reports")

    assert response.status_code == 200
    assert response.json() == []


def test_auth_enabled_requires_token(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_TOKEN", "test-token")
    get_config.cache_clear()
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)
    client = TestClient(api_server.app)

    response = client.get("/reports")

    assert response.status_code == 401


def test_auth_enabled_accepts_bearer_token(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_TOKEN", "test-token")
    get_config.cache_clear()
    monkeypatch.setattr(api_server, "REPORTS_DIR", tmp_path)
    client = TestClient(api_server.app)

    response = client.get("/reports", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json() == []


def test_rate_limit_disabled_does_not_block_review():
    client = TestClient(api_server.app)

    response = client.post("/review", json={"code": "   "})

    assert response.status_code == 200


def test_rate_limit_enabled_returns_429(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    get_config.cache_clear()
    client = TestClient(api_server.app)

    first = client.post("/review", json={"code": "   "})
    second = client.post("/review", json={"code": "   "})

    assert first.status_code == 200
    assert second.status_code == 429
