"""
Minimal, repeatable schema migration runner.

Behavior:
- Ensures a tracking table `schema_migrations` exists.
- Detects/apply baseline infra/init.sql on empty DB (no user tables), then records version '0000_init'.
- Applies SQL files in infra/migrations/*.sql in lexicographic order, recording version + checksum.
- Validates checksum for already applied migrations and fails on drift.

Environment:
- DATABASE_URL (required) e.g., postgresql://mcp:mcppass@localhost:5432/mcpgov

Dependencies:
- psycopg (installed in the db-migrate service from local wheelhouse)
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg  # provided by either 'psycopg' or 'psycopg-binary'
except Exception:  # pragma: no cover
    # Some environments ship a module named 'psycopg_binary'. Fallback to it if present.
    import importlib

    psycopg = importlib.import_module("psycopg_binary")


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SQL = REPO_ROOT / "infra" / "init.sql"
MIGRATIONS_DIR = REPO_ROOT / "infra" / "migrations"


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ensure_schema_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists schema_migrations (
              version text primary key,
              checksum text not null,
              applied_at timestamptz not null default now()
            )
            """
        )
    conn.commit()


def table_exists(conn: psycopg.Connection, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select exists (
              select 1 from pg_catalog.pg_tables
              where schemaname = 'public' and tablename = %s
            )
            """,
            (table,),
        )
        (exists,) = cur.fetchone()
        return bool(exists)


def get_applied(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("select version, checksum from schema_migrations order by version")
        rows = cur.fetchall()
    return {v: c for (v, c) in rows}


def apply_sql(conn: psycopg.Connection, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    # Execute whole script in a single transaction
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def record_migration(conn: psycopg.Connection, version: str, checksum: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "insert into schema_migrations(version, checksum, applied_at) values (%s, %s, %s)",
            (version, checksum, datetime.utcnow()),
        )
    conn.commit()


def maybe_apply_baseline(conn: psycopg.Connection) -> None:
    """Apply baseline from init.sql if DB is empty; otherwise only record it if missing."""
    baseline_version = "0000_init"
    baseline_checksum = sha256_file(INIT_SQL)

    applied = get_applied(conn)
    already = applied.get(baseline_version)

    # If a record exists, validate checksum and return
    if already:
        if already != baseline_checksum:
            print(
                f"ERROR: Baseline checksum drift for {baseline_version}: applied={already} current={baseline_checksum}",
                file=sys.stderr,
            )
            sys.exit(2)
        return

    # Determine emptiness by presence of known baseline tables
    has_lineage = table_exists(conn, "model_lineage")
    has_audit = table_exists(conn, "audit_log")

    if not (has_lineage or has_audit):
        print(f"Applying baseline {baseline_version} from {INIT_SQL.relative_to(REPO_ROOT)}...")
        apply_sql(conn, INIT_SQL)
    else:
        print("Baseline tables detected; recording baseline only.")

    record_migration(conn, baseline_version, baseline_checksum)


def apply_new_migrations(conn: psycopg.Connection) -> int:
    applied = get_applied(conn)
    if not MIGRATIONS_DIR.exists():
        return 0

    sql_files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
    applied_count = 0
    for path in sql_files:
        version = path.name
        checksum = sha256_file(path)
        if version in applied:
            if applied[version] != checksum:
                print(
                    f"ERROR: Checksum drift for migration {version}: applied={applied[version]} current={checksum}",
                    file=sys.stderr,
                )
                sys.exit(3)
            continue
        print(f"Applying migration {version}...")
        apply_sql(conn, path)
        record_migration(conn, version, checksum)
        applied_count += 1
    return applied_count


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    # Ensure files exist
    if not INIT_SQL.exists():
        print(f"Missing baseline file: {INIT_SQL}", file=sys.stderr)
        return 1

    # Connect and run migrations
    with psycopg.connect(db_url, autocommit=False) as conn:
        ensure_schema_table(conn)
        maybe_apply_baseline(conn)
        count = apply_new_migrations(conn)
        print(f"Migrations complete. Applied {count} new migration(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
