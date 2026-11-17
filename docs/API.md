# API Reference

All services listen on port `8000` inside Compose. The gateway is available at `http://localhost:8080`. A gateway path is `/mcp-{service}/{service-endpoint}`; for example, `POST /mcp-policy/validate` forwards to policy service `POST /validate`.

The API uses REST/JSON. The `mcp-*` service names do not mean that the current implementation exposes Model Context Protocol transports.

## Directory and health

- `GET /mcp` returns `{"services": [...], "directory": {...}}`.
- Each service exposes `GET /healthz` returning `{"ok": true}`.

## Lineage service

- `POST /mcp-lineage/register` creates a record.
- `GET /mcp-lineage/lineage/{model_id}` returns that model's records.

Registration body:

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

- `POST /mcp-policy/validate` evaluates a payload.
- `POST /mcp-policy/api/v1/policies/validate` is a compatibility alias.

Request body:

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

The result includes `allowed`, human-readable `reasons`, policy `notes`, `risk_score`, `within_sla`, and `elapsed_ms`. The service evaluates the rules in `policies/model-policy.yml`; the numeric score is computed from `policies/risk-matrix.yml`. All weighted risk factors must be numeric and between 0 and 5; missing or invalid values deny the request. If evaluation exceeds `GATE_SLA_MS`, the response includes a warning reason and still returns the decision.

When AIBOM verification is enabled or an AIBOM is supplied, the payload uses:

```json
{"aibom": {"digest": "sha256:...", "signature_b64": "..."}}
```

The Ed25519 signature is over the exact UTF-8 bytes of the digest string. Only a public PEM key is mounted into the service.

## Audit service

- `POST /mcp-audit/log` appends an event with `event_type`, `subject`, `decision`, and optional `details`.
- `GET /mcp-audit/events?limit=100&offset=0` lists recent events.
- `GET /mcp-audit/export?fmt=json` returns JSON.
- `GET /mcp-audit/export?fmt=csv` returns CSV with `Content-Type: text/csv`.

An event response includes `prev_hash` and `entry_hash`. Use the export to inspect continuity across rows.

## Gateway routing and limitations

The gateway only forwards configured service names and endpoint paths. If an endpoint is added, its service path must also be allowlisted in `services/mcp-gateway/gateway_app.py`. Query strings are forwarded. The gateway preserves response body, status, and content type, including CSV exports.

The high-level model registration and inference endpoints in `gateway_app.py` are demo orchestration examples. They are not an atomic or production inference workflow.
