import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate.py"


@pytest.fixture()
def migrate(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("migrate_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["migrate_under_test"] = module
    spec.loader.exec_module(module)

    init = tmp_path / "init.sql"
    init.write_text("create table model_lineage(id int);", encoding="utf-8")
    folder = tmp_path / "migrations"
    folder.mkdir()
    monkeypatch.setattr(module, "INIT_SQL", init)
    monkeypatch.setattr(module, "MIGRATIONS_DIR", folder)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    state = {"applied": {}, "ran": [], "recorded": [], "tables": set()}
    monkeypatch.setattr(module, "get_applied", lambda conn: dict(state["applied"]))
    monkeypatch.setattr(module, "table_exists", lambda conn, t: t in state["tables"])
    monkeypatch.setattr(module, "apply_sql", lambda conn, p: state["ran"].append(p.name))
    monkeypatch.setattr(
        module,
        "record_migration",
        lambda conn, v, c: (state["recorded"].append(v), state["applied"].update({v: c})),
    )
    module.state = state
    module.folder = folder
    return module


def test_checksum_is_stable_and_content_sensitive(migrate, tmp_path):
    a = tmp_path / "a.sql"
    a.write_text("select 1;")
    first = migrate.sha256_file(a)
    assert first == migrate.sha256_file(a) == migrate.sha256_bytes(b"select 1;")
    a.write_text("select 2;")
    assert migrate.sha256_file(a) != first


def test_baseline_runs_on_empty_database(migrate):
    migrate.maybe_apply_baseline(object())
    assert migrate.state["ran"] == ["init.sql"]
    assert migrate.state["recorded"] == ["0000_init"]


def test_baseline_is_only_recorded_when_tables_exist(migrate):
    migrate.state["tables"].add("audit_log")
    migrate.maybe_apply_baseline(object())
    assert migrate.state["ran"] == []
    assert migrate.state["recorded"] == ["0000_init"]


def test_baseline_is_skipped_when_already_applied(migrate):
    migrate.state["applied"]["0000_init"] = migrate.sha256_file(migrate.INIT_SQL)
    migrate.maybe_apply_baseline(object())
    assert migrate.state["ran"] == [] and migrate.state["recorded"] == []


def test_baseline_drift_stops_with_exit_code_2(migrate):
    migrate.state["applied"]["0000_init"] = "stale"
    with pytest.raises(SystemExit) as err:
        migrate.maybe_apply_baseline(object())
    assert err.value.code == 2


def test_new_migrations_apply_in_name_order(migrate):
    (migrate.folder / "0002_b.sql").write_text("select 2;")
    (migrate.folder / "0001_a.sql").write_text("select 1;")
    (migrate.folder / "notes.txt").write_text("ignored")

    count = migrate.apply_new_migrations(object())

    assert count == 2
    assert migrate.state["ran"] == ["0001_a.sql", "0002_b.sql"]


def test_applied_migrations_are_not_run_again(migrate):
    path = migrate.folder / "0001_a.sql"
    path.write_text("select 1;")
    migrate.state["applied"]["0001_a.sql"] = migrate.sha256_file(path)

    assert migrate.apply_new_migrations(object()) == 0
    assert migrate.state["ran"] == []


def test_edited_migration_stops_with_exit_code_3(migrate):
    path = migrate.folder / "0001_a.sql"
    path.write_text("select 1;")
    migrate.state["applied"]["0001_a.sql"] = migrate.sha256_file(path)
    path.write_text("select 99;")

    with pytest.raises(SystemExit) as err:
        migrate.apply_new_migrations(object())
    assert err.value.code == 3
    assert migrate.state["ran"] == []


def test_missing_migrations_folder_is_not_an_error(migrate, tmp_path, monkeypatch):
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path / "absent")
    assert migrate.apply_new_migrations(object()) == 0


def test_main_requires_database_url(migrate, monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert migrate.main() == 1
    assert "DATABASE_URL" in capsys.readouterr().err


def test_main_requires_baseline_file(migrate, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(migrate, "INIT_SQL", tmp_path / "missing.sql")
    assert migrate.main() == 1
    assert "Missing baseline" in capsys.readouterr().err


class _Conn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_main_runs_baseline_then_migrations(migrate, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr(migrate.psycopg, "connect", lambda url, autocommit=False: _Conn())
    monkeypatch.setattr(migrate, "ensure_schema_table", lambda conn: None)
    (migrate.folder / "0001_a.sql").write_text("select 1;")

    assert migrate.main() == 0
    assert migrate.state["recorded"] == ["0000_init", "0001_a.sql"]
    assert "Applied 1 new migration" in capsys.readouterr().out


class _Cursor:
    def __init__(self, rows=None, one=None):
        self.rows, self.one, self.sql = rows or [], one, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql.append((sql, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one


class _Db:
    def __init__(self, cursor):
        self._cursor, self.commits = cursor, 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


def test_database_helpers_issue_expected_statements(tmp_path):
    spec = importlib.util.spec_from_file_location("migrate_real", SCRIPT)
    real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real)

    cur = _Cursor(rows=[("0000_init", "abc")], one=(True,))
    db = _Db(cur)

    real.ensure_schema_table(db)
    assert "schema_migrations" in cur.sql[0][0] and db.commits == 1
    assert real.table_exists(db, "audit_log") is True
    assert real.get_applied(db) == {"0000_init": "abc"}

    script = tmp_path / "x.sql"
    script.write_text("select 1;", encoding="utf-8")
    real.apply_sql(db, script)
    assert cur.sql[-1][0] == "select 1;"

    real.record_migration(db, "0001_a.sql", "sum")
    assert cur.sql[-1][1][:2] == ("0001_a.sql", "sum")
    assert db.commits == 3
