# mcp-lineage

The model registration service. It records where each model came from.

## What it does

- Registers model versions with their artifacts and metadata.
- Looks up the history of a model by `model_id`.

## Settings

- `DATABASE_URL` (required). Example: `postgresql://mcp:mcppass@db:5432/mcpgov`

## Endpoints

- `GET /healthz` returns `{ "ok": true }`.
- `POST /register` registers a model. Example body: `{ "model_id": "resnet-50", "version": "1.0.0", "artifacts": [], "created_by": "me@example.com", "metadata": {} }`
- `GET /lineage/{model_id}` returns the records for that model.

## Run it locally

```powershell
cd services/mcp-lineage
$env:DATABASE_URL = "postgresql://mcp:mcppass@localhost:5432/mcpgov"
uvicorn lineage_app:app --host 0.0.0.0 --port 8000 --reload
```

## Logging and security

- Passes along the `X-Request-ID` that the gateway sends.
- Writes structured JSON logs that include the request ID.
- Adds security headers to every response.

## Troubleshooting

- Make sure the database can be reached through `DATABASE_URL`.
- Check that the baseline schema and the migrations were applied.
