# Architecture

This repo provides a Compose-first AI Governance Control Plane with four services and a PostgreSQL database.

## Components

- Postgres 16 (db)
  - Schemas in `infra/init.sql` for `model_lineage` and `audit_log` with append-only constraints
- mcp-lineage (FastAPI)
  - Registers and fetches lineage records; uses psycopg3 + pool
  - Endpoints: POST /register, GET /lineage/{model_id}, GET /healthz
- mcp-audit (FastAPI)
  - Append-only audit log with hash chaining; export JSON/CSV
  - Endpoints: POST /log, GET /events, GET /export, GET /healthz
- mcp-policy (FastAPI)
  - Loads customer policy YAMLs; optional AIBOM (Ed25519 public key only); risk scoring with `policies/risk-matrix.yml`
  - Endpoints: POST /validate, GET /healthz
- mcp-gateway (FastAPI)
  - Directory of internal services and a safe reverse proxy
  - Endpoints: GET /mcp, generic proxy /{service}/{path}

## Security

- Containers run as a non-root user with `read_only: true`, tmpfs work dirs, `no-new-privileges`, and `cap_drop: [ALL]`
- SSRF/Traversal protections in gateway: allow-list based (`MCP_DIRECTORY`), path sanitization, and scheme checks
- Standard security headers set by middleware on all services (CSP, HSTS when https, X-Frame-Options, etc.)
- No plaintext secrets in repo; env-driven configuration via `.env.example`
- DB interactions use parameterized queries to avoid SQL injection

## Data Flow

1. Client POSTs lineage ⇒ `mcp-lineage` ⇒ Postgres
2. Client POSTs policy input ⇒ `mcp-policy` ⇒ evaluates YAML rules + risk scoring ⇒ decision
3. Client POSTs audit ⇒ `mcp-audit` ⇒ appends hash-chained event
4. Optional integration via `mcp-gateway`: route `/mcp-lineage/*`, `/mcp-policy/*`, `/mcp-audit/*`

## Operations

- Docker Compose orchestrates services; healthchecks expose readiness
- Policies mounted read-only from `./policies`
- AIBOM public key (optional) mounted from `./infra/keys`
- Makefile targets: `up`, `down`, `logs`, `test`
