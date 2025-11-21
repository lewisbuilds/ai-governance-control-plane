"""
Minimal governance client using Python standard library only.
Usage:
    from clients.python.governance_client import GovernanceClient
    c = GovernanceClient()
    print(c.get_services())
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class GovernanceClient:
    def __init__(self, base_url: str = "http://localhost:8080", timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # Validate path to prevent URL injection: must start with / and not contain scheme markers
        if not path.startswith("/") or "://" in path:
            raise ValueError(f"Invalid path: {path}")
        url = f"{self.base_url}{path}"
        data_bytes = None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
            data_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(url=url, data=data_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            # return basic structured error
            try:
                raw = e.read().decode("utf-8")
                return {"status": e.code, "error": raw}
            except Exception:
                return {"status": e.code, "error": str(e)}

    def get_services(self) -> dict[str, Any]:
        return self._request("GET", "/mcp")

    def register_lineage(
        self,
        model_id: str,
        version: str,
        artifacts: dict[str, Any],
        created_by: str,
        metadata: dict[str, Any],
        aibom: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model_id": model_id,
            "version": version,
            "artifacts": artifacts,
            "created_by": created_by,
            "metadata": metadata,
        }
        if aibom is not None:
            payload["aibom"] = aibom
        return self._request("POST", "/mcp-lineage/register", payload)

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/mcp-policy/validate", {"payload": payload})

    def log_audit(
        self, event_type: str, subject: str, decision: bool, details: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {
            "event_type": event_type,
            "subject": subject,
            "decision": decision,
            "details": details,
        }
        return self._request("POST", "/mcp-audit/log", payload)
