# pbx-admin

[![CI](https://github.com/mennotech/pbx-admin/actions/workflows/ci.yml/badge.svg)](https://github.com/mennotech/pbx-admin/actions/workflows/ci.yml)

Authenticated PBX admin router for Fly.io private networks.

This service verifies Cloudflare Access JWTs, exposes a control UI at /-control/,
stores PBX registry/access policy in SQLite, and proxies all non-control paths to
the selected PBX upstream.

## Files

- src/pbx_admin/: application package (app factory + modules)
  - config.py: environment-driven settings
  - db.py: SQLite access, schema init, and the `init-db` CLI command
  - auth.py: Cloudflare Access JWT verification, `require_identity`
  - repository.py: all SQL (servers, access control, audit log)
  - metrics.py: upstream metrics URL building and reachability checks
  - proxy.py: reverse-proxy engine
  - blueprints/control.py: control UI + health/metrics routes (under /-control/)
  - blueprints/gateway.py: catch-all reverse proxy
  - templates/: Jinja templates (base/control/console)
- tests/: pytest suite
- resources/sql/: SQLite schema and example seed data
- deploy/: container, WSGI, startup, and Fly.io configuration files
- monitoring/zabbix/: Zabbix integration template
- pyproject.toml and uv.lock: package metadata and locked dependencies

## Prerequisites

- GNU Make and uv for local development
- Podman for local container builds, or Docker via `CONTAINER_ENGINE=docker`
- Fly app created in this directory
- Cloudflare Zero Trust Access app configured for admin hostname
- Cloudflare Tunnel token for this service

## Required secrets

Set these with fly secrets set:

- SESSION_SECRET: strong random string for Flask session signing
- CF_ACCESS_TEAM_DOMAIN: yourteam.cloudflareaccess.com
- CF_ACCESS_AUDIENCE: Access app audience (aud claim)
- CLOUDFLARED_TOKEN: token from Cloudflare Tunnel

Example:

```bash
fly secrets set \
  SESSION_SECRET="replace-with-long-random-value" \
  CF_ACCESS_TEAM_DOMAIN="yourteam.cloudflareaccess.com" \
  CF_ACCESS_AUDIENCE="your-access-audience" \
  CLOUDFLARED_TOKEN="your-cloudflared-token"
```

## Optional env values

- DB_AUTO_SEED (default: false)
- UPSTREAM_TIMEOUT_SECONDS (default: 45)
- UPSTREAM_VERIFY_TLS (default: false)
- METRICS_CHECK_ENABLED (default: true)
- METRICS_CHECK_TIMEOUT_SECONDS (default: 5)
- METRICS_VERIFY_TLS (default: false)
- METRICS_URL_TEMPLATE (default: https://{host}:8089/metrics)
- METRICS_ORIGIN_URL_TEMPLATE (default: https://{host}:8089/metrics)
- METRICS_BASIC_AUTH_USER (default: empty)
- METRICS_BASIC_AUTH_PASS (default: empty)

The control page shows mini server reachability for each PBX by probing
METRICS_ORIGIN_URL_TEMPLATE and displays METRICS_URL_TEMPLATE as the
operator-facing check URL. Supported placeholders are:

- {host} from upstream_base_url hostname (for example pbx-alpha.internal)
- {slug} from servers.slug (for example kcpa)
- {server_id} from servers.id (for example pbx-kcpa)

Example for Cloudflare path routing:

```bash
fly secrets set \
  METRICS_URL_TEMPLATE="https://monitoring.example.com/-control/metrics/{slug}" \
  METRICS_ORIGIN_URL_TEMPLATE="https://{host}:8089/metrics" \
  METRICS_BASIC_AUTH_USER="monitoring-user" \
  METRICS_BASIC_AUTH_PASS="replace-with-a-secret"
```

The app also exposes a direct route at /-control/metrics/{slug} that proxies
to METRICS_ORIGIN_URL_TEMPLATE for that server slug.

UPSTREAM_VERIFY_TLS=false is the safe default for Fly private .internal hostnames,
because PBX certificates usually do not include those names.

## Cloudflare Tunnel wiring

In Cloudflare Zero Trust:

1. Create tunnel (or reuse one).
2. Add public hostname, for example pbx-admin.example.com.
3. Service type HTTP, URL http://127.0.0.1:8080.
4. Protect the hostname with Cloudflare Access policy.

This container runs cloudflared when CLOUDFLARED_TOKEN is set.

## Configure PBX registry

Copy and edit `resources/sql/seed.sql` before first deploy:

- Set upstream_base_url values to your Fly private DNS targets.
- Set user_server_access emails to your Access identities.

By default `DB_AUTO_SEED=false` for safety. To seed once:

```bash
fly secrets set DB_AUTO_SEED=true
fly deploy
fly secrets set DB_AUTO_SEED=false
```

## Deploy on Fly

1. Copy `deploy/fly.toml.example` to `deploy/fly.toml` and set the app name.
2. Create volume.
3. Deploy.

```bash
cp deploy/fly.toml.example deploy/fly.toml
fly volumes create pbx_admin_data --region yyz --size 1 --config deploy/fly.toml
make deploy
```

## Validate

```bash
fly status
fly logs --no-tail | tail -n 120
fly ssh console -C "python -c \"import sqlite3; db=sqlite3.connect('/data/pbx_admin.db'); print(db.execute('select user_email, server_id from user_server_access order by 1,2').fetchall())\""
```

## Local run (without cloudflared)

```bash
make setup
export SESSION_SECRET="change-me"
export CF_ACCESS_TEAM_DOMAIN="yourteam.cloudflareaccess.com"
export CF_ACCESS_AUDIENCE="your-aud-tag"
make run
```

Open http://localhost:8080/-control/. Run tests with `make test` and build the
container with `make build`. Docker users can run
`make build CONTAINER_ENGINE=docker`.

## Notes

- Keep SIP/RTP direct on PBX apps; this service is for web admin routing only.
- Use only allowlisted upstreams from SQLite (never user-supplied URLs).
- Consider restricting PBX HTTP/HTTPS to internal proxy sources after cutover.

## Community

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes.
- Use [SUPPORT.md](SUPPORT.md) to choose the appropriate support channel and sanitize diagnostic data.
- Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).
- Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- User-facing changes are recorded in [CHANGELOG.md](CHANGELOG.md).
- Version conventions and maintainer release steps are in [RELEASING.md](RELEASING.md).

## License

PBX Admin is available under the [MIT License](LICENSE).
