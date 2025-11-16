import os

import pytest
import requests


def _env_url(name: str, default: str) -> str:
    return os.getenv(name, default).rstrip("/")


@pytest.fixture(scope="session")
def gateway_url() -> str:
    # Default aligns with docker-compose published port
    return _env_url("MCP_GATEWAY_URL", "http://localhost:8080")


def _get_or_skip(url: str, timeout: float = 3.0) -> requests.Response:
    try:
        resp = requests.get(url, timeout=timeout)
        return resp
    except (requests.ConnectionError, requests.Timeout) as exc:
        pytest.skip(f"Service not reachable at {url}: {exc!s}")
