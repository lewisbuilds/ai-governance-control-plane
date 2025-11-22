# Database migrations

This folder contains incremental SQL migrations applied after the baseline `infra/init.sql`.

Conventions:
- Files are applied in lexicographic order. Use a zero-padded numeric prefix, e.g. `0001_add_index.sql`, `0002_alter_table.sql`.
- Each file should be idempotent or guarded appropriately; the runner tracks applied versions in `schema_migrations` and won’t re-apply them.
- The runner computes and stores a SHA-256 checksum for each migration. If a file changes after being applied, the runner fails fast to prevent drift.

Baseline handling:
- On an empty database (no user tables), the runner will execute `infra/init.sql` and record version `0000_init`.
- On an existing database (e.g., created by Postgres’ entrypoint running `init.sql`), the runner records the baseline without re-applying it.

Apply migrations:
- Via Docker Compose: the `db-migrate` one-off service runs automatically and other services wait for it.
- Manually (host): ensure `DATABASE_URL` is set and run `python scripts/migrate.py` in a Python 3.11 environment with `psycopg` installed.

Creating a migration:
1. Create a new `NNNN_description.sql` file in this folder.
2. Write the SQL needed to move from the previous version to the new one.
3. Commit with an explanation in the PR description.
