import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]

PASSING = {
    "flags": {"contains_forbidden_data": False},
    "context": {"safety_critical": True},
    "metrics": {"accuracy": 0.97},
    "risk": {
        "data_sensitivity": 1,
        "model_complexity": 1,
        "deployment_impact": 1,
        "monitoring_maturity": 3,
    },
    "evidence": {"shap_report_path": "r.json", "lineage_hashes": ["sha256:x"]},
}


@pytest.fixture()
def policy(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "services" / "mcp-policy"))
    for name in ("policy_app", "validators"):
        sys.modules.pop(name, None)
    validators = importlib.import_module("validators")
    monkeypatch.setattr(validators, "POLICIES_DIR", str(REPO / "policies"))
    module = importlib.import_module("policy_app")
    module._MODELS.clear()
    return module


@pytest.fixture()
def client(policy):
    return TestClient(policy.app)


def test_health_routes(client):
    assert client.get("/healthz").json() == {"ok": True}
    assert client.get("/health").json() == {"ok": True}


def test_validate_allows_the_documented_example(client):
    body = client.post("/validate", json={"payload": PASSING}).json()
    assert body["allowed"] is True
    assert set(body) == {"allowed", "reasons", "notes", "risk_score", "within_sla", "elapsed_ms"}


def test_validate_denies_forbidden_data(client):
    flagged = {**PASSING, "flags": {"contains_forbidden_data": True}}
    body = client.post("/validate", json={"payload": flagged}).json()
    assert body["allowed"] is False
    assert any("forbidden" in reason.lower() for reason in body["reasons"])


def test_validate_denies_an_empty_payload(client):
    assert client.post("/validate", json={}).json()["allowed"] is False


def test_v1_alias_matches_validate(client):
    plain = client.post("/validate", json={"payload": PASSING}).json()
    alias = client.post("/api/v1/policies/validate", json={"payload": PASSING}).json()
    assert alias["allowed"] == plain["allowed"]
    assert alias["risk_score"] == plain["risk_score"]


def test_demo_model_registry_is_in_memory(client):
    assert client.get("/api/v1/policies/models").json() == {"models": []}

    resp = client.post("/api/v1/policies/register-model", json={"model_id": "m1", "tags": ["a"]})

    assert resp.json()["model"]["tags"] == ["a"]
    assert [m["model_id"] for m in client.get("/api/v1/policies/models").json()["models"]] == ["m1"]


def test_register_model_requires_an_id(client):
    assert client.post("/api/v1/policies/register-model", json={}).status_code == 422


def test_security_headers_and_request_id(client):
    resp = client.get("/healthz", headers={"X-Request-ID": "p-1"})
    assert resp.headers["X-Request-ID"] == "p-1"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
