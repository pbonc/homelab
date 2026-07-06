# Roadmap

## Phase 0: Foundation (Current)

- Create repository structure for core domains
- Establish documentation baseline
- Add local environment validation (`make doctor`)
- Define CI portability strategy around shared Make targets

## Phase 1: Local Operations Baseline

- Add Docker Compose for local utility services
- Add bootstrap scripts for repeatable controller setup
- Add style/lint/test placeholders for future expansion

## Phase 2: Automation and IaC

- Add initial Ansible role and inventory structure
- Add Terraform module skeletons and remote state strategy
- Introduce environment-specific configuration conventions

## Phase 3: CI/CD Integration

- Add GitHub Actions workflows that call shared Make targets
- Add Jenkins pipeline wrappers calling same targets
- Add GitLab CI wrappers for parity

## Phase 4: Observability and Reliability

- Add Prometheus, Grafana, and Loki base configuration
- Define SLO-inspired service checks for key components
- Add runbook templates and incident response notes

## Phase 5: Kubernetes Platform Layer

- Introduce K3s cluster bootstrap plan
- Add Helm chart organization strategy
- Add workload deployment lifecycle documentation

## Success Criteria

- Every automation path is reproducible from a clean checkout
- CI providers execute the same command contracts
- Documentation stays synchronized with implementation
- Changes are testable, observable, and reversible
