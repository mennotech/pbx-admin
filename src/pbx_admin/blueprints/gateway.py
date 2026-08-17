"""Gateway blueprint: catch-all reverse proxy to the selected PBX upstream."""

from flask import Blueprint, current_app, jsonify, request

from ..proxy import proxy_to_selected

gateway_bp = Blueprint("gateway", __name__)

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


@gateway_bp.route("/", defaults={"path": ""}, methods=_METHODS)
@gateway_bp.route("/<path:path>", methods=_METHODS)
def catch_all(path: str):
    prefix = current_app.config["CONTROL_PREFIX"]
    if request.path.startswith(f"{prefix}/"):
        return jsonify({"error": "not_found"}), 404

    try:
        return proxy_to_selected(path)
    except PermissionError as exc:
        return jsonify({"error": "unauthorized", "details": str(exc)}), 401
