# mcp-policy

A FastAPI service that checks models against YAML policy rules. It also calculates a risk score, can verify an AIBOM signature, and measures how long each check takes.

## Settings

- `POLICIES_DIR` defaults to `/app/policies`.
- `AIBOM_PUBLIC_KEY_PATH` defaults to `/app/keys/aibom_public_key.pem`.
- `AIBOM_REQUIRED` defaults to `false`.
- `GATE_SLA_MS` defaults to `1500`.

## Endpoints

- `GET /healthz` returns `{"ok": true}`.
- `POST /validate` checks a payload.
- `POST /api/v1/policies/validate` does the same thing as `/validate`.
- `POST /api/v1/policies/register-model` and `GET /api/v1/policies/models` are demo endpoints that keep data in memory only.

## How a request is judged

A request must include every configured risk factor as a number from 0 to 5. It must also include the fields that `policies/model-policy.yml` requires. A missing or invalid risk value denies the request.

The response contains the decision, the reasons, notes, the risk score, whether the check was within the SLA, and the time taken.

## AIBOM signatures

If you send AIBOM data, include a `digest` and a base64 `signature_b64`. The Ed25519 signature must cover the exact digest text. Only the public key is mounted in the service.

## Run it locally

```powershell
cd services/mcp-policy
uvicorn policy_app:app --host 0.0.0.0 --port 8000 --reload
```

Compose mounts the policy and key folders as read only.
