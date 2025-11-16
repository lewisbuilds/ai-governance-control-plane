## AI Governance Control Plane

FastAPI + Postgres + Docker Compose stack that provides:
## AI Governance Control Plane

FastAPI + Postgres + Docker Compose stack that provides:
- Model lineage registry (append-only records)
- Policy validation with YAML rules and optional AIBOM verification (Ed25519 public key only)
- Append-only audit log with hash chaining and export
- A gateway that safely proxies requests to internal services and exposes a service directory

Security and ops defaults: non-root containers, read-only filesystems, tmpfs for caches, no-new-privileges, cap_drop: [ALL], parameterized SQL, SSRF/path traversal guards, and standard security headers.

Key directories:
- `services/` — mcp-lineage, mcp-audit, mcp-policy, mcp-gateway
- `infra/init.sql` — DB schema (model_lineage, audit_log)
- `policies/` — customer-editable YAML policies
- `clients/python/` — minimal Python client
- `docs/` — architecture and API docs

## Quickstart

1) Configure environment (optional — defaults exist in `.env.example`).

  Optionally add an explicit request ID to correlate logs across services:

  - PowerShell

  ```powershell
  $rid = [guid]::NewGuid().ToString()
  Invoke-RestMethod http://localhost:8080/mcp-policy/healthz -Headers @{ "X-Request-ID" = $rid }
  docker compose logs -f mcp-gateway mcp-policy | Select-String $rid
  ```

  - curl

  ```sh
  RID=$(uuidgen); curl -H "X-Request-ID: $RID" http://localhost:8080/mcp-policy/healthz; \
  docker compose logs -f mcp-gateway mcp-policy | grep "$RID"
  ```

2) Start Docker Desktop (Linux containers), then from the repo root:

```powershell
# Build and start
docker compose build
docker compose up -d

# Wait for gateway health
for ($i=0; $i -lt 60; $i++) {
  try { $r = Invoke-RestMethod http://localhost:8080/mcp -TimeoutSec 5; if ($r) { $r | ConvertTo-Json -Depth 5; break } }
  catch {}
  Start-Sleep -Seconds 2
}
```

3) Register a lineage record:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-lineage/register -ContentType application/json -Body (Get-Content .\examples\register_model.json -Raw)
```
3. Health endpoints

  - `mcp-gateway`: `/healthz`, `/mcp`
  - `mcp-policy`: `/healthz`
  - `mcp-audit`: `/healthz`
  - `mcp-lineage`: `/healthz`

  Compose healthchecks wait for these endpoints before starting dependents.


4) Validate a policy input:

```powershell
$payload = @{ payload = @{ model_class = "vision"; use_case = "general"; risk = @{ data_sensitivity = 1; model_complexity = 1; deployment_impact = 1; monitoring_maturity = 3 } } }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-policy/validate -ContentType application/json -Body ($payload | ConvertTo-Json -Depth 8)
```

5) Log an audit event:

```powershell
$audit = @{ event_type = "policy_decision"; subject = "demo@1.0.0"; decision = $true; details = @{ note = "smoke" } }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-audit/log -ContentType application/json -Body ($audit | ConvertTo-Json -Depth 8)
```

### Building behind a corporate proxy or with a PyPI mirror

If Docker builds fail to reach PyPI (files.pythonhosted.org), set these optional variables and compose will pass them to the builds:

```powershell
# Optional: internal PyPI mirror
$env:PIP_INDEX_URL = "https://your-internal-pypi/simple"
$env:PIP_TRUSTED_HOST = "your-internal-pypi"

# Optional: corporate HTTP(S) proxy (and NO_PROXY for local addresses)
$env:HTTP_PROXY = "http://proxy.corp:8080"
$env:HTTPS_PROXY = "http://proxy.corp:8080"
$env:NO_PROXY = "localhost,127.0.0.1,.local"

# Then build
docker compose build
```

## Services & Endpoints

- mcp-lineage: `POST /register`, `GET /lineage/{model_id}`, `GET /healthz`
- mcp-policy: `POST /validate`, `GET /healthz`
- mcp-audit: `POST /log`, `GET /events`, `GET /export?fmt=json|csv`, `GET /healthz`
- mcp-gateway: `GET /mcp`, proxy `/{service}/{path}` (safe allow-list only)

See `docs/API.md` for request/response details and examples.

## Configuration

- `.env.example` provides defaults:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `DATABASE_URL`
  - `AIBOM_PUBLIC_KEY_PATH`, `AIBOM_REQUIRED` (AIBOM optional by default)
  - `GATE_SLA_MS` (policy decision SLA window)
- Place the AIBOM Ed25519 public key at `infra/keys/aibom_public_key.pem` when using AIBOM verification.

## Security Posture

- Containers: non-root, read-only rootfs, tmpfs for caches, no-new-privileges, cap_drop: [ALL]
- Gateway: allow-list routing (`MCP_DIRECTORY`), path sanitizer (blocks `..`, `//`, scheme injection), http-only internal URLs
- Apps: parameterized SQL, YAML safe loading, security headers (CSP/NoSniff/HSTS/XFO)
- Errors: generic codes to clients, details retained only in logs

## CI Smoke Test

GitHub Actions workflow `.github/workflows/governance-gate.yml` builds the stack, waits for health, performs a policy validation and audit log write, and prints logs on failure.

## Examples

See `examples/` for a lineage JSON and a scripted walkthrough in `demo_notebook.md`.

## Next Enhancements

- Enforce reproducible builds by pinning `requirements.txt` and maintaining the `wheelhouse/` for offline installs
- Add dependency vulnerability scanning (pip-audit/Trivy) in CI
- Standardize entirely on `requirements.txt` + wheelhouse; no Poetry required
