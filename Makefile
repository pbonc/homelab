SHELL := /usr/bin/env bash
.RECIPEPREFIX := >

# CI portability note:
# GitHub Actions, GitLab CI, and Jenkins should call these same Make targets.

.PHONY: help doctor status lint test telemetry-test telemetry-run telemetry-secrets telemetry-config security-test security-secrets security-config observability-config observability-up observability-down alertmanager-test study-test study-config study-up study-down network-inventory-test network-inventory-config network-inventory-up network-inventory-down architecture-map-test architecture-map-config architecture-map-up architecture-map-down ntfy-test ntfy-secrets ntfy-config ntfy-up ntfy-down ntfy-test-publish purple-range-portal-test purple-range-portal-config purple-range-portal-up purple-range-portal-down purple-range-test purple-range-config purple-range-up purple-range-down purple-range-shell purple-range-verify purple-range-alert-test purple-range-reset quiz-scenario quiz-range-render quiz-app-test quiz-app-config quiz-decoy-test quiz-decoy-config quiz-attacker-test quiz-attacker-config trailhead-test trailhead-config ansible-inventory ansible-ping ansible-check ansible-bootstrap-check ansible-bootstrap ansible-piaware-observability-check ansible-piaware-observability ansible-vault-create ansible-vault-edit ansible-vault-view rebuild-syntax rebuild-check rebuild-apply rebuild-stage-validate backup-init backup-run backup-check backup-snapshots backup-restore-test backup-prune bootstrap docker-up docker-down homepage-validate homepage-deploy homepage-verify homepage-rollback

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

observability-config: ## Validate the Prometheus and Node Exporter Compose configuration
>@docker compose --file docker/observability/compose.yaml config --quiet
>@docker compose --file docker/observability/compose.yaml run --rm --no-deps --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
>@docker compose --file docker/observability/compose.yaml run --rm --no-deps --entrypoint amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
>@docker compose --file docker/observability/compose.yaml run --rm --no-deps loki -verify-config=true -config.file=/etc/loki/config.yml
>@docker compose --file docker/observability/compose.yaml run --rm --no-deps alloy validate /etc/alloy/config.alloy

observability-up: ## Start Prometheus and Node Exporter
>@docker compose --file docker/observability/compose.yaml up --detach

observability-down: ## Stop Prometheus and Node Exporter without deleting metrics
>@docker compose --file docker/observability/compose.yaml down

alertmanager-test: ## Send a synthetic firing and resolved alert through ntfy
>@bash scripts/alertmanager_test.sh

study-test: ## Validate Study Deck content and progress behavior
>@python3 -m unittest discover -s tests -p "test_study_deck.py" -v

study-config: ## Validate the Study Deck Compose configuration
>@docker compose --file docker/study-deck/compose.yaml config --quiet

study-up: ## Build and start the Homelab Study Deck
>@docker compose --file docker/study-deck/compose.yaml up --detach --build

study-down: ## Stop the Study Deck without deleting progress
>@docker compose --file docker/study-deck/compose.yaml down

network-inventory-test: ## Validate network inventory identity and confirmation behavior
>@python3 -m unittest discover -s tests -p "test_network_inventory.py" -v

network-inventory-config: ## Validate the network inventory Compose configuration
>@docker compose --file docker/network-inventory/compose.yaml config --quiet

network-inventory-up: ## Build and start the network inventory API
>@docker compose --file docker/network-inventory/compose.yaml up --detach --build

network-inventory-down: ## Stop the network inventory API without deleting state
>@docker compose --file docker/network-inventory/compose.yaml down

architecture-map-test: ## Validate the versioned architecture model and site
>@python3 -m unittest discover -s tests -p "test_architecture_map.py" -v

architecture-map-config: ## Validate the Architecture Map Compose configuration
>@docker compose --file docker/architecture-map/compose.yaml config --quiet

architecture-map-up: ## Build and start the interactive Architecture Map
>@docker compose --file docker/architecture-map/compose.yaml up --detach --build

architecture-map-down: ## Stop the Architecture Map
>@docker compose --file docker/architecture-map/compose.yaml down

ntfy-test: ## Validate ntfy deployment policy
>@python3 -m unittest discover -s tests -p "test_ntfy.py" -v

ntfy-secrets: ## Create ignored ntfy users, hashes, and passwords
>@python3 scripts/ntfy_secrets.py

ntfy-config: ## Validate the resolved ntfy Compose configuration
>@docker compose --env-file docker/ntfy/.env --file docker/ntfy/compose.yaml config --quiet

ntfy-up: ## Start the authenticated LAN-only ntfy server
>@docker compose --env-file docker/ntfy/.env --file docker/ntfy/compose.yaml up --detach

ntfy-down: ## Stop ntfy without deleting messages or access control
>@docker compose --env-file docker/ntfy/.env --file docker/ntfy/compose.yaml down

ntfy-test-publish: ## Send one authenticated test notification
>@bash scripts/ntfy_test_publish.sh

purple-range-portal-test: ## Validate the LAN-safe Purple-Team launcher
>@python3 -m unittest discover -s tests -p "test_purple_range_portal.py" -v

purple-range-portal-config: ## Validate the Purple-Team launcher Compose model
>@docker compose --file docker/purple-range-portal/compose.yaml config --quiet

purple-range-portal-up: ## Build and start the LAN-safe Purple-Team launcher
>@docker compose --file docker/purple-range-portal/compose.yaml up --detach --build

purple-range-portal-down: ## Stop the Purple-Team launcher
>@docker compose --file docker/purple-range-portal/compose.yaml down

purple-range-test: ## Validate the isolated range safety contract
>@python3 -m unittest discover -s tests -p "test_purple_range.py" -v

purple-range-config: ## Validate the isolated range Compose configuration
>@docker compose --file docker/purple-range/compose.yaml config --quiet

purple-range-up: ## Start the loopback-only Juice Shop target
>@docker compose --file docker/purple-range/compose.yaml up --detach --wait range-gateway

purple-range-down: ## Stop and remove disposable range containers
>@docker compose --file docker/purple-range/compose.yaml --profile attacker down --remove-orphans

purple-range-shell: ## Open a disposable HTTP attacker shell on the target network
>@docker compose --file docker/purple-range/compose.yaml --profile attacker run --rm --no-deps attacker

purple-range-verify: ## Prove target reachability and deny production/internet paths
>@bash scripts/purple_range_verify.sh

purple-range-alert-test: ## Prove range alerts are discarded while production reaches ntfy
>@bash scripts/purple_range_alert_test.sh

purple-range-reset: ## Recreate the disposable target from its pinned image
>@docker compose --file docker/purple-range/compose.yaml --profile attacker down --remove-orphans
>@docker compose --file docker/purple-range/compose.yaml up --detach --wait --force-recreate range-gateway

quiz-scenario: ## Generate a randomized /27 quiz manifest (use ARGS for exclusions or seed)
>@python3 scripts/quiz_scenario.py $(ARGS)

quiz-range-render: ## Render a private Compose model from a scenario (use ARGS for paths)
>@python3 scripts/quiz_range_compose.py $(ARGS)

quiz-app-test: ## Test vulnerable, fixed, and safety behavior of quiz templates
>@python3 -m unittest discover -s tests -p "test_quiz_app.py" -v

quiz-app-config: ## Validate the standalone quiz-template Compose model
>@docker compose --file docker/quiz-app/compose.yaml config --quiet

quiz-decoy-test: ## Test the reviewed safe discovery-decoy catalog
>@python3 -m unittest discover -s tests -p "test_quiz_decoy.py" -v

quiz-decoy-config: ## Validate the constrained discovery-decoy Compose model
>@docker compose --file docker/quiz-decoy/compose.yaml config --quiet

quiz-attacker-test: ## Validate the disposable quiz discovery toolbox
>@python3 -m unittest discover -s tests -p "test_quiz_attacker.py" -v

quiz-attacker-config: ## Validate the off-by-default attacker Compose model
>@docker compose --file docker/quiz-attacker/compose.yaml --profile attacker config --quiet

trailhead-test: ## Test the secure Trailhead Rentals application shell
>@python3 -m unittest discover -s tests -p "test_trailhead_rentals.py" -v

trailhead-config: ## Validate the Trailhead Rentals Compose model
>@docker compose --file docker/trailhead-rentals/compose.yaml config --quiet

ansible-inventory: ## Show the effective production Ansible inventory
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-inventory --graph

ansible-ping: ## Verify SSH and Python connectivity to managed nodes
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible all --module-name ansible.builtin.ping

ansible-check: ## Validate the read-only connectivity playbook in check mode
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --check ansible/playbooks/connectivity.yml

ansible-bootstrap-check: ## Preview the edge-node baseline (use ARGS for limits and become prompt)
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --check --diff ansible/playbooks/bootstrap.yml $(ARGS)

ansible-bootstrap: ## Apply the edge-node baseline (use ARGS for limits and become prompt)
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook ansible/playbooks/bootstrap.yml $(ARGS)

ansible-piaware-observability-check: ## Preview the privacy-safe PiAware metrics exporter
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --check --diff ansible/playbooks/piaware-observability.yml $(ARGS)

ansible-piaware-observability: ## Install the privacy-safe PiAware metrics exporter
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --diff ansible/playbooks/piaware-observability.yml $(ARGS)

ansible-vault-create: ## Create the ignored production variable vault interactively
>@mkdir -p ansible/inventories/production/group_vars/all
>@test ! -e ansible/inventories/production/group_vars/all/vault.yml || (echo "[FAIL] Production vault already exists; use ansible-vault-edit"; exit 1)
>@umask 077; ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-vault create ansible/inventories/production/group_vars/all/vault.yml

ansible-vault-edit: ## Edit the ignored production variable vault interactively
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-vault edit ansible/inventories/production/group_vars/all/vault.yml

ansible-vault-view: ## View the ignored production variable vault
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-vault view ansible/inventories/production/group_vars/all/vault.yml

rebuild-syntax: ## Validate the disposable controller rebuild playbook
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --syntax-check --inventory ansible/inventories/rebuild/hosts.yml ansible/playbooks/controller-rebuild.yml

rebuild-check: ## Preview the marked disposable controller rebuild target
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --check --diff --inventory ansible/inventories/rebuild/hosts.yml ansible/playbooks/controller-rebuild.yml

rebuild-apply: ## Apply the baseline only to the marked disposable rebuild target
>@ANSIBLE_CONFIG="$(CURDIR)/ansible/ansible.cfg" ansible-playbook --diff --inventory ansible/inventories/rebuild/hosts.yml ansible/playbooks/controller-rebuild.yml

rebuild-stage-validate: ## Reconstruct and validate controller state without starting services
>@bash scripts/rebuild_stage_validate.sh

backup-init: ## Initialize the encrypted workstation Restic repository once
>@bash scripts/homelab_backup.sh init

backup-run: ## Export and encrypt all irreplaceable homelab state
>@bash scripts/homelab_backup.sh backup

backup-check: ## Verify a subset of encrypted repository data
>@bash scripts/homelab_backup.sh check

backup-snapshots: ## List encrypted homelab snapshots
>@bash scripts/homelab_backup.sh snapshots

backup-restore-test: ## Restore and validate every encrypted backup data class
>@bash scripts/homelab_backup.sh restore-test

backup-prune: ## Apply retention and reclaim repository space
>@bash scripts/homelab_backup.sh prune

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
