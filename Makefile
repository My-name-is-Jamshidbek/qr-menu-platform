# BOSS KAFE — developer entry points.
#
# Every target runs against the development stack in docker-compose.yml unless
# it says otherwise. Production is driven from deploy/deploy.md, not from here:
# a `make deploy` that silently targets the wrong host is how outages happen.
#
# Run `make` with no argument for the list.

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

# Host-reachable addresses for tools run outside the containers (pytest, npm).
HOST_ENV := .env.hostdev

# Backend tooling runs on the host, from the project virtualenv when there is
# one. Prepending it to PATH keeps the recipes readable and still works for a
# developer who activated the venv themselves or installed globally.
VENV_PATH := PATH="$$PWD/.venv/bin:$$PATH"

# Backend management commands run on the host against the containerised
# database, rather than through `compose exec api`: that works whether the API
# is running in a container, running under `manage.py runserver`, or not running
# at all — a migration should not need a healthy web process.
MANAGE := set -a; source $(HOST_ENV); set +a; cd backend && $(VENV_PATH) python manage.py

.PHONY: help up down logs migrate seed import test e2e lint format

help: ## Show this help
	@echo "BOSS KAFE — make targets"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Stack
# -----------------------------------------------------------------------------

up: ## Start the development stack (postgres, redis, minio, api, web)
	$(COMPOSE) up -d --build
	@echo "web  http://localhost:3100"
	@echo "api  http://localhost:8100/api/v1/"
	@echo "docs http://localhost:8100/api/schema/swagger-ui/"

down: ## Stop the development stack (volumes are kept)
	$(COMPOSE) down

logs: ## Follow the logs; pass S=api to follow one service
	$(COMPOSE) logs -f --tail=100 $(S)

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

migrate: ## Apply database migrations
	@$(MANAGE) migrate --noinput

seed: ## Load the demo menu (ARGS="--fresh --no-images" to wipe and skip uploads)
	@$(MANAGE) seed_demo $(ARGS)

import: ## Import the legacy Firestore menu (ARGS="--dry-run" to validate only)
	@$(MANAGE) import_firestore $(ARGS)

# -----------------------------------------------------------------------------
# Quality
# -----------------------------------------------------------------------------

test: ## Run the backend test suite with coverage
	set -a; source $(HOST_ENV); set +a; \
	cd backend && $(VENV_PATH) pytest --cov=apps --cov-report=term-missing $(ARGS)

e2e: ## Smoke-test the running stack over HTTP (BASE_URL/API_URL to retarget)
	@bash deploy/smoke.sh

lint: ## Lint and typecheck both sides
	cd backend && $(VENV_PATH) ruff check . && $(VENV_PATH) ruff format --check .
	cd frontend && npm run lint && npm run typecheck

format: ## Auto-fix formatting and import order
	cd backend && $(VENV_PATH) ruff check --fix . && $(VENV_PATH) ruff format .
	cd frontend && npm run lint -- --fix
