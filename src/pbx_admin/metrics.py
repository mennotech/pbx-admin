"""Upstream metrics URL building, reachability checks, and payload parsing."""

import re
from urllib.parse import urlparse

import requests
from flask import current_app

# Cap the body we parse so a misbehaving upstream cannot exhaust memory.
_MAX_METRICS_BYTES = 1_000_000

_LABEL_RE = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')


def metrics_auth():
    """Basic-auth tuple for upstream metrics requests, or ``None`` when unset."""
    user = current_app.config["METRICS_BASIC_AUTH_USER"]
    if user:
        return (user, current_app.config["METRICS_BASIC_AUTH_PASS"])
    return None


def format_metrics_url(server: dict, template: str) -> str:
    """Render a metrics URL template using fields from ``server`` (pure)."""
    parsed = urlparse(server.get("upstream_base_url", ""))
    host = parsed.hostname or ""
    try:
        return template.format(
            host=host,
            slug=server.get("slug", ""),
            server_id=server.get("id", ""),
        )
    except Exception:  # noqa: BLE001 - fall back to the raw template on bad format
        return template


def build_metrics_public_url(server: dict) -> str:
    return format_metrics_url(server, current_app.config["METRICS_URL_TEMPLATE"])


def build_metrics_origin_url(server: dict) -> str:
    return format_metrics_url(server, current_app.config["METRICS_ORIGIN_URL_TEMPLATE"])


def check_metrics_status(server: dict) -> dict:
    probe_url = build_metrics_origin_url(server)
    public_url = build_metrics_public_url(server)

    if not current_app.config["METRICS_CHECK_ENABLED"]:
        return _status("disabled", public_url, probe_url, code=None, message="disabled")

    try:
        resp = requests.get(
            probe_url,
            auth=metrics_auth(),
            timeout=current_app.config["METRICS_CHECK_TIMEOUT"],
            verify=current_app.config["METRICS_VERIFY_TLS"],
        )
    except requests.RequestException as exc:
        return _status("error", public_url, probe_url, code=None, message=str(exc))

    if resp.status_code == 200:
        status = _status("ok", public_url, probe_url, code=200, message="ok")
        try:
            samples = parse_prometheus_text(resp.text[:_MAX_METRICS_BYTES])
            status["metrics"] = summarize_metrics(samples)
        except Exception:  # noqa: BLE001 - reachable is still useful even if parsing fails
            status["metrics"] = None
        return status
    return _status("error", public_url, probe_url, code=resp.status_code, message=f"HTTP {resp.status_code}")


def _status(state: str, url: str, probe_url: str, *, code, message: str, metrics=None) -> dict:
    return {
        "state": state,
        "code": code,
        "message": message,
        "url": url,
        "probe_url": probe_url,
        "metrics": metrics,
    }


def _parse_labels(labels_str: str) -> dict:
    """Parse a Prometheus label block (without braces) into a dict."""
    labels = {}
    for match in _LABEL_RE.finditer(labels_str):
        value = match.group(2).replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        labels[match.group(1)] = value
    return labels


def parse_prometheus_text(text: str) -> list:
    """Parse Prometheus exposition text into ``(name, labels, value)`` samples.

    Comment/HELP/TYPE lines are skipped, and any malformed sample line is
    ignored rather than raising, so a partial or odd payload still yields
    whatever could be parsed.
    """
    samples = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            if "{" in line:
                name, rest = line.split("{", 1)
                labels_str, value_str = rest.rsplit("}", 1)
                labels = _parse_labels(labels_str)
                value_tokens = value_str.split()
            else:
                tokens = line.split()
                name, labels, value_tokens = tokens[0], {}, tokens[1:]
            if not value_tokens:
                continue
            value = float(value_tokens[0])
        except (ValueError, IndexError):
            continue
        samples.append((name.strip(), labels, value))
    return samples


def _humanize_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def _as_number(value: float):
    return int(value) if float(value).is_integer() else round(value, 2)


def summarize_metrics(samples: list) -> dict:
    """Reduce parsed samples to a small, display-friendly snapshot.

    Metric names are matched defensively against a few candidates so the
    summary keeps working across Asterisk/exporter versions. Anything not
    recognised still counts toward ``total_series``/``metric_names``.
    """
    by_name = {}
    for name, labels, value in samples:
        by_name.setdefault(name, []).append((labels, value))

    summary = {
        "total_series": len(samples),
        "metric_names": len(by_name),
        "version": None,
        "uptime": None,
        "highlights": [],
    }

    for name, series in by_name.items():
        if name.endswith("_properties"):
            for labels, _ in series:
                if labels.get("version"):
                    summary["version"] = labels["version"]
                    break
        if summary["version"]:
            break

    for name, series in by_name.items():
        if name.endswith("uptime_seconds") and series:
            summary["uptime"] = _humanize_duration(series[0][1])
            break

    def total(*candidates):
        for candidate in candidates:
            if candidate in by_name:
                return sum(value for _, value in by_name[candidate])
        return None

    def count_series(*candidates):
        for candidate in candidates:
            if candidate in by_name:
                return len(by_name[candidate])
        return None

    highlight_specs = [
        ("Active channels", total("asterisk_channels_count", "asterisk_channels_state")),
        ("Active calls", total("asterisk_calls_count")),
        ("Calls processed", total("asterisk_calls_sum")),
        ("Active bridges", total("asterisk_bridges_count")),
        ("Endpoints", count_series("asterisk_endpoints_state") or total("asterisk_endpoints_count")),
        ("System threads", total("asterisk_system_threads")),
    ]
    for label, value in highlight_specs:
        if value is not None:
            summary["highlights"].append({"label": label, "value": _as_number(value)})

    return summary
