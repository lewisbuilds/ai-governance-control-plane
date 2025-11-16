import contextvars
import json
import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field
from validators import evaluate

app = FastAPI(title="mcp-policy")

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class _JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": __import__("datetime").datetime.utcnow().isoformat() + "Z",
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
    _h.setFormatter(_JsonFormatter("mcp-policy"))
    _logger.addHandler(_h)


@app.middleware("http")
async def add_request_id(request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid4())
    token = _request_id_var.set(rid)
    t0 = time.perf_counter()
    _logger.info(f"request_start {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        dt = int((time.perf_counter() - t0) * 1000)
        _logger.info(f"request_end {request.method} {request.url.path} {dt}ms")
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


class ValidateIn(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class ModelRegistration(BaseModel):
    model_id: str = Field(..., description="Unique model identifier")
    name: str | None = Field(None, description="Human-friendly name")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


_MODELS: dict[str, dict[str, Any]] = {}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/validate")
def validate(inp: ValidateIn):
    res = evaluate(inp.payload)
    return {
        "allowed": res.allowed,
        "reasons": res.reasons,
        "risk_score": res.risk_score,
        "within_sla": res.within_sla,
        "elapsed_ms": res.elapsed_ms,
    }


@app.post("/api/v1/policies/validate")
def validate_v1(inp: ValidateIn):
    return validate(inp)


@app.post("/api/v1/policies/register-model")
def register_model_v1(reg: ModelRegistration):
    _MODELS[reg.model_id] = {
        "model_id": reg.model_id,
        "name": reg.name,
        "tags": reg.tags or [],
        "metadata": reg.metadata or {},
    }
    return {"ok": True, "model": _MODELS[reg.model_id]}


@app.get("/api/v1/policies/models")
def list_models_v1():
    return {"models": list(_MODELS.values())}
