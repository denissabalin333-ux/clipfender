from __future__ import annotations

import os
import sys
import tempfile
import atexit
import types
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "googleapiclient" not in sys.modules:
    try:
        import googleapiclient  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        google_pkg = types.ModuleType("googleapiclient")
        discovery = types.ModuleType("googleapiclient.discovery")
        errors = types.ModuleType("googleapiclient.errors")

        def build(*args, **kwargs):
            raise RuntimeError("google-api-python-client is not installed in the test environment")

        class HttpError(Exception):
            pass

        discovery.build = build
        errors.HttpError = HttpError
        google_pkg.discovery = discovery
        google_pkg.errors = errors
        sys.modules["googleapiclient"] = google_pkg
        sys.modules["googleapiclient.discovery"] = discovery
        sys.modules["googleapiclient.errors"] = errors


_db_path = Path(tempfile.gettempdir()) / f"clipfender_pytest_{os.getpid()}.db"
os.environ.setdefault("CLIPFINDER_DB_PATH", str(_db_path))
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")
os.environ.setdefault("APP_ENV", "development")


@atexit.register
def _cleanup_test_db() -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            (_db_path.parent / (_db_path.name + suffix)).unlink()
        except FileNotFoundError:
            pass
