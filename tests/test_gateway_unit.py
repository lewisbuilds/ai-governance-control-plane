import importlib
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

GATEWAY_DIR = Path(__file__).resolve().parents[1] / "services" / "mcp-gateway"

DIRECTORY = {
    "mcp-lineage": "http://lineage:8000",
    "mcp-policy": "http://policy:8000",
    "mcp-audit": "http://audit:8000",
}


class FakeAsyncClient:
    """Replaces httpx.AsyncClient and answers from a routing function."""

    calls: list[dict] = []
    responder = None

    def __init__(self, *args, **kwargs):
        self.options = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def request(self, method, url, content=None, headers=None, params=None):
        FakeAsyncClient.calls.append(
            {"method": method, "url": url, "headers": headers, "params": params, **self.options}
        )
        return FakeAsyncClient.responder(method, url, content)

    async def post(self, url, json=None):
        FakeAsyncClient.calls.append({"method": "POST", "url": url, "json": json})
        return FakeAsyncClient.responder("POST", url, json)


def _reply(status=200, body=None, content_type="application/json"):
    return httpx.Response(
        status,
        json=body if content_type == "application/json" else None,
        content=None if content_type == "application/json" else body,
        headers={"content-type": content_type},
        request=httpx.Request("GET", "http://x"),
    )


@pytest.fixture()
def gateway(monkeypatch):
    monkeypatch.syspath_prepend(str(GATEWAY_DIR))
    sys.modules.pop("gateway_app", None)
    module = importlib.import_module("gateway_app")
    monkeypatch.setattr(module, "MCP_DIRECTORY", dict(DIRECTORY))
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.calls = []
    FakeAsyncClient.responder = lambda m, u, c: _reply(body={"ok": True})
    return module


@pytest.fixture()
def client(gateway):
    return TestClient(gateway.app)


def test_directory_lists_services(client):
    body = client.get("/mcp").json()
    assert body["services"] == ["mcp-audit", "mcp-lineage", "mcp-policy"]


def test_healthz_and_security_headers(client):
    resp = client.get("/healthz", headers={"X-Request-ID": "r-1"})
    assert resp.json() == {"ok": True}
    assert resp.headers["X-Request-ID"] == "r-1"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_request_id_is_generated_when_missing(client):
    assert client.get("/healthz").headers["X-Request-ID"]


@pytest.mark.parametrize("path", ["../etc/passwd", "a/../b", "http://evil", "//evil"])
def test_sanitize_rejects_traversal_and_scheme_tricks(gateway, path):
    with pytest.raises(gateway.HTTPException) as err:
        gateway._sanitize_path(path)
    assert err.value.status_code == 400


def test_sanitize_adds_leading_slash(gateway):
    assert gateway._sanitize_path("healthz") == "/healthz"


def test_proxy_rejects_scheme_injection_in_path(client):
    assert client.get("/mcp-audit/http://evil.example").status_code == 400


def test_unknown_service_is_404(client):
    assert client.get("/mcp-evil/healthz").status_code == 404


def test_path_outside_allowlist_is_403(client):
    assert client.get("/mcp-audit/admin").status_code == 403
    assert client.get("/mcp-lineage/lineage/a/b").status_code == 403


def test_proxy_forwards_query_and_only_safe_headers(client):
    FakeAsyncClient.responder = lambda m, u, c: _reply(body=b"id,x\n1,2\n", content_type="text/csv")

    resp = client.get(
        "/mcp-audit/export?fmt=csv",
        headers={"Authorization": "secret", "Cookie": "a=b", "Accept": "text/csv"},
    )

    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://audit:8000/export"
    assert call["params"] == {"fmt": "csv"}
    assert call["follow_redirects"] is False and call["trust_env"] is False
    assert "authorization" not in {k.lower() for k in call["headers"]}
    assert "cookie" not in {k.lower() for k in call["headers"]}
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.text.startswith("id,x")


def test_proxy_passes_post_body_and_upstream_status(client):
    FakeAsyncClient.responder = lambda m, u, c: _reply(404, {"detail": "nope"})

    resp = client.post("/mcp-lineage/register", json={"model_id": "m"})

    assert resp.status_code == 404
    assert FakeAsyncClient.calls[0]["method"] == "POST"


def test_services_with_non_http_urls_are_ignored(monkeypatch):
    monkeypatch.setenv("MCP_DIRECTORY", '{"a":"http://a:1","b":"https://b:1","c":5}')
    monkeypatch.syspath_prepend(str(GATEWAY_DIR))
    sys.modules.pop("gateway_app", None)
    module = importlib.import_module("gateway_app")
    assert module.MCP_DIRECTORY == {"a": "http://a:1"}


def test_invalid_directory_json_gives_empty_directory(monkeypatch):
    monkeypatch.setenv("MCP_DIRECTORY", "not json")
    monkeypatch.syspath_prepend(str(GATEWAY_DIR))
    sys.modules.pop("gateway_app", None)
    assert importlib.import_module("gateway_app").MCP_DIRECTORY == {}


REGISTRATION = {"model_id": "m", "version": "1", "created_by": "me"}


def test_register_model_calls_lineage_then_audit(client):
    def respond(method, url, payload):
        if url.endswith("/register"):
            return _reply(body={"id": 1, "model_id": "m"})
        return _reply(body={"id": 9})

    FakeAsyncClient.responder = respond

    resp = client.post("/api/v1/models/register", json=REGISTRATION)

    assert resp.json()["status"] == "ok"
    urls = [c["url"] for c in FakeAsyncClient.calls]
    assert urls == ["http://lineage:8000/register", "http://audit:8000/log"]
    assert FakeAsyncClient.calls[1]["json"]["event_type"] == "model_registration"


def test_register_model_reports_lineage_failure(client):
    FakeAsyncClient.responder = lambda m, u, c: _reply(500, {"detail": "x"})
    resp = client.post("/api/v1/models/register", json=REGISTRATION)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "lineage_register_failed"
    assert len(FakeAsyncClient.calls) == 1


def test_register_model_reports_audit_failure(client):
    def respond(method, url, payload):
        if url.endswith("/register"):
            return _reply(body={"id": 1})
        return _reply(500, {"detail": "x"})

    FakeAsyncClient.responder = respond
    resp = client.post("/api/v1/models/register", json=REGISTRATION)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "audit_log_failed"


def test_register_model_needs_both_services(gateway, client, monkeypatch):
    monkeypatch.setattr(gateway, "MCP_DIRECTORY", {"mcp-lineage": "http://lineage:8000"})
    resp = client.post("/api/v1/models/register", json=REGISTRATION)
    assert resp.status_code == 503


INFER = {"model_id": "m", "user_id": "u", "prompt": "hello"}


def _policy(allowed: bool):
    def respond(method, url, payload):
        if url.endswith("/validate"):
            return _reply(body={"allowed": allowed, "reasons": []})
        return _reply(body={"id": 1})

    return respond


def test_inference_allowed_returns_simulated_response_and_audits(client):
    FakeAsyncClient.responder = _policy(True)

    resp = client.post("/api/v1/models/infer", json={**INFER, "risk": {"data_sensitivity": 1}})

    assert resp.status_code == 200
    assert resp.json()["response"].startswith("[simulated]")
    policy_call, audit_call = FakeAsyncClient.calls
    assert policy_call["json"]["payload"]["risk"] == {"data_sensitivity": 1}
    assert policy_call["json"]["payload"]["prompt_len"] == 5
    assert audit_call["json"]["decision"] is True


def test_inference_denied_is_403_but_still_audited(client):
    FakeAsyncClient.responder = _policy(False)

    resp = client.post("/api/v1/models/infer", json=INFER)

    assert resp.status_code == 403
    assert FakeAsyncClient.calls[-1]["json"]["decision"] is False


def test_inference_reports_policy_failure(client):
    FakeAsyncClient.responder = lambda m, u, c: _reply(500, {"detail": "x"})
    resp = client.post("/api/v1/models/infer", json=INFER)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "policy_validate_failed"
