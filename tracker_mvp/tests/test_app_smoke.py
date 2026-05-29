import pytest


def test_health_endpoint_when_httpx_is_available(isolated_workspace):
    pytest.importorskip("httpx")

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
