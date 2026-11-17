# Quickstart

This guide gets the stack running and walks through each service once. For a shorter version, see the [README](../README.md).

## What you get

A FastAPI and PostgreSQL stack, run with Docker Compose, that provides:

- A lineage registry for models. Records are only added, never changed.
- Policy checks with YAML rules and an optional AIBOM signature check. The signature check uses an Ed25519 public key only.
- An audit log where each event is linked to the one before it. You can export the log.
- A gateway that forwards requests to the internal services and lists them in a directory.

Security defaults: containers run as a normal user with a read only filesystem, `no-new-privileges` is on, all extra Linux capabilities are dropped, SQL is parameterized, the gateway guards against SSRF and path traversal, and responses carry standard security headers.

Key folders:

- `services/` holds `mcp-lineage`, `mcp-audit`, `mcp-policy`, and `mcp-gateway`.
- `infra/init.sql` creates the database tables `model_lineage` and `audit_log`.
- `policies/` holds the YAML policy files you can edit.
- `clients/python/` holds a small Python client.
- `docs/` holds the architecture and API docs.

## 1. Set up

Copy the sample settings, then change the password:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Start Docker Desktop with Linux containers, then run this from the repository root:

```powershell
docker compose up -d --build

for ($i = 0; $i -lt 60; $i++) {
  try { Invoke-RestMethod http://localhost:8080/mcp -TimeoutSec 5 | ConvertTo-Json -Depth 5; break }
  catch { Start-Sleep -Seconds 2 }
}
```

Compose waits for each service's health check before it starts the services that depend on it. Health endpoints:

- `mcp-gateway`: `/healthz` and `/mcp`
- `mcp-policy`, `mcp-audit`, and `mcp-lineage`: `/healthz`

## 2. Register a model

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-lineage/register `
  -ContentType application/json -Body (Get-Content .\examples\register_model.json -Raw)
```

## 3. Check a model against the policy

The policy needs `flags`, `metrics`, and `context` fields as well as `risk`. If any are missing, the request is denied.

```powershell
$payload = @{ payload = @{
  flags = @{ contains_forbidden_data = $false }
  context = @{ safety_critical = $true }
  metrics = @{ accuracy = 0.97 }
  risk = @{ data_sensitivity = 1; model_complexity = 1; deployment_impact = 1; monitoring_maturity = 3 }
  evidence = @{ shap_report_path = "reports/demo-shap.json"; lineage_hashes = @("sha256:example") }
} }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-policy/validate `
  -ContentType application/json -Body ($payload | ConvertTo-Json -Depth 8)
```

## 4. Record an audit event

```powershell
$audit = @{ event_type = "policy_decision"; subject = "demo@1.0.0"; decision = $true; details = @{ note = "smoke test" } }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-audit/log `
  -ContentType application/json -Body ($audit | ConvertTo-Json -Depth 8)
```

## Follow one request through the logs

Send your own request ID, then search the logs for it:

```powershell
$rid = [guid]::NewGuid().ToString()
Invoke-RestMethod http://localhost:8080/mcp-policy/healthz -Headers @{ "X-Request-ID" = $rid }
docker compose logs mcp-gateway mcp-policy | Select-String $rid
```

On Linux or macOS:

```sh
RID=$(uuidgen); curl -H "X-Request-ID: $RID" http://localhost:8080/mcp-policy/healthz
docker compose logs mcp-gateway mcp-policy | grep "$RID"
```

## Building behind a proxy or a PyPI mirror

If Docker builds cannot reach PyPI, set these optional variables. Compose passes them to the builds.

```powershell
$env:PIP_INDEX_URL = "https://your-internal-pypi/simple"
$env:PIP_TRUSTED_HOST = "your-internal-pypi"
$env:HTTP_PROXY = "http://proxy.corp:8080"
$env:HTTPS_PROXY = "http://proxy.corp:8080"
$env:NO_PROXY = "localhost,127.0.0.1,.local"
docker compose build
```

## Endpoints at a glance

- `mcp-lineage`: `POST /register`, `GET /lineage/{model_id}`, `GET /healthz`
- `mcp-policy`: `POST /validate`, `GET /healthz`
- `mcp-audit`: `POST /log`, `GET /events`, `GET /export?fmt=json` or `fmt=csv`, `GET /healthz`
- `mcp-gateway`: `GET /mcp`, and forwarding for `/{service}/{path}` on the allowlist

See [API.md](API.md) for full details.

## Settings

`.env.example` provides these:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `DATABASE_URL`
- `AIBOM_PUBLIC_KEY_PATH` and `AIBOM_REQUIRED`. AIBOM checking is optional by default.
- `GATE_SLA_MS`, the time budget for a policy decision

To use AIBOM checking, put the Ed25519 public key at `infra/keys/aibom_public_key.pem`.

## Security summary

- **Containers:** normal user, read only filesystem, temporary storage for caches, `no-new-privileges`, and all capabilities dropped.
- **Gateway:** routes only to an allowlist (`MCP_DIRECTORY`). Its path cleaner blocks `..`, `//`, and scheme tricks. Internal URLs are plain HTTP.
- **Apps:** parameterized SQL, safe YAML loading, and security headers (CSP, NoSniff, HSTS, X Frame Options).
- **Errors:** clients get generic codes. Details stay in the logs.

## Automated smoke test

The GitHub Actions workflow `.github/workflows/governance-gate.yml` builds the stack and waits for it to be healthy. It then runs a policy check and writes an audit event. It prints the logs if anything fails.

## Examples

The `examples/` folder has a sample lineage file. [demo_notebook.md](../examples/demo_notebook.md) is a scripted walkthrough.

## Ideas for next steps

- Keep builds repeatable by pinning `requirements.txt` and keeping the `wheelhouse/` for offline installs.
- Scan dependencies for vulnerabilities in CI with pip-audit or Trivy.
- Use `requirements.txt` and the wheelhouse everywhere. Poetry is not needed.
