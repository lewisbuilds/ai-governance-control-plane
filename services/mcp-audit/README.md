# mcp-audit

The audit log service. It only adds events. Each event is linked to the one before it with a hash.

## What it does

- Accepts audit events and stores them in `audit_log`. Each row holds `prev_hash` and `entry_hash`.
- Blocks `UPDATE` and `DELETE` with database triggers, so rows cannot be changed in normal use.

## Settings

- `DATABASE_URL` (required). Example: `postgresql://mcp:mcppass@db:5432/mcpgov`

## Endpoints

- `GET /healthz` returns `{ "ok": true }`.
- `POST /log` adds an event. Example body: `{ "event_type": "policy_decision", "subject": "resnet-50@1.0.0", "decision": true, "details": {} }`
- `GET /events?limit=100&offset=0` lists events.
- `GET /export?fmt=json` or `fmt=csv` exports the log.

## Run it locally

```powershell
cd services/mcp-audit
$env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"
uvicorn audit_app:app --host 0.0.0.0 --port 8000 --reload
```

## Logging and security

- Passes along the `X-Request-ID` that the gateway sends.
- Writes structured JSON logs that include the request ID.
- Adds security headers to every response.

## Troubleshooting

- Make sure the database can be reached through `DATABASE_URL`.
- If the triggers fail, check that the schema was applied. See `infra/init.sql` and the migration runner.
