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

## Phase 3: Telemetry Platform — Current

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
- [x] Show the collector's last upload and active telemetry-source count in Homepage
- [x] Replace the Homepage search bar with local weather data from the Telemetry Collector API
- [ ] Move Weather from planned inventory to deployed services in Homepage only after live data is verified

### 6. Live rollout and acceptance

- [x] Configure the Ecowitt gateway to upload to `POST /data/report/`
- [ ] Complete `docs/telemetry.md` with REST APIs, Ecowitt setup, dashboard extension, Homepage integration, operations, and troubleshooting
- [ ] Verify live Ecowitt ingestion, restart persistence, API freshness, Grafana dashboards, Homepage cards, and `labctl telemetry`
- [ ] Confirm collector handlers, Grafana dashboards, and Homepage integrations provide clear extension points for the next telemetry source

## Phase 4: CI/CD Orchestration

- [ ] Deploy Jenkins only after the shared deployment contract is stable
- [ ] Have Jenkins call the same Make targets as GitHub Actions
- [ ] Add a Jenkins release parameter for semantic version or Git tag
- [ ] Assign only one system as the automatic production deployer
- [ ] Use the other CI system for validation, manual releases, or pipeline-parity demonstrations

## Phase 5: Runtime Health and Observability

- [ ] Expand `labctl status` beyond repository structure checks
- [ ] Add HTTP reachability, timestamps, latency, and stale-data handling
- [ ] Return nonzero exit codes for actionable failures
- [ ] Define and test a versioned UTF-8 status schema
- [ ] Add Prometheus, Loki, and availability monitoring around the existing telemetry platform
- [ ] Define initial service checks, thresholds, and alerts
- [ ] Add runbooks and incident-response notes

## Phase 6: ADS-B Edge Node

- [ ] Provision the Raspberry Pi receiver with a role-oriented hostname
- [ ] Monitor host health, SDR connectivity, receiver processes, and feed freshness
- [ ] Collect aircraft count, message rate, and reception-range metrics
- [ ] Add an ADS-B collector plugin, Homepage summary, and detailed Grafana dashboard

## Phase 7: Automation and Platform Expansion

- [ ] Add Ansible controller and node bootstrap roles
- [ ] Add Terraform module and state conventions
- [ ] Introduce K3s and Helm when controller capacity and operational needs justify them
- [ ] Add further CI providers only where they demonstrate a distinct capability

## Success Criteria

- Every clickable dashboard item resolves to a deployed destination
- Health indicators come from supported, testable, and documented checks
- Deployments are versioned, mutually exclusive, verifiable, and reversible
- CI providers call shared repository interfaces instead of embedding unique deployment logic
- Automation is reproducible from a clean checkout
- Documentation matches deployed infrastructure
