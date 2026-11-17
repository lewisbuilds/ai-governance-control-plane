# Contributing

This project uses Python 3.11 for local tooling and Docker Compose v2 for the full stack. Keep changes small, preserve the migration history, and update API or architecture docs when behavior changes.

## Local setup

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Set a private local password in .env and keep POSTGRES_PASSWORD and DATABASE_URL in sync.
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

The `.env` file is ignored by Git. Do not commit real credentials or private signing keys.

## Run and test

Start the stack and wait for Compose health checks:

```powershell
docker compose up -d --build
docker compose ps
```

Run unit tests without requiring the stack, then run the complete integration suite while Compose is up:

```powershell
python -m pytest -m "not integration"
python -m pytest
```

Pytest reports coverage for `services`, `scripts`, and `clients`. The current minimum is 0 while coverage is expanded; the latest verified full run reports 42%.

## Static checks

CI runs these quality checks:

```powershell
ruff check .
black --check . --line-length 100 --target-version py311
mypy services clients
pylint services
vulture . scripts/vulture_whitelist.py --min-confidence 80 --exclude "wheelhouse,infra/keys,backups,__pycache__,.venv,test_venv"
```

## Database changes

- Add a new, zero-padded migration under `infra/migrations/`.
- Never edit an applied migration or the `infra/init.sql` baseline. The runner stores checksums and stops on drift.
- Compose runs `db-migrate` before application services.
- For manual execution, use Python 3.11 with `psycopg` installed and set `DATABASE_URL` to the target database.

## API and policy changes

- Use parameterized SQL for all values.
- When adding a service endpoint, update `services/mcp-gateway/gateway_app.py` path allowlists and `docs/API.md`.
- Keep policy rules human-readable and update tests for changed evaluation behavior.
- Use `yaml.safe_load` for YAML input.
- Keep private keys out of the repository. The service only needs an AIBOM verification public key.

## Pull request checklist

- [ ] Tests, Ruff, Black, mypy, Pylint, and Vulture pass.
- [ ] API, policy, or migration behavior is documented.
- [ ] Migration checksums and rollback implications are understood.
- [ ] No credentials, private keys, or unreviewed test data are included.
