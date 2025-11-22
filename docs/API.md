# API

All services are FastAPI applications listening on port 8000 internally. When accessed through the gateway, prefix the path with the service name (e.g., `/mcp-policy/api/v1/policies/validate`).

## Common

- `GET /healthz` ⇒ `{ "ok": true }`
- Security headers are applied on all responses

### Headers and observability

- `X-Request-ID` request header is propagated by the gateway to downstream services and echoed back in responses. If omitted, a request ID is generated and returned.
- All services emit structured JSON logs including the request ID and timing information.

## mcp-lineage

- `POST /register` ⇒ Register lineage
  - Body:
    ```json
    {
      "model_id": "resnet-50",
      "version": "1.0.0",
      "artifacts": {"weights": "..."},
      "created_by": "email@example.com",
      "metadata": {"framework": "pytorch"},
      "aibom": {"data": {...}, "signature": "<hex>"} // optional
    }
    ```
  - Response: record with created_at
- `GET /lineage/{model_id}` ⇒ [record]

## mcp-audit

- `POST /log` ⇒ Append audit event (hash-chained)
  - Body:
    ```json
    {"event_type": "policy_decision", "subject": "resnet-50@1.0.0", "decision": true, "details": {}}
    ```
- `GET /events?limit=100&offset=0` ⇒ [event]
- `GET /export?fmt=json|csv` ⇒ export all

## mcp-policy

- `GET /healthz` ⇒ Health
- `POST /validate` ⇒ Evaluate policy (legacy path; retained for compatibility)
- `POST /api/v1/policies/validate` ⇒ Evaluate policy (preferred)
  - Body:
    ```json
    {"payload": {"model_class": "vision", "use_case": "general", "risk": {"data_sensitivity": 1}}}
    ```
  - Response:
    ```json
    {"allowed": true, "reasons": ["..."], "risk_score": 3.0, "within_sla": true, "elapsed_ms": 42}
    ```
- `POST /api/v1/policies/register-model` ⇒ Ephemeral model registration (demo)
  - Body:
    ```json
    {"model_id": "resnet-50", "name": "ResNet 50", "tags": ["vision"], "metadata": {"framework": "pytorch"}}
    ```
  - Response: `{ "ok": true, "model": { ... } }`
- `GET /api/v1/policies/models` ⇒ List registered models (ephemeral)

## mcp-gateway

- `GET /mcp` ⇒ { services: [..], directory: { service: url } }
- `/{service}/{path}` ⇒ reverse-proxy to internal service; path is sanitized and restricted

Notes
- The gateway only forwards a minimal header allow-list (e.g., `accept`, `content-type`, `x-request-id`).
- The gateway does not follow redirects and does not trust proxy environment variables.

### High-level endpoints (orchestration)

- `POST /api/v1/models/register` ⇒ Register a model via lineage and create an audit entry
  - Body:
    ```json
    {
      "model_id": "resnet-50",
      "version": "1.0.0",
      "artifacts": ["s3://bucket/resnet50.pt"],
      "created_by": "email@example.com",
      "metadata": {"framework": "pytorch"},
      "aibom": {"data": {"sbom": {}}, "signature": "<hex>"}
    }
    ```
  - Response:
    ```json
    {"status": "ok", "model_id": "resnet-50", "lineage": {"...": "..."}, "audit": {"...": "..."}}
    ```

- `POST /api/v1/models/infer` ⇒ Policy-gated inference placeholder
  - Body:
    ```json
    {"model_id": "resnet-50", "user_id": "alice", "prompt": "Hello", "parameters": {}, "risk": {"data_sensitivity": 1}}
    ```
  - Behavior: calls `mcp-policy/validate` and, if allowed, logs to `mcp-audit/log` and returns a simulated response payload with the policy decision attached.
