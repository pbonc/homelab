# Architecture

## Purpose

`brain` is the controller node for this homelab. The controller is responsible for orchestrating automation, CI/CD workflows, infrastructure definitions, and platform observability.

## Design Principles

- Keep components loosely coupled and script-driven
- Prefer declarative infrastructure and configuration
- Keep local execution and CI execution paths identical
- Build incrementally with clear rollback points

## Target Capability Areas

- Container workloads: Docker and Docker Compose
- Infrastructure as code: Terraform
- Configuration management: Ansible
- CI/CD orchestration: GitHub Actions, GitLab CI, Jenkins
- Platform layer: K3s and Helm
- Observability: Prometheus, Grafana, Loki

## High-Level Flow

1. Engineering workflow begins with local validation via `make` targets.
2. CI systems call the same targets to avoid duplicated logic.
3. Infrastructure and configuration changes are applied through controlled modules.
4. Monitoring validates runtime state and exposes system health.

## Current Topology

- `brain`: active controller node running Docker, Homepage, Glances, and a GitHub Actions runner
- ADS-B Raspberry Pi: future edge receiver node
- `atlas`: future GPU-capable node

Homepage is the current control surface. Glances supplies host CPU, memory, and filesystem data to the `brain` infrastructure card over the private Compose network. Planned services remain informational until they have a verified endpoint and health signal.

## Current Phase

Foundation work is complete. The lab is establishing a reliable local-operations and observability baseline before adding additional platforms or nodes.
