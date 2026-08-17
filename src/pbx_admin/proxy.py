"""Reverse-proxy logic for forwarding requests to the selected PBX upstream."""

from time import monotonic
from urllib.parse import urljoin

import requests
from flask import Response, current_app, g, jsonify, redirect, request, session, url_for

from . import auth
from .repository import get_server_for_user, log_audit

# Client-supplied headers that must never be forwarded upstream, either because
# they are hop-by-hop or because the proxy sets a trusted value itself
# (preventing a client from spoofing the authenticated identity).
HEADERS_NOT_FORWARDED = {"content-length", "cf-access-jwt-assertion", "x-pbx-admin-user"}

# Upstream response headers we must not pass back verbatim.
RESPONSE_HEADERS_EXCLUDED = {
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
    "x-frame-options",
}


def strip_frame_ancestors(csp_value: str) -> str:
    """Remove any frame-ancestors directive so the same-origin console iframe can render."""
    directives = [d.strip() for d in csp_value.split(";")]
    kept = [d for d in directives if d and not d.lower().startswith("frame-ancestors")]
    return "; ".join(kept)


def filter_request_headers(items) -> dict:
    """Drop hop-by-hop and spoofable headers from an iterable of (name, value)."""
    return {key: value for key, value in items if key.lower() not in HEADERS_NOT_FORWARDED}


def stream_upstream_body(resp):
    try:
        yield from resp.iter_content(chunk_size=64 * 1024)
    finally:
        resp.close()


def proxy_to_selected(path: str):
    identity = auth.get_identity()
    g.identity = identity
    email = identity["email"]

    selected = session.get("selected_server_id")
    if not selected:
        return redirect(url_for("control.control_home"))

    server = get_server_for_user(email, selected)
    if not server:
        session.pop("selected_server_id", None)
        return redirect(url_for("control.control_home"))

    upstream_base = server["upstream_base_url"].rstrip("/") + "/"
    upstream_url = urljoin(upstream_base, path)
    if request.query_string:
        upstream_url = f"{upstream_url}?{request.query_string.decode('utf-8', errors='ignore')}"

    headers = filter_request_headers(request.headers.items())
    headers["Host"] = request.host
    headers["X-PBX-Admin-User"] = email
    headers["X-Forwarded-Proto"] = request.headers.get("X-Forwarded-Proto", request.scheme)
    headers["X-Forwarded-Host"] = request.host

    upstream_started = monotonic()
    try:
        resp = requests.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True,
            timeout=current_app.config["UPSTREAM_TIMEOUT_SECONDS"],
            verify=current_app.config["UPSTREAM_VERIFY_TLS"],
        )
    except requests.RequestException as exc:
        current_app.logger.warning("Upstream request failed for %s: %s", upstream_url, exc)
        log_audit("proxy_error", server_id=selected, details=str(exc))
        return (
            jsonify(
                {
                    "error": "upstream_unreachable",
                    "details": "Unable to reach selected PBX upstream.",
                }
            ),
            502,
        )
    upstream_header_ms = (monotonic() - upstream_started) * 1000

    response_headers = []
    for name, value in resp.raw.headers.items():
        lname = name.lower()
        if lname in RESPONSE_HEADERS_EXCLUDED:
            continue
        if lname == "content-security-policy":
            value = strip_frame_ancestors(value)
            if not value:
                continue
        response_headers.append((name, value))
    response_headers.append(
        ("Server-Timing", f'pbx-upstream-headers;dur={upstream_header_ms:.1f}')
    )

    log_audit("proxy_request", server_id=selected, details=f"{request.method} {request.path}")
    return Response(
        stream_upstream_body(resp),
        status=resp.status_code,
        headers=response_headers,
        direct_passthrough=True,
    )
