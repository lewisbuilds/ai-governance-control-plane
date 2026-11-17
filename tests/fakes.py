"""Small test doubles that replace PostgreSQL and outbound HTTP calls."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeCursor:
    """Records SQL and returns scripted rows in order."""

    def __init__(self, one: list[Any] | None = None, many: list[list[Any]] | None = None):
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self._one = list(one or [])
        self._many = list(many or [])

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> Any:
        return self._one.pop(0) if self._one else None

    def fetchall(self) -> list[Any]:
        return self._many.pop(0) if self._many else []


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def cursor(self) -> FakeCursor:
        return self._cursor


class FakePool:
    """Stands in for psycopg_pool.ConnectionPool without opening a connection."""

    cursor = FakeCursor()
    fail = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def connection(self) -> FakeConnection:
        if FakePool.fail:
            raise RuntimeError("database unavailable")
        return FakeConnection(FakePool.cursor)


def load_service(module: str, folder: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import a service module with a fake connection pool and a dummy DATABASE_URL."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setattr("psycopg_pool.ConnectionPool", FakePool)
    path = str(REPO_ROOT / "services" / folder)
    monkeypatch.syspath_prepend(path)
    sys.modules.pop(module, None)
    return importlib.import_module(module)
