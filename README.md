# AI Governance Control Plane

A small demo you can run on your own machine. It tracks where AI models came from, checks them against policy rules, and keeps a tamper evident audit log of every decision. It uses FastAPI, PostgreSQL, and Docker Compose. No Kubernetes is needed.

> **Note on the name:** the services are called `mcp-lineage`, `mcp-policy`, `mcp-audit`, and `mcp-gateway`. They use plain REST and JSON. They do not implement the Model Context Protocol. The `mcp` prefix is only a name.

## What it does

- **Lineage:** records each model version and its artifacts. Records are only ever added, never changed.
- **Policy:** checks a model against rules written in YAML and calculates a weighted risk score.
- **AIBOM check:** can verify an Ed25519 signature using a public key. This is optional.
- **Audit log:** every event stores the hash of the one before it, so edits can be detected. You can export the log as JSON or CSV.
- **Gateway:** the only service exposed to your computer. It allows only known services and paths, adds request IDs, and limits how long it waits for other services.
- **Safer containers:** application containers are read only and run as a normal user. Compose health checks confirm each service is ready.

## Quick start

You need Docker with Compose v2.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Open .env and change POSTGRES_PASSWORD. Use the same password inside DATABASE_URL.
docker compose up -d --build
```

Wait until the gateway answers:

```powershell
for ($i = 0; $i -lt 60; $i++) {
  try {
    Invoke-RestMethod http://localhost:8080/mcp -TimeoutSec 3 | ConvertTo-Json -Depth 5
    break
  } catch {
    Start-Sleep -Seconds 2
  }
}
docker compose ps
```

Only the gateway is reachable from your computer, on port `8080`. The database and the other services stay inside Docker.

## Try it

Check that every service is healthy:

```powershell
Invoke-RestMethod http://localhost:8080/mcp
Invoke-RestMethod http://localhost:8080/mcp-lineage/healthz
Invoke-RestMethod http://localhost:8080/mcp-policy/healthz
Invoke-RestMethod http://localhost:8080/mcp-audit/healthz
```

Register a model:

```powershell
$lineage = Get-Content .\examples\register_model.json -Raw
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8080/mcp-lineage/register `
  -ContentType application/json -Body $lineage
```

Check a model against `policies/model-policy.yml`. This example includes every field the policy asks for, so it should be allowed:

```powershell
$decision = @{
  payload = @{
    flags = @{ contains_forbidden_data = $false }
    context = @{ safety_critical = $true }
    metrics = @{ accuracy = 0.97 }
    risk = @{
      data_sensitivity = 1
      model_complexity = 1
      deployment_impact = 1
      monitoring_maturity = 3
    }
    evidence = @{
      shap_report_path = "reports/demo-shap.json"
      lineage_hashes = @("sha256:example")
    }
  }
} | ConvertTo-Json -Depth 8

$result = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8080/mcp-policy/validate `
  -ContentType application/json -Body $decision
$result | ConvertTo-Json -Depth 8
```

Save the decision in the audit log, then read the log back:

```powershell
$audit = @{
  event_type = "policy_decision"
  subject = "resnet-50@1.0.0"
  decision = $result.allowed
  details = $result
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-audit/log `
  -ContentType application/json -Body $audit
Invoke-RestMethod "http://localhost:8080/mcp-audit/export?fmt=json"
```

For a longer walkthrough, see [examples/demo_notebook.md](examples/demo_notebook.md).

## Run the tests

Use Python 3.11. Create a virtual environment and install the tools:

```powershell
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -m "not integration"
```

The integration tests need the Compose stack to be running:

```powershell
python -m pytest -m integration --cov-fail-under=0
```

Test coverage is reported but not enforced yet, so it is not a quality gate.

Useful Docker commands:

- `docker compose ps` shows service status.
- `docker compose logs -f` follows the logs.
- `docker compose down` stops everything and keeps your database data. Back up the database before you delete the volume.

## Configuration

- `policies/model-policy.yml` holds the required checks, deny rules, conditional checks, and notes.
- `policies/risk-matrix.yml` holds the weights for the risk score. Each of the four risk factors must be a number from 0 to 5. A missing or invalid value denies the request.
- `.env` holds the values Compose uses. `.env.example` is only for local use. Always change its sample password.
- AIBOM checking is off by default. To turn it on, set `AIBOM_REQUIRED=true` and mount an Ed25519 public key at `AIBOM_PUBLIC_KEY_PATH`. The request supplies `aibom.digest` and a base64 `aibom.signature_b64`. The signature covers the exact digest text. The private key never enters this system.
- `scripts/pg-backup.ps1` and `scripts/pg-restore.ps1` back up and restore PostgreSQL. Test a restore before you rely on it.
- `scripts/migrate.py` applies database changes. It records a checksum for each migration after it runs.

## Limits you should know about

This is a demo and a learning project. It is not ready for production. It has no login, permissions, rate limiting, separation between customers, or TLS. Keep it on a trusted local network until those are added. The sample password in `.env.example` is not safe for a real deployment. Read [SECURITY.md](SECURITY.md) before you expose any endpoint.

- Audit rows are protected by database triggers and hash links. Someone with full database access can still change the data or the schema. The log shows tampering. It does not prevent it.
- Policy decisions trust the metrics and lineage evidence the caller sends. The service does not retrain a model or recalculate its metrics.
- `GATE_SLA_MS` adds a warning when a check is slow. It does not stop the check or reject the result.
- The gateway only forwards paths on its allowlist. When you add an endpoint, add it to the allowlist too.

## More reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains how the pieces fit together.
- [docs/API.md](docs/API.md) lists every endpoint.
- [docs/README-Quickstart.md](docs/README-Quickstart.md) has extra setup help, such as proxy settings.
- [docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) helps you present the project.
