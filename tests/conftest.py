"""Shared pytest fixtures: an app bound to a temporary, seeded SQLite database."""

import sqlite3

import pytest

from pbx_admin import create_app
from pbx_admin import db as db_module

SEED_SQL = """
INSERT INTO servers (id, slug, display_name, upstream_base_url, enabled) VALUES
  ('pbx-a', 'a', 'Alpha PBX', 'https://alpha.internal', 1),
  ('pbx-b', 'b', 'Beta PBX', 'https://beta.internal', 1),
  ('pbx-off', 'off', 'Disabled PBX', 'https://off.internal', 0);
INSERT INTO user_server_access (user_email, server_id, role) VALUES
  ('user@example.com', 'pbx-a', 'admin'),
  ('user@example.com', 'pbx-off', 'admin');
"""


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    application = create_app(
        overrides={
            "SQLITE_PATH": str(db_path),
            "SECRET_KEY": "test-secret",
            "DB_AUTO_SEED": False,
            "METRICS_CHECK_ENABLED": False,
            "CF_TEAM_DOMAIN": "team.example.com",
            "TESTING": True,
        }
    )
    with application.app_context():
        db_module.init_db(application)

    conn = sqlite3.connect(db_path)
    conn.executescript(SEED_SQL)
    conn.commit()
    conn.close()
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def as_user(monkeypatch):
    """Bypass Cloudflare Access by faking the verified identity."""

    def _login(email="user@example.com"):
        monkeypatch.setattr("pbx_admin.auth.get_identity", lambda: {"email": email})

    return _login
