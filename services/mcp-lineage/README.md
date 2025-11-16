# mcp-lineage

Model lineage and registration service.

## Purpose
- Registers model lineage events and metadata
- Retrieves lineage by `model_id`

## Environment
- `DATABASE_URL` (required), e.g. `postgresql://mcp:mcppass@db:5432/mcpgov`

## Endpoints
- `GET /healthz` → `{ "ok": true }`
- `POST /register` → register lineage
  - Body: `{ "model_id": "resnet-50", "version": "1.0.0", "artifacts": [], "created_by": "me@example.com", "metadata": {} }`
- `GET /lineage/{model_id}` → lineage records

## Run (dev)
```powershell
cd services/mcp-lineage
$env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"
uvicorn lineage_app:app --host 0.0.0.0 --port 8000 --reload
```

## Observability & security
- Echoes/propagates `X-Request-ID` via gateway
- Structured JSON logs with request IDs
- Security headers on all responses

## Troubleshooting
- Ensure DB reachable via `DATABASE_URL`
- Check that baseline schema and migrations are applied