import pytest
import requests


def _get_or_skip(url: str, timeout: float = 3.0) -> requests.Response:
    try:
        resp = requests.get(url, timeout=timeout)
        return resp
    except (requests.ConnectionError, requests.Timeout) as exc:
        pytest.skip(f"Service not reachable at {url}: {exc!s}")


@pytest.mark.integration
def test_gateway_health(gateway_url):
    # Gateway native health (if present)
    resp = _get_or_skip(f"{gateway_url}/healthz")
    assert resp.status_code in (200, 404)  # 404 acceptable if healthz not exposed directly
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict)
        assert any(k in data for k in ("ok", "status"))


@pytest.mark.integration
def test_proxied_policy_health(gateway_url):
    resp = _get_or_skip(f"{gateway_url}/mcp-policy/healthz")
    assert resp.status_code == 200
    assert resp.json().get("ok") is True


@pytest.mark.integration
def test_proxied_audit_health(gateway_url):
    resp = _get_or_skip(f"{gateway_url}/mcp-audit/healthz")
    assert resp.status_code == 200
    assert resp.json().get("ok") is True


@pytest.mark.integration
def test_proxied_lineage_health(gateway_url):
    resp = _get_or_skip(f"{gateway_url}/mcp-lineage/healthz")
    assert resp.status_code == 200
    assert resp.json().get("ok") is True
