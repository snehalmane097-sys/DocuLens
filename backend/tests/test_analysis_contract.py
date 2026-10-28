"""Handler/schema unit tests that need no asyncio loop or socket access."""
import sys
import pytest
from fastapi import HTTPException
from app.main import create_app


def test_analysis_openapi_contract():
    schema = create_app().openapi()
    body = schema["paths"]["/api/documents/analyze"]["post"]["requestBody"]
    assert body["content"]["multipart/form-data"]["schema"]["properties"]["file"]["format"] == "binary"
    assert schema["paths"]["/api/documents/analyze"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("InvoiceAnalysis")


def test_missing_dependencies_returns_clear_503(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.pdf_analysis", None)
    route = next(r for r in create_app().routes if r.path == "/api/documents/analyze")
    coroutine = route.endpoint(None)
    try:
        # Missing dependency branch raises before its first await; no event loop needed.
        with pytest.raises(HTTPException) as error:
            coroutine.send(None)
        assert error.value.status_code == 503
        assert "dependencies" in error.value.detail
    finally:
        coroutine.close()


def test_existing_health_and_list_handlers_still_work():
    app = create_app()
    health = next(r for r in app.routes if r.path == "/api/health").endpoint()
    documents = next(r for r in app.routes if r.path == "/api/documents").endpoint(offset=0,limit=100)
    assert health.status == "ok"
    assert health.phase == 4
    assert documents.items == []
    assert documents.total == 0


def test_uvicorn_export_has_exactly_one_analysis_route():
    from app.main import app
    routes = [route for route in app.routes
              if route.path == "/api/documents/analyze" and "POST" in route.methods]
    assert len(routes) == 1
