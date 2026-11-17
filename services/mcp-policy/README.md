# mcp-policy

FastAPI REST service for YAML policy evaluation, risk scoring, optional AIBOM signature verification, and SLA timing.

## Configuration

- `POLICIES_DIR` defaults to `/app/policies`.
- `AIBOM_PUBLIC_KEY_PATH` defaults to `/app/keys/aibom_public_key.pem`.
- `AIBOM_REQUIRED` defaults to `false`.
- `GATE_SLA_MS` defaults to `1500`.

## Endpoints

- `GET /healthz` returns `{"ok": true}`.
- `POST /validate` evaluates a payload.
- `POST /api/v1/policies/validate` is an alias for `/validate`.
- `POST /api/v1/policies/register-model` and `GET /api/v1/policies/models` are in-memory demo endpoints.

A policy request must include all configured risk factors as numbers from 0 through 5, plus the fields required by `policies/model-policy.yml`. Missing or invalid risk values deny the request. The response contains the decision, reasons, notes, computed risk score, SLA status, and elapsed time.

When AIBOM data is supplied, send `digest` and base64 `signature_b64`; Ed25519 verification covers the exact UTF-8 digest string. Only the public key is mounted in the service.

## Local development

```powershell
cd services/mcp-policy
uvicorn policy_app:app --host 0.0.0.0 --port 8000 --reload
```

The policy and key directories are mounted read-only in Compose.
