# mcp-audit

Append-only audit logging service with hash chaining.

## Purpose
- Accepts audit events and writes to `audit_log` with chained `prev_hash` → `entry_hash`
- Prevents UPDATE/DELETE via triggers (append-only)

## Environment
- `DATABASE_URL` (required), e.g. `postgresql://mcp:mcppass@db:5432/mcpgov`

## Endpoints
- `GET /healthz` → `{ "ok": true }`
- `POST /log` → `{ "event_type": "policy_decision", "subject": "resnet-50@1.0.0", "decision": true, "details": {} }`
- `GET /events?limit=100&offset=0`
- `GET /export?fmt=json|csv`

## Run (dev)
```powershell
cd services/mcp-audit
$env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"
uvicorn audit_app:app --host 0.0.0.0 --port 8000 --reload
```

## Observability & security
- Echoes/propagates `X-Request-ID` via gateway
- Structured JSON logs with request IDs
- Security headers on all responses

## Troubleshooting
- Ensure DB reachable via `DATABASE_URL`
- If triggers fail, confirm schema applied (see `infra/init.sql` and migration runner)
