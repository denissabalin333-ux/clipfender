from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def test_render_blueprint_has_no_persistent_disk_and_uses_free_plan():
    import yaml

    document = yaml.safe_load(Path("render.yaml").read_text(encoding="utf-8"))
    service = document["services"][0]
    assert service["plan"] == "free"
    assert "disk" not in service
    keys = {item["key"] for item in service["envVars"]}
    assert {"TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN", "YOUTUBE_API_KEY", "OPENAI_API_KEY"} <= keys
    assert "CLIPFINDER_DB_PATH" not in keys


def test_turso_remote_row_adapter_preserves_named_and_indexed_access(monkeypatch):
    class FakeRawCursor:
        description = [("id", None, None, None, None, None, None), ("name", None, None, None, None, None, None)]
        rowcount = 1
        lastrowid = 0

        def __init__(self, rows):
            self.rows = list(rows)

        def fetchone(self):
            return self.rows.pop(0) if self.rows else None

        def fetchall(self):
            rows = list(self.rows)
            self.rows.clear()
            return rows

        def fetchmany(self, size):
            result = self.rows[:size]
            del self.rows[:size]
            return result

        def close(self):
            pass

    class FakeRawConnection:
        def __init__(self):
            self.cursor_obj = FakeRawCursor([(7, "Jon")])

        def execute(self, sql, params=()):
            if sql.startswith("SELECT last_insert_rowid"):
                cursor = FakeRawCursor([(7,)])
                cursor.description = [("id", None, None, None, None, None, None)]
                return cursor
            self.cursor_obj = FakeRawCursor([(7, "Jon")])
            return self.cursor_obj

        def cursor(self):
            self.cursor_obj = FakeRawCursor([(7, "Jon")])
            return self.cursor_obj

        def executemany(self, sql, params):
            self.cursor_obj = FakeRawCursor([])
            return self.cursor_obj

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    fake_module = types.ModuleType("turso_serverless")
    fake_module.connect = lambda database_url, auth_token: FakeRawConnection()
    monkeypatch.setitem(sys.modules, "turso_serverless", fake_module)

    from backend.database.remote import RemoteConnection

    connection = RemoteConnection(FakeRawConnection())
    row = connection.execute("SELECT id, name FROM people").fetchone()
    assert row[0] == 7
    assert row["id"] == 7
    assert row["name"] == "Jon"
    assert dict(row) == {"id": 7, "name": "Jon"}
    connection.close()


def test_remote_database_mode_selects_turso_connection(monkeypatch):
    import backend.database.database as database

    called = {}

    class FakeConnection:
        def close(self):
            pass

    def fake_remote(url, token):
        called["url"] = url
        called["token"] = token
        return FakeConnection()

    monkeypatch.setattr(database, "REMOTE_DATABASE_ENABLED", True)
    monkeypatch.setattr(database, "TURSO_DATABASE_URL", "libsql://example.turso.io")
    monkeypatch.setattr(database, "TURSO_AUTH_TOKEN", "secret")
    monkeypatch.setattr("backend.database.remote.connect_remote", fake_remote)

    connection = database.get_connection()
    assert called == {"url": "libsql://example.turso.io", "token": "secret"}
    connection.close()


def test_remote_portrait_path_is_database_backed():
    from backend.services import character_catalog

    assert character_catalog._build_profile("Санса Старк", "/media/characters/sansa-stark.webp", "ai_generation")["image"] == "/media/characters/sansa-stark.webp"
