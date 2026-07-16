SHELL := /usr/bin/env bash
.RECIPEPREFIX := >

# CI portability note:
# GitHub Actions, GitLab CI, and Jenkins should call these same Make targets.

.PHONY: help doctor status lint test telemetry-test telemetry-run telemetry-secrets telemetry-config security-test security-secrets security-config bootstrap docker-up docker-down homepage-validate homepage-deploy homepage-verify homepage-rollback

help: ## Show available targets
>@awk 'BEGIN {FS = ":.*##"; printf "\nAvailable targets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

doctor: ## Validate local environment baseline
>@python3 -m labctl doctor

status: ## Show homelab repository status summary
>@python3 -m labctl status

lint: ## Validate repository and Homepage configuration
>@python3 scripts/validate_homepage.py

test: ## Run repository validation checks
>@python3 scripts/validate_homepage.py
>@python3 -m unittest discover -s tests -v

telemetry-test: ## Run telemetry collector tests (requires development dependencies)
>@python3 -c "import fastapi, httpx"
>@python3 -m unittest discover -s tests -p "test_ecowitt.py" -v
>@python3 -m unittest discover -s tests -p "test_telemetry_*.py" -v

telemetry-run: ## Run the telemetry collector locally on port 8000
>@cd docker/telemetry-collector && python3 -m uvicorn telemetry_collector.main:app --host 127.0.0.1 --port 8000

telemetry-secrets: ## Create ignored telemetry runtime configuration and secrets
>@python3 scripts/telemetry_secrets.py

telemetry-config: ## Validate the resolved telemetry Compose configuration
>@docker compose --env-file docker/telemetry/.env --file docker/telemetry/compose.yaml config --quiet

security-test: ## Run security status adapter tests
>@python3 -m unittest discover -s tests -p "test_security_status.py" -v

security-secrets: ## Create ignored Aikido runtime configuration and credentials
>@python3 scripts/security_secrets.py

security-config: ## Validate the resolved security status Compose configuration
>@docker compose --env-file docker/security-status/.env --file docker/security-status/compose.yaml config --quiet

homepage-validate: ## Validate Homepage source and Compose configuration
>@python3 -u scripts/homepage_release.py validate

homepage-deploy: ## Deploy and verify an immutable Homepage release
>@python3 -u scripts/homepage_release.py deploy

homepage-verify: ## Verify the active Homepage release
>@python3 -u scripts/homepage_release.py verify

homepage-rollback: ## Restore and verify the last-known-good Homepage release
>@python3 -u scripts/homepage_release.py rollback

bootstrap: ## Bootstrap local prerequisites (placeholder, no installs)
>@echo "[bootstrap] Define bootstrap steps in scripts/bootstrap.sh when ready."

docker-up: ## Start Docker Compose stack (when defined)
>@if command -v docker >/dev/null 2>&1; then \
>  docker compose up -d; \
>else \
>  echo "[docker-up] Docker is not installed yet."; \
>fi

docker-down: ## Stop Docker Compose stack (when defined)
>@if command -v docker >/dev/null 2>&1; then \
>  docker compose down; \
>else \
>  echo "[docker-down] Docker is not installed yet."; \
>fi
