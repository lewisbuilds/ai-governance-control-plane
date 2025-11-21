"""
Minimal governance client using Python standard library only.
Implements SSRF protections: allowlist validation and private IP rejection.

Usage:
    from clients.python.governance_client import GovernanceClient
    c = GovernanceClient()  # Uses default http://localhost:8080
    print(c.get_services())
"""

from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class GovernanceClient:
    # SSRF Mitigation: Allowlist of authorized governance endpoints.
    # Only these base URLs are permitted; prevents requests to arbitrary servers.
    AUTHORIZED_URLS: list[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://mcp-gateway:8000",  # Docker internal hostname
    ]

    def __init__(self, base_url: str = "http://localhost:8080", timeout: int = 10) -> None:
        # SSRF Mitigation: Validate base_url against allowlist and resolve IP to reject private addresses.
        validated_url = self._validate_base_url(base_url)
        self.base_url = validated_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _validate_base_url(base_url: str) -> str:
        """
        Validate base_url against allowlist and reject private/reserved IP addresses.
        Raises ValueError if URL is not authorized or resolves to private IP.
        """
        # Check against allowlist first (fastest check)
        normalized = base_url.rstrip("/")
        if normalized in GovernanceClient.AUTHORIZED_URLS:
            return normalized

        # If not in static allowlist, parse and validate hostname/IP
        try:
            parsed = urllib.parse.urlparse(base_url)
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
            if not parsed.netloc:
                raise ValueError(f"Invalid URL: missing hostname or IP")

            hostname = parsed.hostname
            if not hostname:
                raise ValueError(f"Invalid URL: could not extract hostname")

            # Try to resolve hostname to IP address and check if it's private
            try:
                resolved_ips = socket.getaddrinfo(hostname, None)
                for _family, _socktype, _proto, _canonname, sockaddr in resolved_ips:
                    ip_str = sockaddr[0]  # Extract IP from socket address
                    ip_obj = ipaddress.ip_address(ip_str)

                    # Reject private/loopback/reserved addresses EXCEPT localhost patterns
                    # (localhost is allowed by explicit allowlist above)
                    if ip_obj.is_private or ip_obj.is_reserved or ip_obj.is_loopback:
                        if hostname not in ("localhost", "127.0.0.1", "::1"):
                            raise ValueError(f"URL resolves to private/reserved IP: {ip_str}")
            except socket.gaierror as e:
                raise ValueError(f"Could not resolve hostname: {hostname}") from e

            raise ValueError(f"URL not in authorized allowlist: {base_url}")
        except urllib.error.URLError as e:
            raise ValueError(f"Invalid URL: {e}")

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Make HTTP request with SSRF protections:
        1. Validate path format (must start with /)
        2. Verify resolved IP before making request
        3. Reject private/reserved IPs
        """
        # Validate path to prevent URL injection: must start with / and not contain scheme markers
        if not path.startswith("/") or "://" in path:
            raise ValueError(f"Invalid path: {path}")

        url = f"{self.base_url}{path}"

        # Parse and verify IP before making request (defense-in-depth)
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                raise ValueError("Could not extract hostname from URL")

            # Verify the resolved IP is not private/reserved
            resolved_ips = socket.getaddrinfo(hostname, None)
            for _family, _socktype, _proto, _canonname, sockaddr in resolved_ips:
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_private or ip_obj.is_reserved or ip_obj.is_loopback:
                    if hostname not in ("localhost", "127.0.0.1", "::1", "mcp-gateway"):
                        raise ValueError(
                            f"Request blocked: hostname resolves to private IP {ip_str}"
                        )
        except socket.gaierror as e:
            raise ValueError(f"Could not resolve hostname for request: {e}") from e

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
