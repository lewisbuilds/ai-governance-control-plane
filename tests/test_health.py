import pytest
import requests


def _get_or_skip(url: str, timeout: float = 3.0) -> requests.Response:
    try:
        resp = requests.get(url, timeout=timeout)
        return resp
    except (requests.ConnectionError, requests.Timeout) as exc:
        pytest.skip(f"Service not reachable at {url}: {exc!s}")


@pytest.mark.integration
def test_gateway_health(gateway_url: str) -> None:
    # Gateway native health (if present)
    resp = _get_or_skip(f"{gateway_url}/healthz")
    assert resp.status_code in (200, 404)  # 404 acceptable if healthz not exposed directly
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict)
        assert any(k in data for k in ("ok", "status"))


@pytest.mark.integration
def test_proxied_policy_health(gateway_url: str) -> None:
    resp = _get_or_skip(f"{gateway_url}/mcp-policy/healthz")
    assert resp.status_code == 200
    assert resp.json().get("ok") is True


@pytest.mark.integration
def test_proxied_audit_health(gateway_url: str) -> None:
    resp = _get_or_skip(f"{gateway_url}/mcp-audit/healthz")
    assert resp.status_code == 200
    assert resp.json().get("ok") is True


@pytest.mark.integration
def test_proxied_lineage_health(gateway_url: str) -> None:
    resp = _get_or_skip(f"{gateway_url}/mcp-lineage/healthz")
    assert resp.status_code == 200
    assert resp.json().get("ok") is True


@pytest.mark.integration
def test_audit_entry_creation(gateway_url: str) -> None:
    """Test that audit entries are created with proper structure."""
    resp = requests.post(
        f"{gateway_url}/mcp-audit/log",
        json={
            "event_type": "test_event",
            "subject": "test-subject",
            "decision": True,
            "details": {"test_key": "test_value"},
        },
        timeout=3.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("event_type") == "test_event"
    assert data.get("subject") == "test-subject"
    assert data.get("decision") is True
    assert data.get("details") == {"test_key": "test_value"}
    assert "id" in data
    assert "entry_hash" in data
    assert "prev_hash" in data


@pytest.mark.integration
def test_audit_hash_chaining(gateway_url: str) -> None:
    """Test that consecutive audit entries form a hash chain."""
    # Create first entry in this test
    resp1 = requests.post(
        f"{gateway_url}/mcp-audit/log",
        json={
            "event_type": "chain_test_1",
            "subject": "chain-subject",
            "decision": True,
            "details": {"step": 1},
        },
        timeout=3.0,
    )
    assert resp1.status_code == 200
    entry1 = resp1.json()
    hash1 = entry1.get("entry_hash")
    prev_hash_1 = entry1.get("prev_hash")

    # Verify structure (prev_hash may be GENESIS or a previous entry's hash)
    assert prev_hash_1 is not None, "First entry should have prev_hash"

    # Create second entry
    resp2 = requests.post(
        f"{gateway_url}/mcp-audit/log",
        json={
            "event_type": "chain_test_2",
            "subject": "chain-subject",
            "decision": True,
            "details": {"step": 2},
        },
        timeout=3.0,
    )
    assert resp2.status_code == 200
    entry2 = resp2.json()

    # Verify hash chain: entry2.prev_hash must equal entry1.entry_hash
    assert entry2.get("prev_hash") == hash1, "Second entry's prev_hash should link to first entry"
    assert entry2.get("entry_hash") != hash1, "Entry hashes must be unique"


@pytest.mark.integration
def test_policy_validation_success(gateway_url: str) -> None:
    """Test successful policy validation."""
    resp = requests.post(
        f"{gateway_url}/mcp-policy/api/v1/policies/validate",
        json={
            "payload": {
                "model_class": "vision",
                "use_case": "general",
                "region": "global",
                "risk": {
                    "data_sensitivity": 1,
                    "model_complexity": 1,
                    "deployment_impact": 1,
                    "monitoring_maturity": 3,
                },
            }
        },
        timeout=3.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "allowed" in data
    assert "risk_score" in data
    assert "reasons" in data


@pytest.mark.integration
def test_lineage_registration(gateway_url: str) -> None:
    """Test model lineage registration."""
    resp = requests.post(
        f"{gateway_url}/mcp-lineage/register",
        json={
            "model_id": f"test-model-{int(__import__('time').time())}",
            "version": "1.0.0",
            "created_by": "test-user",
            "artifacts": ["artifact1", "artifact2"],
            "metadata": {"framework": "pytorch", "created_at": "2025-01-01"},
        },
        timeout=3.0,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "model_id" in data
    assert data.get("version") == "1.0.0"
    assert data.get("created_by") == "test-user"
