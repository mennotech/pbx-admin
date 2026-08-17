"""Data-access layer: all SQL for servers, access control, and audit logging."""

from flask import g, request

from .db import get_db

_SERVER_SELECT = "SELECT s.id, s.slug, s.display_name, s.upstream_base_url FROM servers s"
_SERVER_ACCESS_JOIN = " JOIN user_server_access usa ON usa.server_id = s.id"


def get_allowed_servers(user_email: str):
    return get_db().execute(
        _SERVER_SELECT + _SERVER_ACCESS_JOIN
        + " WHERE usa.user_email = ? AND s.enabled = 1 ORDER BY s.display_name",
        (user_email,),
    ).fetchall()


def get_server_for_user(user_email: str, server_id: str):
    return get_db().execute(
        _SERVER_SELECT + _SERVER_ACCESS_JOIN
        + " WHERE usa.user_email = ? AND s.id = ? AND s.enabled = 1",
        (user_email, server_id),
    ).fetchone()


def get_server_by_slug_for_user(user_email: str, slug: str):
    return get_db().execute(
        _SERVER_SELECT + _SERVER_ACCESS_JOIN
        + " WHERE usa.user_email = ? AND s.slug = ? AND s.enabled = 1",
        (user_email, slug),
    ).fetchone()


def get_server_by_slug(slug: str):
    return get_db().execute(
        _SERVER_SELECT + " WHERE s.slug = ? AND s.enabled = 1",
        (slug,),
    ).fetchone()


def get_all_servers():
    """Every server in the registry, regardless of per-user access."""
    return get_db().execute(
        "SELECT id, slug, display_name, upstream_base_url, enabled"
        " FROM servers ORDER BY display_name"
    ).fetchall()


def add_server(server_id: str, slug: str, display_name: str, upstream_base_url: str,
               enabled: bool = True) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO servers (id, slug, display_name, upstream_base_url, enabled)"
        " VALUES (?, ?, ?, ?, ?)",
        (server_id, slug, display_name, upstream_base_url, 1 if enabled else 0),
    )
    db.commit()


def delete_server(server_id: str) -> None:
    db = get_db()
    db.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    db.commit()


def grant_access(user_email: str, server_id: str, role: str = "admin") -> None:
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO user_server_access (user_email, server_id, role)"
        " VALUES (?, ?, ?)",
        (user_email, server_id, role),
    )
    db.commit()


def log_audit(action: str, server_id: str | None = None, details: str | None = None) -> None:
    email = g.get("identity", {}).get("email", "unknown")
    db = get_db()
    db.execute(
        "INSERT INTO audit_log (user_email, action, server_id, request_path, client_ip, details)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (email, action, server_id, request.path, request.remote_addr, details),
    )
    db.commit()
