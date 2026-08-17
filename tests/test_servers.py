def test_servers_page_lists_all_servers(client, as_user):
    as_user()
    resp = client.get("/-control/servers")
    assert resp.status_code == 200
    # Server manager shows every server, including disabled and unassigned ones.
    assert b"Alpha PBX" in resp.data
    assert b"Beta PBX" in resp.data
    assert b"Disabled PBX" in resp.data


def test_add_server_grants_creator_access(client, as_user):
    as_user()
    resp = client.post(
        "/-control/servers",
        data={
            "display_name": "Gamma PBX",
            "slug": "gamma",
            "upstream_base_url": "https://gamma.internal",
        },
    )
    assert resp.status_code == 302

    # Visible in the server manager...
    assert b"Gamma PBX" in client.get("/-control/servers").data
    # ...and on the creator's dashboard, because access was granted.
    assert b"Gamma PBX" in client.get("/-control/").data


def test_add_server_rejects_invalid_slug(client, as_user):
    as_user()
    resp = client.post(
        "/-control/servers",
        data={
            "display_name": "Bad One",
            "slug": "Bad Slug!",
            "upstream_base_url": "https://x.internal",
        },
        follow_redirects=True,
    )
    assert b"Slug must be" in resp.data
    assert b"Bad One" not in resp.data


def test_add_server_rejects_bad_upstream(client, as_user):
    as_user()
    resp = client.post(
        "/-control/servers",
        data={"display_name": "No Scheme", "slug": "noscheme", "upstream_base_url": "ftp://x"},
        follow_redirects=True,
    )
    assert b"Upstream base URL must start with" in resp.data


def test_delete_server_removes_it(client, as_user):
    as_user()
    resp = client.post("/-control/servers/pbx-a/delete")
    assert resp.status_code == 302
    assert b"Alpha PBX" not in client.get("/-control/servers").data


def test_status_page_shows_snapshot(client, as_user):
    as_user()
    resp = client.get("/-control/status")
    assert resp.status_code == 200
    assert b"Alpha PBX" in resp.data
    # Metrics checks are disabled in tests, so every server reads as "disabled".
    assert b"disabled" in resp.data
