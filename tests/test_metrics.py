"""Tests for Prometheus payload parsing and the status page metric details."""

import pytest

from pbx_admin import metrics

SAMPLE = """\
# HELP asterisk_core_properties Asterisk instance properties
# TYPE asterisk_core_properties gauge
asterisk_core_properties{version="20.5.0"} 1
# HELP asterisk_core_uptime_seconds Uptime
# TYPE asterisk_core_uptime_seconds counter
asterisk_core_uptime_seconds 93780
asterisk_channels_count 3
asterisk_calls_count 2
asterisk_calls_sum 145
asterisk_bridges_count 1
asterisk_endpoints_state{endpoint="1001"} 2
asterisk_endpoints_state{endpoint="1002"} 0
asterisk_endpoints_state{endpoint="1003"} 2
asterisk_system_threads 42
# a trailing comment
garbage line without value
"""


def test_parse_prometheus_text_extracts_samples_and_labels():
    samples = metrics.parse_prometheus_text(SAMPLE)
    names = [name for name, _, _ in samples]
    assert "asterisk_channels_count" in names
    # Comment lines and malformed lines are skipped.
    assert "garbage" not in names
    props = [s for s in samples if s[0] == "asterisk_core_properties"][0]
    assert props[1]["version"] == "20.5.0"
    assert props[2] == 1.0


def test_summarize_metrics_builds_snapshot():
    summary = metrics.summarize_metrics(metrics.parse_prometheus_text(SAMPLE))
    assert summary["version"] == "20.5.0"
    assert summary["uptime"] == "1d 2h 3m"  # 93780s
    assert summary["metric_names"] == 8
    assert summary["total_series"] == 10

    highlights = {h["label"]: h["value"] for h in summary["highlights"]}
    assert highlights["Active channels"] == 3
    assert highlights["Active calls"] == 2
    assert highlights["Calls processed"] == 145
    assert highlights["Active bridges"] == 1
    assert highlights["Endpoints"] == 3  # three endpoint series
    assert highlights["System threads"] == 42


def test_summarize_metrics_handles_empty_payload():
    summary = metrics.summarize_metrics(metrics.parse_prometheus_text(""))
    assert summary["total_series"] == 0
    assert summary["highlights"] == []
    assert summary["version"] is None


class _FakeResponse:
    status_code = 200
    text = SAMPLE


def test_status_page_shows_metric_details(client, as_user, monkeypatch):
    # Enable the check for this request and stub the upstream fetch.
    client.application.config["METRICS_CHECK_ENABLED"] = True
    monkeypatch.setattr(metrics.requests, "get", lambda *a, **k: _FakeResponse())

    as_user()
    resp = client.get("/-control/status")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "reachable" in body
    assert "20.5.0" in body  # Asterisk version
    assert "1d 2h 3m" in body  # uptime
    assert "Active channels" in body
    assert "Calls processed" in body
