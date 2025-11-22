# AGENTS.md

Agent-focused guide for working on the AI Governance Control Plane. This complements the human-focused README and docs by collecting concrete, reliable commands and conventions that coding agents can execute directly.

## Project overview

- Purpose: Governance control plane for AI/ML workloads
  - Lineage registry (append-only)
  - Policy evaluation (YAML-driven rules, optional AIBOM/Ed25519 verification)
  - Audit log (append-only, hash chained)
  - Gateway proxy + orchestration of the above services
- Architecture: 4 FastAPI microservices + PostgreSQL, orchestrated via Docker Compose
  - Services: `mcp-gateway`, `mcp-policy`, `mcp-audit`, `mcp-lineage`
  - Internal service ports: 8000, Gateway exposed at 8080
  - DB schema lives in `infra/init.sql`
- Languages/Frameworks: Python 3.11, FastAPI, Pydantic v2, httpx, psycopg3
- Tests: pytest (static YAML/SQL checks + optional integration via running services)

## Setup commands (Windows PowerShell)

Prerequisites
- Docker Desktop (Linux engine)
- Python 3.11 (optional for local dev/test without Docker)

Clone and prepare env
```powershell
# From repository root
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Optional: corporate proxy or PyPI mirror for Docker builds (compose passes these through)
```powershell
# If required in your network, set any that apply:
# $env:PIP_INDEX_URL = "https://your-internal-pypi/simple"
# $env:PIP_TRUSTED_HOST = "your-internal-pypi"
# $env:HTTP_PROXY = "http://proxy.corp:8080"
# $env:HTTPS_PROXY = "http://proxy.corp:8080"
# $env:NO_PROXY = "localhost,127.0.0.1,.local"
```

Build and run with Docker Compose
```powershell
# Start Docker Desktop if needed, then:
docker compose build
docker compose up -d
```

## Development workflow

Run a single service locally (without Docker)
```powershell
# Example: mcp-policy
cd services/mcp-policy
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# If the service touches DB (policy does not write DB; audit/lineage do), set DATABASE_URL
# $env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"

uvicorn policy_app:app --host 0.0.0.0 --port 8000 --reload
```

Repo-level testing
```powershell
# From repo root
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements-dev.txt
pytest
```

## Testing instructions

- Run all tests (host):
```powershell
pytest
```

- Integration tests expect running services. Either:
  - Start the stack via Docker Compose (recommended), or
  - Run the gateway and dependent services locally

- Focus or skip markers:
```powershell
# Run only non-integration tests (fast, offline)
pytest -m "not integration"

# Run a specific test module or test
pytest tests\test_health.py -q
```

## Smoke testing via gateway (PowerShell)

After `docker compose up -d` and services are healthy:
```powershell
# Health endpoints through the gateway
Invoke-RestMethod http://localhost:8080/mcp-policy/healthz
Invoke-RestMethod http://localhost:8080/mcp-lineage/healthz
Invoke-RestMethod http://localhost:8080/mcp-audit/healthz
Invoke-RestMethod http://localhost:8080/mcp-gateway/healthz

# Policy validate (preferred v1 path)
$payload = @{ payload = @{ model_class = "vision"; use_case = "general"; risk = @{ data_sensitivity = 1 } } }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-policy/api/v1/policies/validate -ContentType application/json -Body ($payload | ConvertTo-Json -Depth 8)

# Demo-only: register and list models in policy (ephemeral memory store)
$model = @{ model_id = "resnet-50"; name = "ResNet 50"; tags = @("vision"); metadata = @{ framework = "pytorch" } }
Invoke-RestMethod -Method Post -Uri http://localhost:8080/mcp-policy/api/v1/policies/register-model -ContentType application/json -Body ($model | ConvertTo-Json -Depth 8)
Invoke-RestMethod http://localhost:8080/mcp-policy/api/v1/policies/models
```

## Observability: structured logs and correlation IDs

All services emit structured JSON logs to stdout and propagate the `X-Request-ID` header. If you supply an `X-Request-ID`, the gateway and downstream service will log the same ID and the gateway will echo it back in the response headers.

Verify propagation and logs (Windows PowerShell):

```powershell
# 1) Send a request with a custom correlation ID
$rid = [guid]::NewGuid().ToString()
$headers = @{ 'X-Request-ID' = $rid }
$resp = Invoke-WebRequest -Uri http://localhost:8080/mcp-policy/healthz -Headers $headers

# 2) Confirm the response echoes the same ID
$resp.Headers['X-Request-ID']

# 3) Inspect gateway and service logs for the same ID
docker compose logs -f mcp-gateway | Select-String $rid
docker compose logs -f mcp-policy  | Select-String $rid

# Tip: Use Ctrl+C to stop following logs once verified.
```

Notes
- If you omit `X-Request-ID`, the services will generate one and return it in the response headers from the gateway.
- Logs are JSON lines; use your preferred tooling to parse/pretty-print if needed.

## Security hardening additions

- Container runtime protections are enabled in `docker-compose.yml` for app services: non-root user, read-only root filesystem, tmpfs for writable paths, `no-new-privileges`, `cap_drop: [ALL]`, and conservative `pids_limit`/`ulimits`.
- Optional AIBOM verification is supported by `mcp-policy`. See `docs/SECURITY-AIBOM.md` and enable via `AIBOM_REQUIRED=true` with a mounted Ed25519 public key at `infra/keys/aibom_public_key.pem`.
- For Kubernetes deployments, baseline NetworkPolicies are provided under `infra/k8s/network-policies/` (default deny, intra-namespace allow, Postgres ingress only from labeled app pods). Adapt labels to your manifests.

## Code style guidelines

- Python 3.11 with FastAPI; follow idiomatic FastAPI patterns (pydantic models for inputs/outputs)
- Security-first:
  - Parameterized SQL only (psycopg3), never string-concatenated queries
  - Do not accept external URLs without strict allow-lists (avoid SSRF)
  - Keep gateway path sanitization intact; avoid adding un-sanitized proxy routes
  - Maintain security headers middleware across services
- Config via environment variables (see `.env.example`); do not hardcode secrets
- No enforced linters committed; if you add one (e.g., ruff/black), document the commands here and in CI

## Schema migrations (repeatable path)

- Baseline lives in `infra/init.sql` and is treated as version `0000_init`.
- Incremental migrations live in `infra/migrations/*.sql` and are applied in lexicographic order. See `infra/migrations/README.md`.
- A lightweight runner (`scripts/migrate.py`) tracks applied versions and checksums in `schema_migrations`.

Run via Docker Compose (automatic):

```powershell
docker compose up -d db db-migrate
```

Run manually (host):

```powershell
$env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"
python .\scripts\migrate.py
```

Notes
- On an empty DB, the runner executes `infra/init.sql` and records the baseline.
- On an existing DB (e.g., when Postgres bootstraps from `init.sql`), the runner records the baseline without reapplying it.

## Backup and restore (tested regularly)

Use the provided PowerShell scripts against the running `mcp-db` container:

```powershell
# Set required env vars for credentials (match your compose/.env)
$env:POSTGRES_USER = "mcp"
$env:POSTGRES_PASSWORD = "mcppass"
$env:POSTGRES_DB = "mcpgov"

# Create a compressed custom-format dump
./scripts/pg-backup.ps1 -Output .\backups\latest.dump

# Restore into a target database (created if missing)
./scripts/pg-restore.ps1 -InputDump .\backups\latest.dump -TargetDb "restoretest"
```

CI coverage
- Workflow `.github/workflows/pg-backup-restore-test.yml` runs weekly and on-demand, performing a dump and restore round-trip to validate procedures.

## Build and deployment

- Docker images are built per service; Dockerfiles install from `requirements.txt`
- Network-restricted environments:
  - Use PIP_INDEX_URL/PIP_TRUSTED_HOST and/or HTTP(S)_PROXY/NO_PROXY as shown above
  - Offline fallback: pre-download wheels on the host and adjust Dockerfiles to install with `--no-index --find-links=/app/wheelhouse`
- Compose brings up Postgres and services; database schema is defined in `infra/init.sql` (compose or scripts may apply it)
- Gateway is exposed at `http://localhost:8080` by default

## Security considerations

- AIBOM verification is optional by default; enable by providing an Ed25519 public key at `infra/keys/aibom_public_key.pem` and set `AIBOM_REQUIRED=true`
- Key env vars (see `.env.example`):
  - `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `AIBOM_PUBLIC_KEY_PATH`, `AIBOM_REQUIRED`
  - `GATE_SLA_MS`
- Keep policy YAMLs (`policies/`) under source control; treat YAML parsing with `yaml.safe_load`

## Pull request guidelines

- Keep PRs small and focused; update `docs/API.md` when you add or change endpoints
- Always run tests locally before PR:
```powershell
pytest -m "not integration"
```
- For integration changes, run the stack and execute the smoke tests in this document
- If you change Infra/Compose:
  - Confirm `docker compose build` and `docker compose up -d` succeed on a clean machine
  - Document any new env vars in `.env.example` and here

## Debugging & troubleshooting

- Docker daemon not reachable (Windows): start Docker Desktop and retry `docker version`
- Pip cannot reach PyPI during build:
  - Set a PyPI mirror and/or corporate proxy env vars
  - As a last resort, vendor wheels and install with `--no-index`
- Services unhealthy:
  - Check container logs: `docker compose logs -f <service>`
  - Verify DB connectivity via `DATABASE_URL`
  - Ensure policy YAMLs parse and paths are correct

## Repository layout quick reference

```
ai-governance-control-plane/
  clients/python/                 # Minimal Python client
  collections/                    # Collections metadata
  docs/                           # API and architecture docs
  examples/                       # Demo payloads and walkthrough
  infra/                          # Database schema and keys
  policies/                       # YAML policies (rules and risk matrix)
  services/
    mcp-audit/
    mcp-gateway/
    mcp-lineage/
    mcp-policy/
  tests/                          # pytest suite (YAML/SQL checks + health tests)
```

## Agent tips

- Use the gateway for end-to-end flows; prefer `/api/v1/...` where available
- Keep the gateway’s allow-list and path sanitizer intact when adding routes
- When adding policy rules, adjust both `policies/model-policy.yml` and `policies/risk-matrix.yml` and update tests if logic changes
- When adding DB fields, update `infra/init.sql` and any service using that table; add a test to validate schema assumptions
- For new microservices, follow existing patterns: security headers, health endpoints, uvicorn entrypoint, Dockerfile with non-root user
