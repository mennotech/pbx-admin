from pbx_admin import repository


def test_allowed_servers_excludes_disabled_and_unassigned(app):
    with app.test_request_context("/"):
        rows = repository.get_allowed_servers("user@example.com")
    slugs = {row["slug"] for row in rows}
    # pbx-b is not assigned to the user; pbx-off is disabled.
    assert slugs == {"a"}


def test_get_server_for_user_enforces_access(app):
    with app.test_request_context("/"):
        assert repository.get_server_for_user("user@example.com", "pbx-a") is not None
        assert repository.get_server_for_user("user@example.com", "pbx-b") is None


def test_get_server_by_slug_ignores_access_but_honors_enabled(app):
    with app.test_request_context("/"):
        assert repository.get_server_by_slug("b") is not None
        assert repository.get_server_by_slug("off") is None
