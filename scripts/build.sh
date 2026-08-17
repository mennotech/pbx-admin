#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$repo_root"

engine=${CONTAINER_ENGINE:-podman}

if ! command -v "$engine" >/dev/null 2>&1; then
  echo "$engine is required; set CONTAINER_ENGINE=docker to use Docker instead" >&2
  exit 1
fi

if ! "$engine" info >/dev/null 2>&1; then
  echo "$engine is installed but unavailable; check its service or socket" >&2
  exit 1
fi

exec "$engine" build \
  --file deploy/Containerfile \
  --tag "${IMAGE:-pbx-admin:local}" \
  .
