import contextvars
import csv
import io
import json
import logging
import os
import time
from hashlib import sha256
from uuid import uuid4

from audit_schema import AuditEvent, AuditIn
from fastapi import FastAPI, HTTPException, Query, Response
from psycopg import types as psycopg_types
from psycopg_pool import ConnectionPool

try:
    DATABASE_URL = os.environ["DATABASE_URL"]
except KeyError as exc:
    raise RuntimeError("DATABASE_URL environment variable is required") from exc
pool = ConnectionPool(conninfo=DATABASE_URL, max_size=10, open=True)

app = FastAPI(title="mcp-audit")

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
    _h.setFormatter(_JsonFormatter("mcp-audit"))
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


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@app.post("/log", response_model=AuditEvent)
def log_event(evt: AuditIn):
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            prev_hash = row[0] if row else "GENESIS"

            payload_str = canonical_json(
                {
                    "event_type": evt.event_type,
                    "subject": evt.subject,
                    "decision": evt.decision,
                    "details": evt.details,
                }
            )
            entry_hash = sha256((prev_hash + "|" + payload_str).encode("utf-8")).hexdigest()

            cur.execute(
                """
                INSERT INTO audit_log (event_type, subject, decision, details, prev_hash, entry_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, event_type, subject, decision, details, prev_hash, entry_hash, created_at
                """,
                (
                    evt.event_type,
                    evt.subject,
                    evt.decision,
                    psycopg_types.json.Json(evt.details),
                    prev_hash,
                    entry_hash,
                ),
            )
            r = cur.fetchone()
            return {
                "id": r[0],
                "event_type": r[1],
                "subject": r[2],
                "decision": r[3],
                "details": r[4],
                "prev_hash": r[5],
                "entry_hash": r[6],
                "created_at": r[7].isoformat(),
            }
    except Exception as e:
        _logger.error("log_event failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="audit_failed") from e


@app.get("/events", response_model=list[AuditEvent])
def events(limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0)):
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, event_type, subject, decision, details, prev_hash, entry_hash, created_at
                FROM audit_log
                ORDER BY id DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "event_type": r[1],
                    "subject": r[2],
                    "decision": r[3],
                    "details": r[4],
                    "prev_hash": r[5],
                    "entry_hash": r[6],
                    "created_at": r[7].isoformat(),
                }
                for r in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="list_failed") from e


@app.get("/export")
def export(fmt: str = Query(default="json", pattern="^(json|csv)$")):
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_type, subject, decision, details, prev_hash, entry_hash, created_at FROM audit_log ORDER BY id ASC"
            )
            rows = cur.fetchall()
            data = [
                {
                    "id": r[0],
                    "event_type": r[1],
                    "subject": r[2],
                    "decision": r[3],
                    "details": r[4],
                    "prev_hash": r[5],
                    "entry_hash": r[6],
                    "created_at": r[7].isoformat(),
                }
                for r in rows
            ]
        if fmt == "json":
            return Response(content=json.dumps(data), media_type="application/json")
        else:
            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=[
                    "id",
                    "event_type",
                    "subject",
                    "decision",
                    "details",
                    "prev_hash",
                    "entry_hash",
                    "created_at",
                ],
            )
            writer.writeheader()
            for row in data:
                row = {**row, "details": canonical_json(row["details"])}
                writer.writerow(row)
            return Response(content=buf.getvalue(), media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail="export_failed") from e
