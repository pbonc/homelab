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

`brain` is currently the only running homelab system. It hosts:

- Docker and Docker Compose
- Homepage at `http://192.168.1.23:3000`
- Glances host metrics displayed on the `brain` card
- A self-hosted GitHub Actions runner
- Repository diagnostics through `labctl`

Homepage and Glances use digest-pinned images. Homepage has an explicit healthcheck, restricted host-header allowlist, and read-only Docker integration through an internal socket proxy.

Weather data and an ADS-B receiver on a Raspberry Pi are planned. Other dashboard cards are intentionally non-clickable until their services are deployed.

## Quick Start

1. Run environment checks: `make doctor`
2. Validate Homepage configuration: `make lint`
3. Show repository and service status: `make status`
4. Explore available commands: `make help`

Homepage releases use the shared deployment contract documented in [`docs/deployment.md`](docs/deployment.md). Validate with `make homepage-validate`; deploy, verify, and rollback through the corresponding `homepage-*` targets.

## Repository Layout

See the folders in the project root and detailed documentation in `docs/`.

## Next Milestones

- Build shared validate, deploy, verify, and rollback targets for Homepage
- Add a manually triggered, version-aware GitHub Actions deployment
- Harden the runtime with pinned images, a Homepage healthcheck, and restricted allowed hosts
- Deploy Jenkins after the shared deployment contract is proven
- Expand `labctl` and add the observability stack

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
