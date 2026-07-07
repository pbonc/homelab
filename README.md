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

## Current Scope

Initial scaffold includes:

- Documentation baseline under `docs/`
- Common automation entry points in `Makefile`
- Environment validation script in `scripts/doctor.sh`
- Domain folders for Ansible, Terraform, Docker, Helm, Kubernetes, Jenkins, monitoring, and security

No real secrets, production manifests, or installations are included at this stage.

## Quick Start

1. Make the doctor script executable:
	- `chmod +x scripts/doctor.sh`
2. Run environment checks:
	- `make doctor`
3. Explore available commands:
	- `make help`

## Repository Layout

See the folders in the project root and detailed documentation in `docs/`.

## Next Milestones

- Add foundational Docker Compose services for local tooling
- Add Ansible baseline playbooks for controller bootstrap
- Add Terraform skeleton for future cloud/on-prem experiments
- Add first CI pipeline wrappers that call the same `make` targets

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