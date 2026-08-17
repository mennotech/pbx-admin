"""Configuration for the PBX admin server, sourced from environment variables.

Values are read once at import time and applied to ``app.config`` in the
application factory. Tests override any of these by passing ``overrides`` to
:func:`pbx_admin.create_app`.
"""

import os
from datetime import timedelta
from pathlib import Path

# Repository root for source checkouts, used by local-development defaults.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SQL_RESOURCE_DIR = REPOSITORY_ROOT / "resources" / "sql"


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() == "true"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class Config:
    """Base configuration read from the environment."""

    # --- Routing / identity ------------------------------------------------
    CONTROL_PREFIX = os.getenv("CONTROL_PREFIX", "/-control")
    JWT_HEADER_NAME = os.getenv("CF_ACCESS_JWT_HEADER", "Cf-Access-Jwt-Assertion")
    CF_TEAM_DOMAIN = os.getenv("CF_ACCESS_TEAM_DOMAIN", "")
    CF_AUDIENCE = os.getenv("CF_ACCESS_AUDIENCE", "")

    # --- Database ----------------------------------------------------------
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(REPOSITORY_ROOT / "instance" / "pbx_admin.db"))
    SCHEMA_PATH = os.getenv("SCHEMA_PATH", str(SQL_RESOURCE_DIR / "schema.sql"))
    SEED_PATH = os.getenv("SEED_PATH", str(SQL_RESOURCE_DIR / "seed.sql"))
    DB_AUTO_SEED = _env_bool("DB_AUTO_SEED", False)

    # --- Session (Flask-native keys) --------------------------------------
    SECRET_KEY = os.getenv("SESSION_SECRET", "")
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "pbx_admin_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_TTL_HOURS = _env_int("SESSION_TTL_HOURS", 12)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=SESSION_TTL_HOURS)

    # --- Upstream proxy ----------------------------------------------------
    UPSTREAM_TIMEOUT_SECONDS = _env_int("UPSTREAM_TIMEOUT_SECONDS", 45)
    UPSTREAM_VERIFY_TLS = _env_bool("UPSTREAM_VERIFY_TLS", False)

    # --- Metrics health check / proxy -------------------------------------
    METRICS_CHECK_ENABLED = _env_bool("METRICS_CHECK_ENABLED", True)
    METRICS_CHECK_TIMEOUT = _env_int("METRICS_CHECK_TIMEOUT_SECONDS", 5)
    METRICS_VERIFY_TLS = _env_bool("METRICS_VERIFY_TLS", False)
    METRICS_URL_TEMPLATE = os.getenv("METRICS_URL_TEMPLATE", "https://{host}:8089/metrics")
    METRICS_ORIGIN_URL_TEMPLATE = os.getenv("METRICS_ORIGIN_URL_TEMPLATE", "https://{host}:8089/metrics")
    METRICS_BASIC_AUTH_USER = os.getenv("METRICS_BASIC_AUTH_USER", "")
    METRICS_BASIC_AUTH_PASS = os.getenv("METRICS_BASIC_AUTH_PASS", "")
