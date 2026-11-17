# Contributing

This project uses Python 3.11 for local tools and Docker Compose v2 for the full stack. Keep changes small, never rewrite old migrations, and update the API or architecture docs when behavior changes.

## Set up

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Set a private password in .env. Keep POSTGRES_PASSWORD and DATABASE_URL in sync.
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Git ignores `.env`. Never commit real passwords or private signing keys.

## Run and test

Start the stack and wait for the health checks to pass:

```powershell
docker compose up -d --build
docker compose ps
```

Run the unit tests first. They do not need the stack. Then run everything while Compose is up:

```powershell
python -m pytest -m "not integration"
python -m pytest
```

Pytest reports coverage for `services`, `scripts`, and `clients`. The minimum is 0 for now while coverage grows.

## Code checks

CI runs these checks. Run them before you open a pull request:

```powershell
ruff check .
black --check . --line-length 100 --target-version py311
mypy services clients
pylint services
vulture . scripts/vulture_whitelist.py --min-confidence 80 --exclude "wheelhouse,infra/keys,backups,__pycache__,.venv,test_venv"
```

## Database changes

- Add a new migration in `infra/migrations/` with a zero padded number.
- Never edit a migration that was already applied, or the baseline in `infra/init.sql`. The runner stores checksums and stops if they change.
- Compose runs `db-migrate` before the application services start.
- To run migrations by hand, use Python 3.11 with `psycopg` installed and set `DATABASE_URL`.

## API and policy changes

- Use parameterized SQL for every value.
- When you add an endpoint, update the path allowlists in `services/mcp-gateway/gateway_app.py` and the list in `docs/API.md`.
- Keep policy rules easy to read, and update the tests when evaluation changes.
- Load YAML with `yaml.safe_load`.
- Keep private keys out of the repository. The service only needs the public key for AIBOM checks.

## Pull request checklist

- [ ] Tests, Ruff, Black, mypy, Pylint, and Vulture pass.
- [ ] Changes to the API, policy, or migrations are documented.
- [ ] You understand the checksum and rollback impact of any migration.
- [ ] No passwords, private keys, or unreviewed test data are included.
