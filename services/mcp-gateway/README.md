# mcp-gateway

The front door of the control plane. It is the only service you reach from your computer.

## What it does

- Gives one entry point for all services.
- Lists the services at `GET /mcp`.
- Forwards `/{service}/{path}` to the right internal service after cleaning the path strictly.
- Echoes and passes along `X-Request-ID` so you can follow a request through the logs.

## Settings

- `MCP_DIRECTORY` is a JSON map from service name to internal URL. Example:
  ```json
  {"mcp-lineage":"http://mcp-lineage:8000","mcp-policy":"http://mcp-policy:8000","mcp-audit":"http://mcp-audit:8000"}
  ```

## Endpoints

- `GET /mcp` returns `{ "services": [...], "directory": { ... } }`.
- `/{service}/{path}` is forwarded to an internal service. Example: `/mcp-policy/api/v1/policies/validate`.
- `GET /healthz` returns `{ "ok": true }`.

## Run it locally

```powershell
cd services/mcp-gateway
$env:MCP_DIRECTORY = '{"mcp-lineage":"http://localhost:8001","mcp-policy":"http://localhost:8002","mcp-audit":"http://localhost:8003"}'
uvicorn gateway_app:app --host 0.0.0.0 --port 8000 --reload
```

## Logging and security

- Passes `X-Request-ID` along and returns it in responses.
- Forwards only these headers: `accept`, `content-type`, and `x-request-id`.
- Does not follow redirects and ignores proxy environment variables.
- Adds security headers to every response.

## Troubleshooting

- Check the directory: `Invoke-RestMethod http://localhost:8080/mcp`
- Search the logs for a request ID: `docker compose logs -f mcp-gateway | Select-String <ID>`
