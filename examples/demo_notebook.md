# Demo Walkthrough

This walkthrough shows the full flow with `curl` and the small Python client.

## Before you start

- Docker Engine with Docker Compose v2
- `jq` to format the output
- Optional: Python 3.11 to run the client

## Start the stack

```bash
docker compose up -d --build
# Wait for the gateway
for i in {1..60}; do curl -sf http://localhost:8080/mcp && break; sleep 2; done
```

## List the services

```bash
curl -s http://localhost:8080/mcp | jq
```

## Register a model

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  --data @examples/register_model.json \
  http://localhost:8080/mcp-lineage/register | jq
```

## Check the policy

This model has every field the policy requires, so it is allowed.

```bash
cat > /tmp/policy-input.json <<'JSON'
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
      "shap_report_path": "reports/demo-shap.json",
      "lineage_hashes": ["sha256:example"]
    }
  }
}
JSON

curl -s -X POST \
  -H "Content-Type: application/json" \
  --data @/tmp/policy-input.json \
  http://localhost:8080/mcp-policy/validate | jq
```

To see a denial, change `contains_forbidden_data` to `true` and send it again.

## Log an audit event

```bash
cat > /tmp/audit.json <<'JSON'
{
  "event_type": "policy_decision",
  "subject": "resnet-50@1.0.0",
  "decision": true,
  "details": {"reason": "allowed for general use"}
}
JSON

curl -s -X POST \
  -H "Content-Type: application/json" \
  --data @/tmp/audit.json \
  http://localhost:8080/mcp-audit/log | jq
```

## Use the Python client

```python
from clients.python.governance_client import GovernanceClient

c = GovernanceClient()
print(c.get_services())

payload = {
    "flags": {"contains_forbidden_data": False},
    "context": {"safety_critical": True},
    "metrics": {"accuracy": 0.97},
    "risk": {
        "data_sensitivity": 1,
        "model_complexity": 1,
        "deployment_impact": 1,
        "monitoring_maturity": 3,
    },
}
print(c.validate(payload))
```
