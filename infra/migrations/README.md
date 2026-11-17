# Database migrations

This folder holds the SQL changes that run after the baseline file `infra/init.sql`.

## Rules

- Files run in name order. Start each name with a zero padded number, such as `0001_add_index.sql` or `0002_alter_table.sql`.
- Write each file so it is safe to run again, or guard it properly. The runner records applied versions in `schema_migrations` and does not run them twice.
- The runner stores a SHA 256 checksum for each migration. If a file changes after it was applied, the runner stops so the history cannot drift.

## The baseline

- On an empty database, the runner executes `infra/init.sql` and records version `0000_init`.
- On a database that already has tables, such as one created by the Postgres entrypoint running `init.sql`, the runner records the baseline without running it again.

## Run migrations

- **With Docker Compose:** the one off `db-migrate` service runs automatically. The other services wait for it.
- **By hand:** set `DATABASE_URL` and run `python scripts/migrate.py`. Use Python 3.11 with `psycopg` installed.

## Add a migration

1. Create a file named `NNNN_description.sql` in this folder.
2. Write the SQL that moves the database from the previous version to the new one.
3. Explain the change in your pull request.
