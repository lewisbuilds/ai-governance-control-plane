# mcp-gateway

Reverse proxy and entrypoint for the AI Governance Control Plane.

## Purpose
- Exposes a consolidated facade for all services
- Service directory at `GET /mcp`
- Reverse-proxy routing `/{service}/{path}` to internal services with strict path sanitization
- Correlation support via `X-Request-ID` (echoed and propagated)

## Environment
- `MCP_DIRECTORY` (JSON map): service name → internal URL, e.g.
  ```json
  {"mcp-lineage":"http://mcp-lineage:8000","mcp-policy":"http://mcp-policy:8000","mcp-audit":"http://mcp-audit:8000"}
  ```

## Endpoints
- `GET /mcp` → `{ "services": [...], "directory": { ... } }`
- `/{service}/{path}` → proxied to internal service (e.g., `/mcp-policy/api/v1/policies/validate`)
- `GET /healthz` → `{ "ok": true }`

## Run (dev)
```powershell
cd services/mcp-gateway
$env:MCP_DIRECTORY = '{"mcp-lineage":"http://localhost:8001","mcp-policy":"http://localhost:8002","mcp-audit":"http://localhost:8003"}'
uvicorn gateway_app:app --host 0.0.0.0 --port 8000 --reload
```

## Observability & security
- Propagates `X-Request-ID` and echoes it in responses
- Restricts forwarded headers (accept, content-type, x-request-id)
- Does not follow redirects; ignores proxy env vars
- Adds standard security headers on all responses

## Troubleshooting
- Verify directory: `Invoke-RestMethod http://localhost:8080/mcp`
- Check logs for the request ID: `docker compose logs -f mcp-gateway | Select-String <ID>`
