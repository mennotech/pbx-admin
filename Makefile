.DEFAULT_GOAL := help

UV ?= uv
PYTHON_VERSION ?= 3.12
TEST_ARGS ?=
IMAGE ?= pbx-admin:local
CONTAINER_ENGINE ?= podman
FLY_CONFIG ?= deploy/fly.toml
RELEASE_TAG ?=

.PHONY: help setup sync lock test check run build release-check release-build fly-config fly-validate deploy

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install Python and development dependencies with uv
	$(UV) python install $(PYTHON_VERSION)
	$(UV) sync --extra dev

sync: ## Synchronize the development environment from the lockfile
	$(UV) sync --extra dev --locked

lock: ## Update uv.lock from pyproject.toml
	$(UV) lock

test: ## Run tests; pass TEST_ARGS="..." to narrow the run
	$(UV) run pytest $(TEST_ARGS)

check: sync ## Run all required local checks
	$(UV) run pytest

run: ## Run the local Flask development server
	PORT="$(or $(PORT),8080)" ./scripts/run.sh

build: ## Build the production container image
	CONTAINER_ENGINE="$(CONTAINER_ENGINE)" IMAGE="$(IMAGE)" ./scripts/build.sh

release-check: ## Validate RELEASE_TAG, metadata, changelog, lockfile, and tests
	@test -n "$(RELEASE_TAG)" || { echo "RELEASE_TAG is required" >&2; exit 1; }
	$(UV) run python scripts/check_release.py "$(RELEASE_TAG)"
	$(MAKE) check

release-build: release-check ## Build the versioned production image for RELEASE_TAG
	$(MAKE) build IMAGE="pbx-admin:$(patsubst v%,%,$(RELEASE_TAG))"

fly-config: ## Create ignored deploy/fly.toml from the example
	@if test -f "$(FLY_CONFIG)"; then \
		echo "$(FLY_CONFIG) already exists"; \
	else \
		cp deploy/fly.toml.example "$(FLY_CONFIG)"; \
		echo "Created $(FLY_CONFIG); set its app and region before deploying"; \
	fi

fly-validate: ## Validate the local Fly configuration
	@command -v fly >/dev/null 2>&1 || { echo "flyctl is required" >&2; exit 1; }
	@test -f "$(FLY_CONFIG)" || { echo "Missing $(FLY_CONFIG); run 'make fly-config'" >&2; exit 1; }
	fly config validate --config "$(FLY_CONFIG)"

deploy: check fly-validate ## Test and deploy the app with Fly.io
	FLY_CONFIG="$(FLY_CONFIG)" ./scripts/deploy.sh
