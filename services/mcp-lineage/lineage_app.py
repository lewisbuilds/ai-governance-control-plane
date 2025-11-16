import contextvars
import json
import logging
import os
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from lineage_schema import LineageIn, LineageRecord
from psycopg_pool import ConnectionPool

try:
    DATABASE_URL = os.environ["DATABASE_URL"]
except KeyError as exc:
    raise RuntimeError("DATABASE_URL environment variable is required") from exc

pool = ConnectionPool(conninfo=DATABASE_URL, max_size=10, open=True)

app = FastAPI(title="mcp-lineage")

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
    _h.setFormatter(_JsonFormatter("mcp-lineage"))
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


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/register", response_model=LineageRecord)
def register(lineage: LineageIn):
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_lineage (model_id, version, artifacts, created_by, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, model_id, version, artifacts, created_by, metadata, created_at
                """,
                (
                    lineage.model_id,
                    lineage.version,
                    lineage.artifacts,
                    lineage.created_by,
                    lineage.metadata,
                ),
            )
            row = cur.fetchone()
            return {
                "id": row[0],
                "model_id": row[1],
                "version": row[2],
                "artifacts": row[3],
                "created_by": row[4],
                "metadata": row[5],
                "created_at": row[6].isoformat(),
                "aibom": lineage.aibom,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail="registration_failed") from e


@app.get("/lineage/{model_id}", response_model=list[LineageRecord])
def get_lineage(model_id: str):
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, model_id, version, artifacts, created_by, metadata, created_at
                FROM model_lineage
                WHERE model_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (model_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "model_id": r[1],
                    "version": r[2],
                    "artifacts": r[3],
                    "created_by": r[4],
                    "metadata": r[5],
                    "created_at": r[6].isoformat(),
                }
                for r in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="query_failed") from e
