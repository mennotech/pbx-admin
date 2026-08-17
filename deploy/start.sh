#!/bin/sh
set -eu

if [ -z "${SESSION_SECRET:-}" ]; then
  echo "SESSION_SECRET is required"
  exit 1
fi

if [ -z "${CF_ACCESS_TEAM_DOMAIN:-}" ]; then
  echo "CF_ACCESS_TEAM_DOMAIN is required"
  exit 1
fi

flask --app wsgi init-db

if [ -n "${CLOUDFLARED_TOKEN:-}" ]; then
  cloudflared tunnel --no-autoupdate run --token "$CLOUDFLARED_TOKEN" &
  echo "Started cloudflared tunnel"
else
  echo "CLOUDFLARED_TOKEN is not set; cloudflared will not start"
fi

exec gunicorn \
  --workers "${GUNICORN_WORKERS:-2}" \
  --worker-class gthread \
  --threads "${GUNICORN_THREADS:-4}" \
  --bind 0.0.0.0:"${PORT:-8080}" \
  wsgi:app
