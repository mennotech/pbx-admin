from types import SimpleNamespace


class StreamingResponse:
    status_code = 200
    raw = SimpleNamespace(headers={"Content-Type": "text/plain"})

    def __init__(self):
        self.closed = False

    @property
    def content(self):
        raise AssertionError("gateway must not buffer the upstream response")

    def iter_content(self, chunk_size):
        yield b"first"
        yield b"second"

    def close(self):
        self.closed = True


def test_healthz_is_public(client):
    resp = client.get("/-control/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_select_then_console_flow(client, as_user):
    as_user()
    resp = client.post("/-control/select", data={"server_id": "pbx-a"})
    assert resp.status_code == 302

    resp = client.get("/-control/console")
    assert resp.status_code == 200
    assert b"Alpha PBX" in resp.data


def test_select_denied_for_unassigned_server(client, as_user):
    as_user()
    resp = client.post("/-control/select", data={"server_id": "pbx-b"})
    assert resp.status_code == 403


def test_unknown_control_path_returns_404(client, as_user):
    as_user()
    resp = client.get("/-control/does-not-exist")
    assert resp.status_code == 404


def test_gateway_redirects_to_router_without_selection(client, as_user):
    as_user()
    resp = client.get("/some/upstream/path")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/-control/")


def test_gateway_streams_upstream_response(client, as_user, monkeypatch):
    as_user()
    client.post("/-control/select", data={"server_id": "pbx-a"})
    upstream_response = StreamingResponse()
    monkeypatch.setattr(
        "pbx_admin.proxy.requests.request", lambda **kwargs: upstream_response
    )

    response = client.get("/admin/config.php?display=extensions")

    assert response.data == b"firstsecond"
    assert response.headers["Content-Type"] == "text/plain"
    assert "pbx-upstream-headers;dur=" in response.headers["Server-Timing"]
    assert upstream_response.closed is True
