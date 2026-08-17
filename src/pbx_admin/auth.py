"""Cloudflare Access JWT verification and the ``require_identity`` decorator."""

import json
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import requests
from flask import current_app, g, jsonify, request

# Per-process JWKS cache. Cheap to hold in memory; refreshed every 10 minutes.
_JWKS_CACHE = {"expires": datetime.now(timezone.utc), "jwks": None}


def reset_jwks_cache() -> None:
    """Clear the cached JWKS (used by tests)."""
    _JWKS_CACHE["jwks"] = None
    _JWKS_CACHE["expires"] = datetime.now(timezone.utc)


def fetch_jwks() -> dict:
    now = datetime.now(timezone.utc)
    if _JWKS_CACHE["jwks"] and now < _JWKS_CACHE["expires"]:
        return _JWKS_CACHE["jwks"]

    team = current_app.config["CF_TEAM_DOMAIN"]
    if not team:
        raise RuntimeError("CF_ACCESS_TEAM_DOMAIN is required")

    url = f"https://{team}/cdn-cgi/access/certs"
    resp = requests.get(url, timeout=current_app.config["UPSTREAM_TIMEOUT_SECONDS"])
    resp.raise_for_status()
    jwks = resp.json()

    _JWKS_CACHE["jwks"] = jwks
    _JWKS_CACHE["expires"] = now + timedelta(minutes=10)
    return jwks


def verify_access_jwt(token: str) -> dict:
    jwks = fetch_jwks()
    unverified = jwt.get_unverified_header(token)
    key = None
    for candidate in jwks.get("keys", []):
        if candidate.get("kid") == unverified.get("kid"):
            key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(candidate))
            break

    if not key:
        raise ValueError("Unable to find matching JWT key")

    team = current_app.config["CF_TEAM_DOMAIN"]
    kwargs = {
        "algorithms": ["RS256"],
        "issuer": f"https://{team}",
        "options": {"require": ["exp", "iat"]},
    }
    audience = current_app.config["CF_AUDIENCE"]
    if audience:
        kwargs["audience"] = audience

    return jwt.decode(token, key=key, **kwargs)


def get_identity() -> dict:
    header = current_app.config["JWT_HEADER_NAME"]
    token = request.headers.get(header)
    if not token:
        raise PermissionError(f"Missing {header} header")
    payload = verify_access_jwt(token)

    email = payload.get("email") or payload.get("sub")
    if not email:
        raise PermissionError("JWT payload does not contain email/sub")
    return {"email": email, "payload": payload}


def require_identity(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            g.identity = get_identity()
        except Exception as exc:  # noqa: BLE001 - surfaced to caller as 401
            return jsonify({"error": "unauthorized", "details": str(exc)}), 401
        return func(*args, **kwargs)

    return wrapper
