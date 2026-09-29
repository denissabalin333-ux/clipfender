"""Application bootstrap configuration loaded before backend modules import environment-sensitive settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

# Load local .env before other modules read os.environ at import time.
# Render/Docker environment variables take precedence over the local file.
load_dotenv(ENV_PATH, override=False)

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "1" if APP_ENV == "production" else "0").strip().lower() not in {"0", "false", "no", "off"}
