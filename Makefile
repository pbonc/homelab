SHELL := /usr/bin/env bash
.RECIPEPREFIX := >

# CI portability note:
# GitHub Actions, GitLab CI, and Jenkins should call these same Make targets.

.PHONY: help doctor status lint test bootstrap docker-up docker-down

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
