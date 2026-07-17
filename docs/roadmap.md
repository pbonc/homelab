# Roadmap

## Phase 0: Foundation — Complete

- [x] Create the repository structure and documentation baseline
- [x] Establish shared Make targets and `labctl` diagnostics
- [x] Deploy Homepage with Docker Compose
- [x] Register a self-hosted GitHub Actions runner on `brain`

## Phase 1: Truthful Dashboard — Complete

- [x] Separate infrastructure nodes, deployed services, planned services, and future work
- [x] Remove placeholder click targets and unused project cards
- [x] Separate `brain` from the Homepage service
- [x] Add Glances-backed CPU, memory, and root filesystem metrics to `brain`
- [x] Classify `brain` as active, warning, critical, or unavailable from live metrics
- [x] Style planned and future cards as inactive inventory
- [x] Display dashboard semantic version `0.1.0`
- [x] Retire the unsupported status JSON polling path
- [x] Add UTF-8, URL, lifecycle, and version validation
- [x] Add Glances readiness, host-header validation, and restricted CORS configuration
- [x] Deploy and visually verify the current dashboard on `brain`

## Phase 2: Deployment Contract — Complete

Build one deployment interface that works locally, from GitHub Actions, and later from Jenkins.

- [x] Choose and document a permanent deployment directory on `brain`
- [x] Add `homepage-validate`, `homepage-deploy`, `homepage-verify`, and `homepage-rollback` Make targets
- [x] Record the deployed semantic version, Git commit, deployer, and timestamp
- [x] Preserve the last known-good release for rollback
- [x] Prevent overlapping deployments with a deployment lock
- [x] Add a manually triggered GitHub Actions deployment workflow
- [x] Exercise deploy, failed verification, and rollback paths
- [x] Keep production deployment manually triggered; do not deploy automatically from `main`

### Runtime hardening during Phase 2

- [x] Pin Homepage and Glances image versions instead of using mutable `latest` tags
- [x] Add a real Homepage container healthcheck
- [x] Replace `HOMEPAGE_ALLOWED_HOSTS=*` with the trusted hostnames and addresses
- [x] Restore Homepage Docker integration through a least-privilege socket proxy or equivalent
- [x] Update `labctl status` to recognize the Glances container and deployed release

## Phase 3: Telemetry Platform — Complete

Build the first version of a generic ingestion, storage, API, and visualization platform. The Ecowitt weather station is the first data source, not a weather-specific architectural boundary.

### 1. Contracts and configuration

- [x] Define the source-plugin interface, normalized telemetry envelope, measurement names, units, timestamps, and unknown-field preservation rules
- [x] Establish API conventions that support future routes such as `/api/current/adsb` and `/api/current/docker`
- [x] Define environment-based configuration and local secret handling for InfluxDB and Grafana without committing credentials
- [x] Create the initial `docs/telemetry.md` architecture, data-flow, configuration, and extension-point sections

### 2. Collector vertical slice

- [x] Create a modular `docker/telemetry-collector/` Python and FastAPI service
- [x] Implement source plugins or handlers with Ecowitt as the first source
- [x] Accept Ecowitt uploads at `POST /data/report/`
- [x] Normalize common weather, wind, rain, solar, UV, and battery measurements
- [x] Preserve unknown Ecowitt values rather than discarding them
- [x] Add automated tests and representative Ecowitt fixtures for parsing, normalization, unknown fields, and API errors

### 3. Storage and container runtime

- [x] Add Docker Compose services for the FastAPI telemetry collector, InfluxDB, and Grafana
- [x] Automatically configure the InfluxDB organization, bucket, and retention policy
- [x] Store normalized and source-specific telemetry in InfluxDB
- [x] Add service healthchecks, dependency readiness, automatic restarts, and persistent volumes where appropriate
- [x] Verify a synthetic Ecowitt report reaches InfluxDB before connecting the physical station

### 4. Query APIs

- [x] Add `GET /api/health`, `GET /api/current/weather`, and `GET /api/history/weather`
- [x] Define bounded history-query parameters and stable empty, stale, and error responses
- [x] Add automated API tests backed by known telemetry samples

### 5. Platform consumers

- [x] Automatically provision the Grafana datasource and a starter weather dashboard covering temperature, humidity, pressure, wind, rain, UV, solar, battery, and upload frequency
- [x] Add `python -m labctl telemetry` for platform health, latest weather, last upload, and source count
- [x] Add Homepage cards for Telemetry Collector, InfluxDB, and Grafana
- [x] Expose the collector's last upload and active telemetry-source count through its API and `labctl telemetry`
- [x] Replace the Homepage search bar with local weather data from the Telemetry Collector API
- [x] Move Weather from planned inventory to deployed services in Homepage only after live data is verified

### 6. Live rollout and acceptance

- [x] Configure the Ecowitt gateway to upload to `POST /data/report/`
- [x] Complete `docs/telemetry.md` with REST APIs, Ecowitt setup, dashboard extension, Homepage integration, operations, and troubleshooting
- [x] Verify live Ecowitt ingestion, restart persistence, API freshness, Grafana dashboards, Homepage cards, and `labctl telemetry`
- [x] Confirm collector handlers, Grafana dashboards, and Homepage integrations provide clear extension points for the next telemetry source

## Phase 4: Security Visibility — Complete

### 1. Aikido baseline and policy

- [x] Connect only the `homelab` repository to Aikido through its read-only GitHub App permissions
- [x] Establish an Aikido baseline for dependency, SAST, secret, license, IaC, and malware findings
- [x] Keep Autofix, write permissions, and release gating disabled during baseline adoption

### 2. Homepage security status

- [x] Add a server-side Aikido status adapter on `brain` that stores its API token outside the repository and polls Aikido at a conservative interval
- [x] Aggregate open findings across the Aikido workspace and expose only severity counts, scan freshness, and a dashboard link through a credential-free LAN endpoint
- [x] Add an equal-height Aikido card to Homepage without embedding a variable-height widget
- [x] Color the card green when clear, yellow for low or medium findings or stale results, orange for high findings, red for critical findings, and gray when status is unavailable
- [x] Base the card state on open findings rather than closed, ignored, snoozed, or historical findings
- [x] Verify the API token and detailed findings are never exposed to Homepage clients, logs, or committed configuration

## Phase 5: Runtime Health Contract

### 1. Runtime status contract

- [x] Define and test a versioned UTF-8 status schema
- [x] Define the service inventory, criticality, and ownership before adding checks
- [x] Measure initial probes and document service-specific latency, stale-data, and failure thresholds
- [x] Expand `labctl status` to check Docker, deployed containers, the GitHub Actions runner, and managed release metadata
- [x] Add HTTP reachability, response latency, timestamps, and stale-data handling for Homepage, telemetry, Grafana, InfluxDB, and Aikido status
- [x] Return nonzero exit codes only for documented actionable failures and preserve an explicit unavailable state for unsupported checks
- [x] Add deterministic contract tests for healthy, degraded, stale, unavailable, and failed states
- [x] Refresh architecture and network documentation from the verified runtime inventory

### 2. Operational acceptance

- [x] Add runbooks and incident-response notes
- [ ] Exercise service-down, stale-data, runner-offline, and unsupported-platform scenarios

### Security follow-up

- [ ] Triage and document accepted Aikido baseline findings
- [ ] Gate newly introduced critical and high-severity findings without granting automatic-fix write access
- [ ] Add container-image and exposed-domain scanning as deployed services expand

## Phase 6: Metrics and Observability

### 1. Metrics, hardware, and availability

- [ ] Deploy Prometheus and Node Exporter with constrained access, persistent storage, and documented retention
- [ ] Collect host hardware telemetry for `brain`, including CPU, memory, disks, network interfaces, and available temperature or sensor readings
- [ ] Provision a Grafana hardware dashboard with current health, utilization trends, storage capacity, and sensor history
- [ ] Add availability probes for the Phase 5 critical service inventory and distinguish service failure from stale application data
- [ ] Define recording rules, thresholds, and alerts only after observing a representative baseline

### 2. Deployment events

- [ ] Define a versioned deployment-event contract and durable event sink independent of Grafana
- [ ] Record successful, failed, and rolled-back deployments using version, Git commit, deployer, target, result, and timestamp
- [ ] Make event publication best-effort so an unavailable observability backend cannot alter deployment or rollback outcomes
- [ ] Display deployment events as Grafana annotations on weather, hardware, and future service dashboards
- [ ] Test annotation correlation across successful deployment, failed verification, and rollback paths

### 3. Logs and acceptance

- [ ] Add Loki and a constrained log collector after metrics and availability checks are stable
- [ ] Add observability runbooks and retention or capacity notes
- [ ] Exercise disk-pressure, failed-deployment, log-backend-outage, and metrics-backend-outage scenarios

## Phase 7: Reproducible Node Automation

- [ ] Define an Ansible inventory and connection model for `brain` and future edge nodes
- [ ] Add a minimal bootstrap role for users, SSH access, time synchronization, base packages, and Docker where required
- [ ] Separate non-secret defaults from encrypted or runtime-only secrets
- [ ] Add check-mode and idempotence validation before using automation on a new node
- [ ] Document recovery and manual break-glass steps when automation cannot reach a node

## Phase 8: ADS-B Edge Node

- [ ] Record receiver hardware, SDR model, network identity, and power or storage constraints
- [ ] Provision the Raspberry Pi receiver through the Phase 7 automation baseline with a role-oriented hostname
- [ ] Verify local aircraft decoding and feed freshness before adding remote telemetry
- [ ] Monitor host health, SDR connectivity, receiver processes, and feed freshness
- [ ] Collect aircraft count, message rate, and reception-range metrics
- [ ] Add an ADS-B collector plugin, Homepage summary, and detailed Grafana dashboard
- [ ] Document offline buffering, restart behavior, retention, and troubleshooting
- [ ] Complete an outage and recovery exercise without affecting the controller node

## Phase 9: Optional Platform Expansion

- [ ] Add Terraform module and state conventions only when a concrete managed provider or reproducible resource exists
- [ ] Introduce K3s and Helm only after capacity measurements and a multi-service operational need justify their overhead
- [ ] Deploy Jenkins only when it demonstrates a capability not already provided by GitHub Actions
- [ ] Require Jenkins to call the same Make targets, preserve manual production releases, and leave only one production deployer
- [ ] Add further CI providers only where they demonstrate a distinct capability

## Success Criteria

- Every clickable dashboard item resolves to a deployed destination
- Health indicators come from supported, testable, and documented checks
- Deployments are versioned, mutually exclusive, verifiable, and reversible
- Security status is least-privilege, actionable, and free of credentials or finding details
- Runtime checks distinguish healthy, degraded, stale, unavailable, and failed states
- Telemetry and deployment events remain useful across restarts and observability outages
- CI providers call shared repository interfaces instead of embedding unique deployment logic
- Automation is reproducible from a clean checkout
- Documentation matches deployed infrastructure
