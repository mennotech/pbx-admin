"""Tests for the unauthenticated /-control/zabbix health + DB stats endpoint."""


def test_zabbix_endpoint_needs_no_auth(client):
    # Unlike the control UI, the scraper endpoint requires no CF Access identity.
    resp = client.get("/-control/zabbix")
    assert resp.status_code == 200
    assert resp.is_json


def test_zabbix_reports_db_statistics(client):
    data = client.get("/-control/zabbix").get_json()
    assert data["status"] == "ok"
    assert data["up"] == 1
    assert data["uptime_seconds"] >= 0
    assert data["checks"] == {"app": "ok", "database": "ok"}

    db = data["db"]
    # Seed: three servers (two enabled, one disabled).
    assert db["servers_total"] == 3
    assert db["servers_enabled"] == 2
    assert db["servers_disabled"] == 1
    assert db["access_grants"] == 2
    assert db["size_bytes"] > 0
    assert "audit_events" in db
    assert "audit_events_24h" in db


def test_zabbix_counts_reflect_changes(client, as_user):
    as_user()
    client.post(
        "/-control/servers",
        data={
            "display_name": "Gamma PBX",
            "slug": "gamma",
            "upstream_base_url": "https://gamma.internal",
        },
    )
    db = client.get("/-control/zabbix").get_json()["db"]
    assert db["servers_total"] == 4
    assert db["servers_enabled"] == 3
