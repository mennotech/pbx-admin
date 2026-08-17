# PBX Admin Agent Guidelines

## Project Layout

- `src/pbx_admin/` is the Flask application package. Keep HTTP routing in `src/pbx_admin/blueprints/`, persistence in `repository.py`, database lifecycle code in `db.py`, and upstream proxy behavior in `proxy.py`.
- `src/pbx_admin/templates/` contains Jinja templates shared by the control UI.
- `resources/sql/` contains the SQLite schema and optional starter data. Local runtime databases belong in the ignored `instance/` directory.
- `deploy/` contains deployment-only files: the container build, Fly.io configuration, startup script, and WSGI entry point.
- `monitoring/` contains monitoring-system integrations such as the Zabbix template.
- `tests/` contains the pytest suite. Add or update focused tests for every behavior change.
- Keep the repository root limited to project documentation, dependency and tool configuration, and the primary source, test, data, and deployment directories.

## Development Workflow

1. Install uv, then run `make setup` to install Python and synchronize `.venv` from `pyproject.toml` and `uv.lock`.
2. Run the full suite with `make test`.
3. During iteration, run the narrowest relevant test first, for example `make test TEST_ARGS=tests/test_proxy.py`.
4. Before finishing, run `make check`; report any check that could not run or any unrelated existing failure.

## Python Conventions

- Support the Python version declared by the container image unless the project explicitly changes it.
- Follow the existing application-factory and Flask blueprint patterns.
- Use package-relative imports within `src/pbx_admin/` and absolute imports from `pbx_admin` in tests and deployment entry points.
- Add type annotations where they clarify public functions and non-obvious data structures; do not add annotations mechanically to untouched code.
- Keep changes focused. Do not combine feature work with unrelated renames, formatting, or dependency upgrades.
- Prefer small functions with explicit inputs over hidden request or application context dependencies, except where Flask APIs require context.

## Data and Security

- Treat Cloudflare Access identity and server authorization checks as security boundaries. Never bypass them outside tests.
- Proxy only to server URLs loaded from the repository layer. Never construct an upstream from untrusted request input.
- Preserve upstream timeout, TLS verification, header filtering, cookie, redirect, and streaming behavior when changing proxy code.
- Use parameterized SQL for values. Put SQL access in `src/pbx_admin/repository.py` unless it is schema or database lifecycle logic.
- Make schema changes idempotent and compatible with existing SQLite databases. Do not edit production data or commit database files.
- Never commit secrets, access tokens, private hostnames, user mappings, or real credentials. Use environment variables and clearly fake examples.

## Tests and Documentation

- Reuse fixtures from `tests/conftest.py`; keep tests deterministic and independent of live Cloudflare, Fly.io, PBX, or Zabbix services.
- Mock network boundaries, not the business logic under test.
- Cover authorization failures and malformed upstream responses as well as happy paths when changing gateway behavior.
- Update `README.md`, deployment paths, and commands whenever files or runtime entry points move.
- When changing environment configuration, update the README and deployment configuration together.

## Deployment

- Container builds are expected to run from the repository root with `deploy/Containerfile` as the Dockerfile.
- Use `make build` for local images. Podman is the default; set `CONTAINER_ENGINE=docker` to use Docker.
- Keep `deploy/fly.toml.example`, `deploy/Containerfile`, `deploy/start.sh`, and `deploy/wsgi.py` consistent about build context and runtime paths.
- Treat `deploy/fly.toml` as local deployment configuration; keep it ignored and update the committed example when shared settings change.
- Follow `RELEASING.md` for version changes and releases. Keep `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, Git tags, and container tags consistent.
- Do not deploy, modify Fly.io secrets, or mutate remote infrastructure unless the user explicitly requests it.
