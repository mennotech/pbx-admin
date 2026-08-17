from pbx_admin import proxy


class StreamingResponse:
    status_code = 200

    def __init__(self):
        self.closed = False

    @property
    def content(self):
        raise AssertionError("streaming must not access the buffered content property")

    def iter_content(self, chunk_size):
        assert chunk_size == 64 * 1024
        yield b"first"
        yield b"second"

    def close(self):
        self.closed = True


def test_filter_request_headers_strips_spoofable_and_hop_by_hop():
    items = [
        ("Content-Length", "5"),
        ("X-Pbx-Admin-User", "evil@example.com"),
        ("Cf-Access-Jwt-Assertion", "token"),
        ("Accept", "text/html"),
    ]
    out = proxy.filter_request_headers(items)
    lowered = {k.lower() for k in out}
    assert "accept" in lowered
    assert "content-length" not in lowered
    assert "x-pbx-admin-user" not in lowered
    assert "cf-access-jwt-assertion" not in lowered


def test_strip_frame_ancestors_removes_only_that_directive():
    csp = "default-src 'self'; frame-ancestors 'none'; script-src 'self'"
    out = proxy.strip_frame_ancestors(csp)
    assert "frame-ancestors" not in out
    assert "default-src 'self'" in out
    assert "script-src 'self'" in out


def test_stream_upstream_body_yields_chunks_and_closes_response():
    response = StreamingResponse()

    assert list(proxy.stream_upstream_body(response)) == [b"first", b"second"]
    assert response.closed is True
