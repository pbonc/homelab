# Homelab

Professional, portfolio-style homelab repository for building and operating a hybrid infrastructure controller node.

## Project Context

- Controller host: `brain`
- OS target: Ubuntu 26.04 LTS
- User: `dar`
- Hardware profile: Intel Celeron N5095A (4 cores), 14 GB RAM, ~100 GB NVMe
- Role: Controller node for automation, CI/CD, infrastructure as code, and observability workflows

## Objectives

- Build the homelab incrementally with clean structure and traceable decisions
- Keep automation portable across CI systems
- Document architecture, standards, and operating assumptions clearly
- Demonstrate practical SRE/DevOps/QA engineering habits

## CI Portability Principle

This repository is designed so GitHub Actions, GitLab CI, and Jenkins call the same local interfaces (`make` targets and scripts), rather than re-implementing logic per CI platform.

## Current State

The homelab currently has two running nodes:

- `brain`, the controller and primary workload node
- `piaware`, a Raspberry Pi ADS-B receiver and monitored edge node

`brain` hosts:

- Docker and Docker Compose
- Homepage at `http://192.168.1.23:3000`
- Glances host metrics displayed on the `brain` card
- A self-hosted GitHub Actions runner
- Repository diagnostics through `labctl`
- Prometheus, Loki, Alloy, Alertmanager, and ntfy observability services
- The Study Deck, Network Inventory API, and Architecture Map

Homepage and Glances use digest-pinned images. Homepage has an explicit healthcheck, restricted host-header allowlist, and read-only Docker integration through an internal socket proxy.

The telemetry platform ingests live Ecowitt weather data into InfluxDB and
provides Grafana dashboards plus a current-weather Homepage summary. A
server-side Aikido adapter source preserves the aggregate security-status
integration without exposing credentials or finding details; live polling is
dormant while API access remains plan-restricted. The `piaware` edge node
provides aggregate receiver and host metrics to Prometheus without exporting
aircraft identities or private location data. Planned dashboard cards remain
non-clickable until their services are deployed.

## Quick Start

1. Run environment checks: `make doctor`
2. Validate Homepage configuration: `make lint`
3. Show repository and service status: `make status`
4. Explore available commands: `make help`

Homepage releases use the shared deployment contract documented in [`docs/deployment.md`](docs/deployment.md). Validate with `make homepage-validate`; deploy, verify, and rollback through the corresponding `homepage-*` targets.

## Repository Layout

See the folders in the project root and detailed documentation in `docs/`.

## Current Roadmap Focus

- Finish the remaining Sprint 6 outage exercises and continuous-security work
- Complete post-Sprint 9 notification, network-inventory, and Architecture Map rollout
- Add the threat-assessment explorer and refreshed Aikido controls
- Build Sprint 8's isolated purple-team range with explicit safety boundaries
- Keep Sprints 10 and 11 deferred until their documented prerequisites justify them

See [`docs/roadmap.md`](docs/roadmap.md) for the authoritative sprint status and
acceptance criteria.

The first Sprint 8 vertical slice is documented in
[`docs/purple-range.md`](docs/purple-range.md). It provides a loopback-only,
digest-pinned OWASP Juice Shop target and a disposable attacker profile on an
internal Docker network.

## License

This repository is currently intended as a personal engineering portfolio project.

## Homepage Dashboard (First Deployed Service)

The first deployed service in this homelab is [Homepage](https://github.com/gethomepage/homepage), running with Docker Compose under `docker/homepage/`.

Why Homepage first:

- Provides an interview-ready control surface immediately
- Creates a single dashboard for current, planned, and future services
- Establishes a repeatable Docker Compose deployment pattern for the rest of the stack

Start Homepage:

- `cd docker/homepage`
- `docker compose up -d`

Stop Homepage:

- `cd docker/homepage`
- `docker compose down`

View logs:

- `cd docker/homepage`
- `docker compose logs -f`

Open in browser:

- `http://192.168.1.23:3000`

Homepage configuration is mounted from `docker/homepage/config/`. Repository changes do not affect the running dashboard until this directory is deployed or synchronized to `brain`.

The dashboard configuration version is stored in `docker/homepage/version.env` and displayed on the Homepage service card. Git tags and future deployment pipelines can override this value for versioned releases.
