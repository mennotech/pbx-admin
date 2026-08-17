def test_control_requires_identity_without_token(client):
    resp = client.get("/-control/")
    assert resp.status_code == 401


def test_control_home_renders_only_allowed_servers(client, as_user):
    as_user()
    resp = client.get("/-control/")
    assert resp.status_code == 200
    assert b"Alpha PBX" in resp.data
    assert b"Beta PBX" not in resp.data


def test_metrics_url_helpers_are_pure():
    from pbx_admin import metrics

    server = {"upstream_base_url": "https://alpha.internal", "slug": "a", "id": "pbx-a"}
    assert metrics.format_metrics_url(server, "https://{host}:8089/metrics") == (
        "https://alpha.internal:8089/metrics"
    )
    # Unknown placeholders fall back to the raw template rather than raising.
    assert metrics.format_metrics_url(server, "https://{bogus}") == "https://{bogus}"
