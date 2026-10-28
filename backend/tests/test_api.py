import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import create_app
from app.schemas import Document


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    with TestClient(create_app()) as client:
        yield client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "service": "doculens-api", "phase": 4,
        "processing_available": all(__import__("importlib.util").util.find_spec(name) is not None for name in ("pypdf", "python_multipart")),
    }


def test_empty_document_contract(client):
    response = client.get("/api/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["mode"] == "persistent"
    assert body["processing_available"] is True
    assert "persisted records" in body["message"]


def test_no_upload_or_processing_endpoint(client):
    assert client.post("/api/documents").status_code == 405
    assert client.get("/api/documents/not-present").status_code == 404


def test_cors_allows_only_configured_origin(client):
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-credentials" not in allowed.headers
    denied = client.get("/api/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in denied.headers
    preflight = client.options("/api/documents", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "DELETE",
    })
    assert preflight.status_code == 400


@pytest.mark.parametrize("origin", ["*", "http://localhost:3000/path", "file://test", "https://user:pass@example.com"])
def test_invalid_cors_config_rejected(monkeypatch, origin):
    monkeypatch.setenv("CORS_ORIGINS", origin)
    with pytest.raises(ValueError):
        create_app()


def test_document_schema_rejects_negative_amount():
    with pytest.raises(ValidationError):
        Document(id="a", filename="a.pdf", type="Invoice",
                 uploaded_at="2026-10-28T10:00:00Z", status="Pending", total=-1)
