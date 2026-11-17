# API Reference

Inside Compose, every service listens on port `8000`. You reach them through the gateway at `http://localhost:8080`.

A gateway path looks like `/mcp-{service}/{endpoint}`. For example, `POST /mcp-policy/validate` is forwarded to the policy service as `POST /validate`.

The API uses REST and JSON. The `mcp` in the service names does not mean the Model Context Protocol is supported.

## Directory and health

- `GET /mcp` returns `{"services": [...], "directory": {...}}`.
- Every service has `GET /healthz`, which returns `{"ok": true}`.

## Lineage service

- `POST /mcp-lineage/register` adds a record.
- `GET /mcp-lineage/lineage/{model_id}` returns all records for one model.

Example request body for registering a model:

```json
{
  "model_id": "resnet-50",
  "version": "1.0.0",
  "artifacts": ["sha256:example"],
  "created_by": "mlops@example.com",
  "metadata": {"framework": "pytorch"}
}
```

## Policy service

- `POST /mcp-policy/validate` checks a payload against the policy.
- `POST /mcp-policy/api/v1/policies/validate` does the same thing. It exists for older callers.

Example request body:

```json
{
  "payload": {
    "flags": {"contains_forbidden_data": false},
    "context": {"safety_critical": true},
    "metrics": {"accuracy": 0.97},
    "risk": {
      "data_sensitivity": 1,
      "model_complexity": 1,
      "deployment_impact": 1,
      "monitoring_maturity": 3
    },
    "evidence": {
      "shap_report_path": "reports/shap.json",
      "lineage_hashes": ["sha256:example"]
    }
  }
}
```

The response contains:

- `allowed`: whether the model passed.
- `reasons`: plain language reasons for the decision.
- `notes`: notes from the policy file.
- `risk_score`: the weighted score.
- `within_sla`: whether the check finished on time.
- `elapsed_ms`: how long the check took.

The service applies the rules in `policies/model-policy.yml` and calculates the score from `policies/risk-matrix.yml`. Every weighted risk factor must be a number from 0 to 5. A missing or invalid value denies the request. If a check takes longer than `GATE_SLA_MS`, the response adds a warning but still returns the decision.

When AIBOM checking is on, or when you send an AIBOM anyway, add this to the payload:

```json
{"aibom": {"digest": "sha256:...", "signature_b64": "..."}}
```

The Ed25519 signature must cover the exact bytes of the digest text. Only the public key is mounted into the service.

## Audit service

- `POST /mcp-audit/log` adds an event. It needs `event_type`, `subject`, and `decision`. `details` is optional.
- `GET /mcp-audit/events?limit=100&offset=0` lists recent events.
- `GET /mcp-audit/export?fmt=json` returns the log as JSON.
- `GET /mcp-audit/export?fmt=csv` returns the log as CSV.

Each event includes `prev_hash` and `entry_hash`. Export the log and compare them to check that the chain is unbroken.

## How the gateway routes requests

The gateway forwards only to known services and known paths. When you add an endpoint to a service, also add its path to the allowlist in `services/mcp-gateway/gateway_app.py`. Query strings are passed along. The response body, status, and content type are returned unchanged, including CSV exports.

The gateway also has higher level endpoints for registering and running a model. These are demo examples. They are not a safe all or nothing workflow for production use.
