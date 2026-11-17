import csv
import io
import json
from datetime import datetime
from hashlib import sha256

import pytest
from fakes import FakeCursor, FakePool, load_service
from fastapi.testclient import TestClient


@pytest.fixture()
def audit(monkeypatch):
    module = load_service("audit_app", "mcp-audit", monkeypatch)
    FakePool.fail = False
    FakePool.cursor = FakeCursor()
    yield module
    FakePool.fail = False


def _row(i: int, prev: str, entry: str):
    return (i, "policy_decision", "m@1", True, {"a": 1}, prev, entry, datetime(2026, 1, 1))


BODY = {"event_type": "policy_decision", "subject": "m@1", "decision": True, "details": {"a": 1}}


def test_first_event_chains_from_genesis(audit):
    expected = sha256(("GENESIS|" + audit.canonical_json(BODY)).encode()).hexdigest()
    FakePool.cursor = FakeCursor(one=[None, _row(1, "GENESIS", expected)])

    resp = TestClient(audit.app).post("/log", json=BODY)

    assert resp.status_code == 200
    assert resp.json()["prev_hash"] == "GENESIS"
    insert_params = FakePool.cursor.executed[-1][1]
    assert insert_params[-2:] == ("GENESIS", expected)


def test_next_event_uses_previous_entry_hash(audit):
    expected = sha256(("abc123|" + audit.canonical_json(BODY)).encode()).hexdigest()
    FakePool.cursor = FakeCursor(one=[("abc123",), _row(2, "abc123", expected)])

    resp = TestClient(audit.app).post("/log", json=BODY)

    assert resp.json()["entry_hash"] == expected
    assert FakePool.cursor.executed[-1][1][-2] == "abc123"


def test_canonical_json_ignores_key_order(audit):
    assert audit.canonical_json({"b": 1, "a": 2}) == audit.canonical_json({"a": 2, "b": 1})


def test_log_rejects_invalid_body(audit):
    resp = TestClient(audit.app).post("/log", json={"event_type": ""})
    assert resp.status_code == 422


def test_log_returns_generic_error_when_database_fails(audit):
    FakePool.fail = True
    resp = TestClient(audit.app, raise_server_exceptions=False).post("/log", json=BODY)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "audit_failed"


def test_events_lists_rows_and_validates_paging(audit):
    FakePool.cursor = FakeCursor(many=[[_row(2, "h1", "h2"), _row(1, "GENESIS", "h1")]])
    client = TestClient(audit.app)

    resp = client.get("/events?limit=2&offset=0")

    assert [e["id"] for e in resp.json()] == [2, 1]
    assert FakePool.cursor.executed[-1][1] == (2, 0)
    assert client.get("/events?limit=0").status_code == 422
    assert client.get("/events?limit=1001").status_code == 422


def test_events_hides_database_errors(audit):
    FakePool.fail = True
    resp = TestClient(audit.app, raise_server_exceptions=False).get("/events")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "list_failed"


def test_export_json_and_csv(audit):
    rows = [_row(1, "GENESIS", "h1"), _row(2, "h1", "h2")]
    client = TestClient(audit.app)

    FakePool.cursor = FakeCursor(many=[rows])
    as_json = client.get("/export?fmt=json")
    assert as_json.headers["content-type"].startswith("application/json")
    assert [e["entry_hash"] for e in json.loads(as_json.text)] == ["h1", "h2"]

    FakePool.cursor = FakeCursor(many=[rows])
    as_csv = client.get("/export?fmt=csv")
    assert as_csv.headers["content-type"].startswith("text/csv")
    parsed = list(csv.DictReader(io.StringIO(as_csv.text)))
    assert parsed[1]["prev_hash"] == parsed[0]["entry_hash"]


def test_export_rejects_unknown_format(audit):
    assert TestClient(audit.app).get("/export?fmt=xml").status_code == 422


def test_export_hides_database_errors(audit):
    FakePool.fail = True
    resp = TestClient(audit.app, raise_server_exceptions=False).get("/export")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "export_failed"


def test_responses_carry_security_headers_and_request_id(audit):
    resp = TestClient(audit.app).get("/healthz", headers={"X-Request-ID": "req-1"})
    assert resp.json() == {"ok": True}
    assert resp.headers["X-Request-ID"] == "req-1"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
