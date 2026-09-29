"""Compatibility layer for using Turso/libSQL through a sqlite3-like API.

The application intentionally keeps its existing qmark SQL and connection
lifecycle.  When a TURSO_DATABASE_URL is configured, this adapter makes the
remote DB-API connection look enough like sqlite3 for the existing modules,
including named row access and lastrowid.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any


class RemoteRow(Mapping[str, Any], Sequence[Any]):
    """sqlite3.Row-like object backed by a tuple and column names."""

    __slots__ = ("_columns", "_values", "_index")

    def __init__(self, columns: Sequence[str], values: Sequence[Any]) -> None:
        self._columns = tuple(str(column) for column in columns)
        self._values = tuple(values)
        self._index = {column.casefold(): index for index, column in enumerate(self._columns)}

    def __getitem__(self, key: int | slice | str) -> Any:
        if isinstance(key, str):
            try:
                return self._values[self._index[key.casefold()]]
            except KeyError as error:
                raise IndexError(key) from error
        return self._values[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self):
        return self._columns

    def items(self):
        return ((column, self._values[index]) for index, column in enumerate(self._columns))

    def values(self):
        return iter(self._values)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except IndexError:
            return default


class RemoteCursor:
    def __init__(self, connection: "RemoteConnection", raw_cursor: Any) -> None:
        self._connection = connection
        self._raw = raw_cursor

    @property
    def description(self):
        return getattr(self._raw, "description", None)

    @property
    def rowcount(self) -> int:
        value = getattr(self._raw, "rowcount", -1)
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1

    @property
    def lastrowid(self) -> int | None:
        value = getattr(self._raw, "lastrowid", None)
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            numeric = 0
        if numeric:
            return numeric
        try:
            probe = self._connection.execute("SELECT last_insert_rowid() AS id").fetchone()
            if probe is not None:
                return int(probe["id"])
        except Exception:
            pass
        return None

    def execute(self, sql: str, parameters: Any = ()) -> "RemoteCursor":
        if parameters is None:
            parameters = ()
        if parameters == ():
            raw = self._connection._raw.execute(sql)
        else:
            raw = self._connection._raw.execute(sql, parameters)
        self._raw = raw
        return self

    def executemany(self, sql: str, seq_of_parameters: Any) -> "RemoteCursor":
        raw = self._connection._raw.executemany(sql, seq_of_parameters)
        self._raw = raw
        return self

    def fetchone(self) -> RemoteRow | None:
        raw_row = self._raw.fetchone()
        if raw_row is None:
            return None
        return self._wrap_row(raw_row)

    def fetchall(self) -> list[RemoteRow]:
        return [self._wrap_row(row) for row in self._raw.fetchall()]

    def fetchmany(self, size: int | None = None) -> list[RemoteRow]:
        rows = self._raw.fetchmany() if size is None else self._raw.fetchmany(size)
        return [self._wrap_row(row) for row in rows]

    def __iter__(self) -> Iterator[RemoteRow]:
        return iter(self.fetchall())

    def _wrap_row(self, row: Any) -> RemoteRow:
        description = self.description or ()
        columns = [item[0] for item in description]
        if isinstance(row, Mapping):
            if not columns:
                columns = list(row.keys())
            values = [row.get(column) for column in columns]
        else:
            values = list(row)
        return RemoteRow(columns, values)

    def close(self) -> None:
        close = getattr(self._raw, "close", None)
        if callable(close):
            close()


class RemoteConnection:
    """Small sqlite3-compatible facade over the libsql DB-API driver."""

    def __init__(self, raw_connection: Any) -> None:
        self._raw = raw_connection
        self._row_factory = None

    @property
    def row_factory(self):
        return self._row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        # The libsql driver does not expose sqlite3.Row. We always return
        # RemoteRow instances, which provide the same named/indexed access
        # the application uses.
        self._row_factory = value

    def execute(self, sql: str, parameters: Any = ()) -> RemoteCursor:
        if parameters is None:
            parameters = ()
        if parameters == ():
            raw = self._raw.execute(sql)
        else:
            raw = self._raw.execute(sql, parameters)
        return RemoteCursor(self, raw)

    def executemany(self, sql: str, seq_of_parameters: Any) -> RemoteCursor:
        raw = self._raw.executemany(sql, seq_of_parameters)
        return RemoteCursor(self, raw)

    def cursor(self) -> RemoteCursor:
        raw = self._raw.cursor()
        return RemoteCursor(self, raw)

    def commit(self) -> None:
        commit = getattr(self._raw, "commit", None)
        if callable(commit):
            commit()

    def rollback(self) -> None:
        rollback = getattr(self._raw, "rollback", None)
        if callable(rollback):
            rollback()

    def close(self) -> None:
        close = getattr(self._raw, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "RemoteConnection":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


def connect_remote(database_url: str, auth_token: str) -> RemoteConnection:
    if not database_url:
        raise RuntimeError("TURSO_DATABASE_URL не задан")
    if not auth_token:
        raise RuntimeError("TURSO_AUTH_TOKEN не задан")

    try:
        import turso_serverless
    except ImportError as error:  # pragma: no cover - exercised on deployment
        raise RuntimeError(
            "Для удалённой БД нужен пакет turso_serverless. Он должен быть установлен из requirements.txt."
        ) from error

    raw = turso_serverless.connect(database_url, auth_token=auth_token)
    return RemoteConnection(raw)
