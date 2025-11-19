import contextvars
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

RAW_DIRECTORY = os.environ.get("MCP_DIRECTORY", "{}")
try:
    MCP_DIRECTORY: dict[str, str] = json.loads(RAW_DIRECTORY)
except json.JSONDecodeError:
    MCP_DIRECTORY = {}

# Strictly allow only http URLs to known internal services
for k, v in list(MCP_DIRECTORY.items()):
    if not isinstance(v, str) or not v.startswith("http://"):
        MCP_DIRECTORY.pop(k, None)

# Map each service to a list of allowed path patterns (as regex).
# e.g., {"mcp-lineage": [r"^/artifacts/\w+$"], ...}
ALLOWED_PATHS: dict[str, list[str]] = {
    # Replace with actual service keys and the paths you wish to allow
    # "mcp-lineage": [r"^/artifacts/\w+$", r"^/status$"],
    # "mcp-audit": [r"^/events/\d+$"],
    # "mcp-policy": [r"^/validate$"],
}

app = FastAPI(title="mcp-gateway")

# ---- Structured logging with correlation IDs ----
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class _JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "service": self.service_name,
            "message": record.getMessage(),
            "request_id": _request_id_var.get(),
        }
        return json.dumps(payload, ensure_ascii=False)


_logger = logging.getLogger("app")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(_JsonFormatter("mcp-gateway"))
    _logger.addHandler(_h)


@app.middleware("http")
async def add_request_id(request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid4())
    token = _request_id_var.set(rid)
    t0 = time.perf_counter()
    _logger.info("request_start %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        dt = int((time.perf_counter() - t0) * 1000)
        _logger.info("request_end %s %s %sms", request.method, request.url.path, dt)
        _request_id_var.reset(token)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/mcp")
def mcp_directory():
    return {"services": sorted(MCP_DIRECTORY.keys()), "directory": MCP_DIRECTORY}


def _sanitize_path(path: str) -> str:
    # Disallow path traversal or scheme injection
    if ".." in path or path.startswith("http") or path.startswith("//"):
        raise HTTPException(status_code=400, detail="invalid_path")
    # ensure single leading slash
    if not path.startswith("/"):
        path = "/" + path
    return path


async def _proxy(service: str, path: str, req: Request):
    base = MCP_DIRECTORY.get(service)
    if not base:
        raise HTTPException(status_code=404, detail="service_not_found")
    spath = _sanitize_path(path)

    # SSRF Mitigation: check path against allowed patterns for service
    patterns = ALLOWED_PATHS.get(service)
    if patterns is None or not any(re.match(p, spath) for p in patterns):
        raise HTTPException(status_code=403, detail="unauthorized_path")

    # Build target URL and forward
    url = base.rstrip("/") + spath

    # Prepare request body
    body_bytes = await req.body()

    # Only forward a minimal, explicit set of safe headers. Drop auth/cookies and hop-by-hop headers.
    allowed = {"accept", "content-type", "x-request-id"}
    headers = {k: v for k, v in req.headers.items() if k.lower() in allowed}

    timeout = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, trust_env=False
    ) as client:
        resp = await client.request(
            req.method,
            url,
            content=body_bytes,
            headers=headers,
            params=dict(req.query_params),
        )
        # Return JSON if possible; do not forward upstream headers to avoid hop-by-hop/header conflicts
        try:
            data = resp.json()
            return JSONResponse(content=data, status_code=resp.status_code)
        except Exception:
            return JSONResponse(
                content={"status": resp.status_code, "body": resp.text},
                status_code=resp.status_code,
            )


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    return await _proxy(service, path, request)


# -------- High-level orchestration endpoints --------


def _service_url(key: str) -> str:
    base = MCP_DIRECTORY.get(key)
    if not base:
        raise HTTPException(status_code=503, detail=f"dependent_service_unavailable:{key}")
    return base.rstrip("/")


class ModelRegistration(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=100)
    created_by: str = Field(..., min_length=1, max_length=200)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    aibom: dict[str, Any] | None = None


class InferenceRequest(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=200)
    user_id: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] | None = None


@app.post("/api/v1/models/register")
async def register_model(reg: ModelRegistration):
    """Register a model (lineage) and create an audit log; optionally evaluate policies via AIBOM.

    - Calls mcp-lineage /register
    - Calls mcp-audit /log with decision=True (or policy result if later expanded)
    """
    lineage_url = f"{_service_url('mcp-lineage')}/register"
    audit_url = f"{_service_url('mcp-audit')}/log"

    timeout = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1) Record lineage
        lin_resp = await client.post(lineage_url, json=reg.model_dump())
        try:
            lin_resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="lineage_register_failed") from e
        lineage_record = lin_resp.json()

        # 2) Audit log
        audit_payload = {
            "event_type": "model_registration",
            "subject": reg.model_id,
            "decision": True,
            "details": {"lineage": lineage_record},
        }
        aud_resp = await client.post(audit_url, json=audit_payload)
        try:
            aud_resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="audit_log_failed") from e

    return {
        "status": "ok",
        "model_id": reg.model_id,
        "lineage": lineage_record,
        "audit": aud_resp.json(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/v1/models/infer")
async def infer(req: InferenceRequest):
    """Policy-gated inference placeholder.

    - Calls mcp-policy /validate with a payload derived from the request
    - If allowed, emits an audit event and returns a simulated response
    """
    policy_url = f"{_service_url('mcp-policy')}/validate"
    audit_url = f"{_service_url('mcp-audit')}/log"

    payload = {
        "model_id": req.model_id,
        "user_id": req.user_id,
        "prompt_len": len(req.prompt),
        "parameters": req.parameters,
    }
    if req.risk:
        payload["risk"] = req.risk

    timeout = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        pol_resp = await client.post(policy_url, json={"payload": payload})
        try:
            pol_resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="policy_validate_failed") from e
        policy = pol_resp.json()

        decision = bool(policy.get("allowed", False))

        # Always log audit
        audit_payload = {
            "event_type": "model_inference",
            "subject": req.model_id,
            "decision": decision,
            "details": {
                "user_id": req.user_id,
                "policy": policy,
                "prompt_len": len(req.prompt),
            },
        }
        _ = await client.post(audit_url, json=audit_payload)

    if not decision:
        raise HTTPException(status_code=403, detail={"policy": policy})

    # Simulated model response
    return {
        "model_id": req.model_id,
        "response": f"[simulated] echo:{req.prompt[:64]}",
        "policy": policy,
        "timestamp": datetime.utcnow().isoformat(),
    }
