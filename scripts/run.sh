#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$repo_root"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required; see https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

exec uv run flask --app deploy.wsgi run \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-8080}"
