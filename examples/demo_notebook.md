# AI Governance Control Plane - Demo walkthrough

This walkthrough shows the basic end-to-end flow using `curl` and the minimal Python client.

## Prerequisites

- Docker Engine + Docker Compose v2
- Optional: Python 3.11 to run the simple client

## Start the stack

```bash
docker compose up -d --build
# wait for gateway
for i in {1..60}; do curl -sf http://localhost:8080/mcp && break; sleep 2; done
```

## List available services

```bash
curl -s http://localhost:8080/mcp | jq
```

## Register model lineage

```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  --data @examples/register_model.json \
  http://localhost:8080/mcp-lineage/register | jq
```

## Run a policy validation

```bash
cat > /tmp/policy-input.json <<'JSON'
{
  "payload": {
    "model_class": "vision",
    "use_case": "general",
    "region": "global",
    "risk": {
      "data_sensitivity": 1,
      "model_complexity": 2,
      "deployment_impact": 1,
      "monitoring_maturity": 3
    },
    "claims": {"human_in_loop": true}
  }
}
JSON

curl -s -X POST \
  -H "Content-Type: application/json" \
  --data @/tmp/policy-input.json \
  http://localhost:8080/mcp-policy/validate | jq
```

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

## Python minimal client

```python
from clients.python.governance_client import GovernanceClient

c = GovernanceClient()
print(c.get_services())

payload = {
    "model_class": "vision",
    "use_case": "general",
    "risk": {
        "data_sensitivity": 1,
        "model_complexity": 2,
        "deployment_impact": 1,
        "monitoring_maturity": 3,
    },
}
print(c.validate(payload))
```
