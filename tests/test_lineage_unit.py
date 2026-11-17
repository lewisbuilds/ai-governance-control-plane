from datetime import datetime

import pytest
from fakes import FakeCursor, FakePool, load_service
from fastapi.testclient import TestClient

BODY = {
    "model_id": "resnet-50",
    "version": "1.0.0",
    "artifacts": ["sha256:abc"],
    "created_by": "me@example.com",
    "metadata": {"framework": "pytorch"},
}


@pytest.fixture()
def lineage(monkeypatch):
    module = load_service("lineage_app", "mcp-lineage", monkeypatch)
    FakePool.fail = False
    FakePool.cursor = FakeCursor()
    yield module
    FakePool.fail = False


def _row(i: int, version: str):
    return (i, "resnet-50", version, ["sha256:abc"], "me@example.com", {}, datetime(2026, 1, 1))


def test_register_inserts_with_bound_parameters(lineage):
    FakePool.cursor = FakeCursor(one=[_row(7, "1.0.0")])

    resp = TestClient(lineage.app).post("/register", json=BODY)

    assert resp.status_code == 200
    assert resp.json()["id"] == 7
    sql, params = FakePool.cursor.executed[0]
    assert "%s" in sql and "resnet-50" not in sql
    assert params[0] == "resnet-50"


def test_register_echoes_aibom_when_supplied(lineage):
    FakePool.cursor = FakeCursor(one=[_row(1, "1.0.0")])
    aibom = {"digest": "sha256:x", "signature_b64": "sig"}

    resp = TestClient(lineage.app).post("/register", json={**BODY, "aibom": aibom})

    assert resp.json()["aibom"] == aibom


def test_register_rejects_missing_fields(lineage):
    resp = TestClient(lineage.app).post("/register", json={"model_id": "x"})
    assert resp.status_code == 422


def test_register_hides_database_errors(lineage):
    FakePool.fail = True
    resp = TestClient(lineage.app, raise_server_exceptions=False).post("/register", json=BODY)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "registration_failed"


def test_register_fails_when_insert_returns_nothing(lineage):
    resp = TestClient(lineage.app, raise_server_exceptions=False).post("/register", json=BODY)
    assert resp.status_code == 500


def test_lookup_returns_versions_for_one_model(lineage):
    FakePool.cursor = FakeCursor(many=[[_row(2, "1.1.0"), _row(1, "1.0.0")]])

    resp = TestClient(lineage.app).get("/lineage/resnet-50")

    assert [r["version"] for r in resp.json()] == ["1.1.0", "1.0.0"]
    assert FakePool.cursor.executed[0][1] == ("resnet-50",)


def test_lookup_of_unknown_model_is_empty(lineage):
    assert TestClient(lineage.app).get("/lineage/none").json() == []


def test_lookup_hides_database_errors(lineage):
    FakePool.fail = True
    resp = TestClient(lineage.app, raise_server_exceptions=False).get("/lineage/x")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "query_failed"


def test_security_headers_and_request_id(lineage):
    resp = TestClient(lineage.app).get("/healthz", headers={"X-Request-ID": "abc"})
    assert resp.headers["X-Request-ID"] == "abc"
    assert resp.headers["Content-Security-Policy"] == "default-src 'none'"
