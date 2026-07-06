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

## Current Phase

This repository is in the initial scaffolding phase. It intentionally contains structure and contracts before implementation depth.
