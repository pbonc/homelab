# Roadmap

## Phase 0: Foundation — Complete

- Repository structure and documentation baseline
- Shared Make targets and `labctl` diagnostics
- Docker Compose deployment for Homepage
- Self-hosted GitHub Actions runner workflow

## Phase 1: Truthful Dashboard — Current

- [x] Separate deployed, planned, and future services
- [x] Remove placeholder click targets
- [x] Retire unsupported status JSON and DOM mutation
- [x] Add UTF-8 and Homepage configuration validation
- [x] Separate physical nodes from deployed services
- [x] Add host metrics to the `brain` card
- [x] Display the semantic dashboard version
- [ ] Deploy the current Homepage configuration to `brain`
- [ ] Restore Docker integration through a supported, least-privilege connection
- [ ] Add a real container healthcheck

## Phase 2: Runtime Health Collection

- Expand `labctl status` beyond repository structure checks
- Add HTTP reachability, timestamps, latency, and stale-data handling
- Return nonzero exit codes for actionable failures
- Define and test a versioned UTF-8 JSON schema

## Phase 3: Observability

- Add Prometheus, Grafana, and availability monitoring
- Define service checks and initial alerts
- Add weather conditions and forecast integration
- Add runbooks and incident-response notes

## Phase 4: ADS-B Edge Node

- Provision the Raspberry Pi receiver with a role-oriented hostname
- Monitor host health, SDR connectivity, receiver processes, and feed freshness
- Collect aircraft count, message rate, and reception-range metrics
- Add a Homepage summary and detailed Grafana dashboard

## Phase 5: Automation and Platform Expansion

- Add Ansible controller and node bootstrap roles
- Add Terraform module and state conventions
- Introduce K3s and Helm when controller capacity and operational needs justify them
- Add further CI providers only where they demonstrate a distinct capability

## Success Criteria

- Every clickable dashboard item resolves to a deployed destination
- Health indicators come from supported and testable checks
- Automation is reproducible from a clean checkout
- Documentation matches deployed infrastructure
- Changes are testable, observable, and reversible
