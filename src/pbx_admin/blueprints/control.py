"""Control UI blueprint, mounted under ``CONTROL_PREFIX``.

Handles the router/console pages, server selection, health checks, and the
unauthenticated metrics proxy consumed by the Zabbix scraper.
"""

from datetime import datetime, timezone
import os
import re
import sqlite3
import time

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..auth import require_identity
from ..db import get_db
from ..metrics import build_metrics_origin_url, check_metrics_status, metrics_auth
from ..repository import (
    add_server,
    delete_server,
    get_all_servers,
    get_allowed_servers,
    get_server_by_slug,
    get_server_by_slug_for_user,
    get_server_for_user,
    grant_access,
    log_audit,
)

control_bp = Blueprint("control", __name__)

# Monotonic timestamp captured when this worker process imported the module;
# used to report process uptime (and thus detect restarts) via /-control/zabbix.
_PROCESS_START = time.monotonic()

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _validate_server(slug: str, display_name: str, upstream: str) -> str | None:
    if not slug or not _SLUG_RE.match(slug):
        return "Slug must be lowercase letters, numbers, or hyphens (no spaces)."
    if not display_name:
        return "Display name is required."
    if not (upstream.startswith("http://") or upstream.startswith("https://")):
        return "Upstream base URL must start with http:// or https://."
    return None


@control_bp.route("/", methods=["GET"])
@require_identity
def control_home():
    email = g.identity["email"]
    servers = [dict(row) for row in get_allowed_servers(email)]
    return render_template(
        "dashboard.html",
        active="dashboard",
        email=email,
        servers=servers,
        selected=session.get("selected_server_id"),
    )


@control_bp.route("/console", methods=["GET"])
@require_identity
def console_view():
    email = g.identity["email"]
    servers = [dict(row) for row in get_allowed_servers(email)]
    selected = session.get("selected_server_id")
    if not selected or not any(str(s["id"]) == str(selected) for s in servers):
        session.pop("selected_server_id", None)
        return redirect(url_for("control.control_home"))
    return render_template(
        "console.html",
        email=email,
        servers=servers,
        selected=selected,
        iframe_src="/",
    )


@control_bp.route("/console/<slug>", methods=["GET"])
@require_identity
def console_view_slug(slug: str):
    email = g.identity["email"]
    server = get_server_by_slug_for_user(email, slug)
    if not server:
        log_audit("console_denied", details=f"slug={slug}")
        return redirect(url_for("control.control_home"))

    server_id = str(server["id"])
    if session.get("selected_server_id") != server_id:
        session.permanent = True
        session["selected_server_id"] = server_id
        session["selected_at"] = datetime.now(timezone.utc).isoformat()
        log_audit("select_server", server_id=server_id, details=f"slug={slug}")

    servers = [dict(row) for row in get_allowed_servers(email)]
    return render_template(
        "console.html",
        email=email,
        servers=servers,
        selected=server_id,
        iframe_src="/",
    )


@control_bp.route("/select", methods=["POST"])
@require_identity
def select_server():
    email = g.identity["email"]
    server_id = request.form.get("server_id", "")
    server = get_server_for_user(email, server_id)
    if not server:
        log_audit("select_denied", server_id=server_id)
        return jsonify({"error": "server_not_allowed"}), 403

    session.permanent = True
    session["selected_server_id"] = server_id
    session["selected_at"] = datetime.now(timezone.utc).isoformat()
    log_audit("select_server", server_id=server_id)
    return redirect(url_for("control.console_view"))


@control_bp.route("/clear", methods=["POST"])
@require_identity
def clear_server():
    selected = session.pop("selected_server_id", None)
    session.pop("selected_at", None)
    log_audit("clear_server", server_id=selected)
    return redirect(url_for("control.control_home"))


@control_bp.route("/servers", methods=["GET", "POST"])
@require_identity
def servers_manage():
    email = g.identity["email"]
    if request.method == "POST":
        slug = request.form.get("slug", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        upstream = request.form.get("upstream_base_url", "").strip()
        error = _validate_server(slug, display_name, upstream)
        if error:
            flash(error, "error")
        else:
            server_id = f"pbx-{slug}"
            try:
                add_server(server_id, slug, display_name, upstream)
                grant_access(email, server_id, "admin")
                log_audit("add_server", server_id=server_id, details=upstream)
                flash(f"Added server '{display_name}'.", "success")
            except sqlite3.IntegrityError:
                flash("A server with that slug already exists.", "error")
        return redirect(url_for("control.servers_manage"))

    servers = [dict(row) for row in get_all_servers()]
    return render_template("servers.html", active="servers", email=email, servers=servers)


@control_bp.route("/servers/<server_id>/delete", methods=["POST"])
@require_identity
def servers_delete(server_id: str):
    delete_server(server_id)
    if session.get("selected_server_id") == server_id:
        session.pop("selected_server_id", None)
        session.pop("selected_at", None)
    log_audit("delete_server", server_id=server_id)
    flash("Server removed.", "success")
    return redirect(url_for("control.servers_manage"))


@control_bp.route("/status", methods=["GET"])
@require_identity
def status_view():
    email = g.identity["email"]
    servers = [dict(row) for row in get_all_servers()]
    for server in servers:
        server["metrics_status"] = check_metrics_status(server)
    return render_template("status.html", active="status", email=email, servers=servers)


@control_bp.route("/healthz", methods=["GET"])
def healthz():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@control_bp.route("/zabbix", methods=["GET"])
def zabbix_health():
    """Unauthenticated health + DB statistics for the Zabbix scraper.

    Like ``/metrics/<slug>``, Cloudflare bypasses SSO for the monitoring host,
    so no CF Access JWT is required here. Returns a single JSON document that a
    Zabbix HTTP agent master item polls; dependent items extract fields via
    JSONPath preprocessing.
    """
    db_path = current_app.config["SQLITE_PATH"]
    try:
        size_bytes = os.path.getsize(db_path)
    except OSError:
        size_bytes = 0

    payload = {
        "status": "ok",
        "up": 1,
        "uptime_seconds": int(time.monotonic() - _PROCESS_START),
        "time": datetime.now(timezone.utc).isoformat(),
        "checks": {"app": "ok", "database": "ok"},
        "db": {"path": db_path, "size_bytes": size_bytes},
    }

    try:
        row = get_db().execute(
            """
            SELECT
              (SELECT COUNT(*) FROM servers) AS servers_total,
              (SELECT COUNT(*) FROM servers WHERE enabled = 1) AS servers_enabled,
              (SELECT COUNT(*) FROM user_server_access) AS access_grants,
              (SELECT COUNT(*) FROM audit_log) AS audit_events,
              (SELECT COUNT(*) FROM audit_log
                 WHERE created_at >= datetime('now', '-1 day')) AS audit_events_24h
            """
        ).fetchone()
    except sqlite3.Error as exc:
        current_app.logger.warning("Zabbix health DB error: %s", exc)
        payload["status"] = "error"
        payload["up"] = 0
        payload["checks"]["database"] = "error"
        payload["db"]["error"] = str(exc)
        return jsonify(payload)

    servers_total = row["servers_total"]
    servers_enabled = row["servers_enabled"]
    payload["db"].update(
        {
            "servers_total": servers_total,
            "servers_enabled": servers_enabled,
            "servers_disabled": servers_total - servers_enabled,
            "access_grants": row["access_grants"],
            "audit_events": row["audit_events"],
            "audit_events_24h": row["audit_events_24h"],
        }
    )
    return jsonify(payload)


@control_bp.route("/metrics/<slug>", methods=["GET"])
def metrics_proxy(slug: str):
    # No CF Access JWT required on this path: Cloudflare bypasses SSO for the
    # Zabbix scraper host. Upstream access is still protected by basic auth.
    server = get_server_by_slug(slug)
    if not server:
        log_audit("metrics_denied", details=f"slug={slug}")
        return jsonify({"error": "server_not_found"}), 404

    upstream_url = build_metrics_origin_url(dict(server))
    try:
        resp = requests.get(
            upstream_url,
            auth=metrics_auth(),
            timeout=current_app.config["METRICS_CHECK_TIMEOUT"],
            verify=current_app.config["METRICS_VERIFY_TLS"],
        )
    except requests.RequestException as exc:
        current_app.logger.warning("Metrics proxy failed for %s: %s", upstream_url, exc)
        log_audit("metrics_proxy_error", server_id=server["id"], details=str(exc))
        return jsonify({"error": "upstream_unreachable", "details": str(exc)}), 502

    excluded = {"content-length", "transfer-encoding", "connection"}
    response_headers = [
        (name, value)
        for (name, value) in resp.headers.items()
        if name.lower() not in excluded
    ]
    log_audit("metrics_proxy_request", server_id=server["id"], details=upstream_url)
    return Response(resp.content, status=resp.status_code, headers=response_headers)
