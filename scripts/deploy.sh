#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$repo_root"

config=${FLY_CONFIG:-deploy/fly.toml}

if ! command -v fly >/dev/null 2>&1; then
  echo "flyctl is required; see https://fly.io/docs/flyctl/install/" >&2
  exit 1
fi

if [ ! -f "$config" ]; then
  echo "Missing $config; run 'make fly-config'" >&2
  exit 1
fi

exec fly deploy --config "$config"
