# mcp-policy

Policy evaluation service.

## Purpose
- Evaluates inputs against YAML policies and a risk matrix
- Optional AIBOM (Ed25519) public-key verification
- SLA timing with `GATE_SLA_MS`

## Environment
- `POLICIES_DIR` (default `/app/policies`)
- `AIBOM_PUBLIC_KEY_PATH` (default `/app/keys/aibom_public_key.pem`)
- `AIBOM_REQUIRED` (default `false`)
- `GATE_SLA_MS` (default `1500`)

## Endpoints
- `GET /healthz` → `{ "ok": true }`
- `POST /validate` → legacy
- `POST /api/v1/policies/validate` → preferred
  - Body: `{ "payload": { "model_class": "vision", "use_case": "general", "risk": {"data_sensitivity": 1} } }`
- `POST /api/v1/policies/register-model` → demo-only (ephemeral)
- `GET /api/v1/policies/models`

## Run (dev)
```powershell
cd services/mcp-policy
uvicorn policy_app:app --host 0.0.0.0 --port 8000 --reload
```

## Observability & security
- Echoes/propagates `X-Request-ID` via gateway
- Structured JSON logs with elapsed time and request IDs
- Security headers on all responses

## Troubleshooting
- Validate file permissions for `POLICIES_DIR`
- If AIBOM is required and missing/invalid, responses will include an explanatory reason