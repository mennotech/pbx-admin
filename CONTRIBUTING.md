# Contributing

Thank you for considering a contribution to PBX Admin.

## Before You Start

- Search existing issues and pull requests before opening a new one.
- Use an issue to discuss substantial features, architecture changes, or new dependencies before implementation.
- Do not use public issues for security vulnerabilities. Follow [SECURITY.md](SECURITY.md) instead.
- Never include credentials, access tokens, private hostnames, real user mappings, or production database contents in issues, tests, logs, or commits.

## Development Setup

Install [uv](https://docs.astral.sh/uv/) and GNU Make, then run:

```bash
make setup
make check
```

Python 3.12 is pinned in `.python-version`. `make setup` creates and synchronizes the local `.venv` from `pyproject.toml` and `uv.lock`.

Podman is the default container engine:

```bash
make build
```

Docker is also supported:

```bash
make build CONTAINER_ENGINE=docker
```

Run `make help` to see the complete command interface.

## Making Changes

- Keep changes focused and consistent with the existing Flask application-factory and blueprint patterns.
- Add or update focused tests for every behavior change.
- Keep network tests deterministic by mocking external boundaries.
- Preserve authentication, authorization, upstream allowlisting, TLS, timeout, redirect, cookie, header-filtering, and streaming behavior when changing gateway code.
- Update documentation and deployment examples when commands, paths, configuration, or runtime behavior change.
- Add dependencies to `pyproject.toml`, then run `make lock`. Commit the resulting `uv.lock` change.

See [AGENTS.md](AGENTS.md) for detailed repository architecture and engineering conventions.

## Testing

Run the narrowest relevant test while iterating:

```bash
make test TEST_ARGS=tests/test_proxy.py
```

Before submitting a pull request, run:

```bash
make check
make build
```

If a check cannot run in your environment, explain that clearly in the pull request.

## Pull Requests

- Use a descriptive title and explain the problem and solution.
- Link related issues.
- Describe security and deployment implications when relevant.
- Include test evidence and screenshots for visible UI changes.
- Keep unrelated refactors and dependency upgrades out of the pull request.
- Ensure commits contain no secrets or private operational data.

By contributing, you agree that your contribution will be licensed under the repository's [MIT License](LICENSE).

Maintainers should follow [RELEASING.md](RELEASING.md) when preparing tags and release artifacts.
