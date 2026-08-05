# Roadmap

## Sprint 0: Foundation — Complete

- [x] Create the repository structure and documentation baseline
- [x] Establish shared Make targets and `labctl` diagnostics
- [x] Deploy Homepage with Docker Compose
- [x] Register a self-hosted GitHub Actions runner on `brain`

## Sprint 1: Truthful Dashboard — Complete

- [x] Separate infrastructure nodes, deployed services, planned services, and future work
- [x] Remove placeholder click targets and unused project cards
- [x] Separate `brain` from the Homepage service
- [x] Add Glances-backed CPU, memory, and root filesystem metrics to `brain`
- [x] Classify `brain` as active, warning, critical, or unavailable from live metrics
- [x] Style planned and future cards as inactive inventory
- [x] Display the dashboard semantic version (initially `0.1.0`, currently `0.12.0`)
- [x] Retire the unsupported status JSON polling path
- [x] Add UTF-8, URL, lifecycle, and version validation
- [x] Add Glances readiness, host-header validation, and restricted CORS configuration
- [x] Deploy and visually verify the current dashboard on `brain`

## Sprint 2: Deployment Contract — Complete

Build one deployment interface that works locally, from GitHub Actions, and later from Jenkins.

- [x] Choose and document a permanent deployment directory on `brain`
- [x] Add `homepage-validate`, `homepage-deploy`, `homepage-verify`, and `homepage-rollback` Make targets
- [x] Record the deployed semantic version, Git commit, deployer, and timestamp
- [x] Preserve the last known-good release for rollback
- [x] Prevent overlapping deployments with a deployment lock
- [x] Add a manually triggered GitHub Actions deployment workflow
- [x] Exercise deploy, failed verification, and rollback paths
- [x] Keep production deployment manually triggered; do not deploy automatically from `main`

### Runtime hardening during Sprint 2

- [x] Pin Homepage and Glances image versions instead of using mutable `latest` tags
- [x] Add a real Homepage container healthcheck
- [x] Replace `HOMEPAGE_ALLOWED_HOSTS=*` with the trusted hostnames and addresses
- [x] Restore Homepage Docker integration through a least-privilege socket proxy or equivalent
- [x] Update `labctl status` to recognize the Glances container and deployed release

## Sprint 3: Telemetry Platform — Complete

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

## Sprint 4: Security Visibility — Complete

### 1. Aikido baseline and policy

- [x] Connect only the `homelab` repository to Aikido through its read-only GitHub App permissions
- [x] Establish an Aikido baseline for dependency, SAST, secret, license, IaC, and malware findings
- [x] Keep Autofix, write permissions, and release gating disabled during baseline adoption

### 2. Homepage security status

- [x] Add a server-side Aikido status adapter on `brain` that stores its API token outside the repository and polls Aikido at a conservative interval
- [x] Aggregate open findings across the Aikido workspace and expose only severity counts, scan freshness, and a dashboard link through a credential-free LAN endpoint
- [x] Add an equal-height Aikido card to Homepage without embedding a variable-height widget
- [x] Retire live Aikido polling when Public REST API access became plan-restricted; retain a static dashboard link and the reversible adapter source
- [x] Color the card green when clear, yellow for low or medium findings or stale results, orange for high findings, red for critical findings, and gray when status is unavailable
- [x] Base the card state on open findings rather than closed, ignored, snoozed, or historical findings
- [x] Verify the API token and detailed findings are never exposed to Homepage clients, logs, or committed configuration

## Sprint 5: Runtime Health Contract — Complete

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
- [x] Exercise service-down, stale-data, runner-offline, and unsupported-platform scenarios

## Sprint 6: Metrics and Observability

### 1. Metrics, hardware, and availability

- [x] Deploy Prometheus and Node Exporter with constrained access, persistent storage, and documented retention
- [x] Collect host hardware telemetry for `brain`, including CPU, memory, disks, network interfaces, and available temperature or sensor readings
- [x] Provision a Grafana hardware dashboard with current health, utilization trends, storage capacity, and sensor history
- [x] Add availability probes for the Sprint 5 critical service inventory and distinguish service failure from stale application data
- [x] Define recording rules, thresholds, and alerts only after observing a representative baseline

### 2. Deployment events

- [x] Define a versioned deployment-event contract and durable event sink independent of Grafana
- [x] Record successful, failed, and rolled-back deployments using version, Git commit, deployer, target, result, and timestamp
- [x] Make event publication best-effort so an unavailable observability backend cannot alter deployment or rollback outcomes
- [x] Display deployment events as Grafana annotations on the hardware dashboard without cluttering weather or platform-health views
- [x] Test annotation correlation across successful deployment, failed verification, and rollback paths

### 3. Logs and acceptance

- [x] Add Loki and a constrained log collector after metrics and availability checks are stable
- [x] Move Prometheus and Loki into deployed Homepage cards and expose Alloy's container health after live verification
- [x] Replace raw observability card destinations with Platform Health and a provisioned Container Logs dashboard
- [x] Add observability runbooks and retention or capacity notes
- [ ] Exercise disk-pressure, failed-deployment, log-backend-outage, and metrics-backend-outage scenarios

### 4. Continuous security

- [ ] Triage each Aikido baseline finding; document only explicit risk acceptances and leave deferred findings actionable
- [ ] Gate newly introduced critical and high-severity findings without granting automatic-fix write access
- [ ] Add container-image and exposed-domain scanning as deployed services expand
- [ ] Generate SBOMs for locally built images and attach verifiable signatures or provenance without granting deployment-time write access

### 5. Homelab study deck

- [x] Define a versioned, human-reviewable content schema for notes, multiple-choice questions, explanations, topics, difficulty, and links to repository documentation
- [x] Build a lightweight LAN-only study service that keeps question content in Git and personal progress in persistent runtime storage
- [x] Add short daily review sessions with shuffled choices, answer explanations, confidence ratings, and simple spaced repetition
- [x] Add an interview mode covering architecture, tradeoffs, failure scenarios, security boundaries, and concise project talking points
- [x] Seed the deck from completed sprints, including deployment rollback, telemetry contracts, Aikido boundaries, runtime health states, Prometheus, Grafana, and outage exercises
- [x] Require every technical answer to cite a repository document or deployed configuration so generated or stale claims cannot silently enter the deck
- [x] Add an equal-height Homepage card showing due-question count and study status, with the full experience opening as a separate page
- [x] Support progress export, reset, backup, and restore without committing personal history or browser data
- [x] Verify that notes, quiz responses, and APIs expose no credentials, secret values, private finding details, or unsafe purple-team instructions

## Sprint 7: Reproducible Node Automation — Complete

- [x] Define an Ansible inventory and connection model for `brain` and future edge nodes
- [x] Add a minimal bootstrap role for users, SSH access, time synchronization, base packages, and Docker where required
- [x] Separate non-secret defaults from encrypted or runtime-only secrets
- [x] Add check-mode and idempotence validation before using automation on a new node
- [x] Document recovery and manual break-glass steps when automation cannot reach a node
- [x] Define encrypted off-host backups, recovery-point and recovery-time objectives, and retention for irreplaceable state
- [x] Prove every encrypted backup data class restores into a disposable location
- [x] Document and execute a clean-Ubuntu rebuild exercise for `brain`

## Sprint 8: Isolated Purple-Team Range

### 1. Safety boundary and reproducibility

- [x] Define a threat model and an explicit authorization boundary covering only lab-owned targets
- [x] Place vulnerable targets on a dedicated network or VLAN with default-deny access to production services, no internet exposure, and restricted outbound access
- [x] Provision and destroy the range reproducibly; never reuse production credentials, secrets, volumes, or trusted service accounts
- [x] Add an ephemeral attacker workstation or container that can reach only the authorized target network
- [x] Verify isolation with positive target-connectivity tests and negative production-connectivity tests

### 2. Targets and detection

- [ ] Deploy one digest-pinned deliberately vulnerable target, beginning with OWASP Juice Shop or crAPI, and document its expected vulnerabilities
- [ ] Add a second target only after reset, isolation, and evidence collection are repeatable
- [ ] Collect target availability, application logs, network evidence, and selected runtime-security events without exposing attack payloads on Homepage
- [ ] Build Grafana views that correlate attack time, target health, network behavior, runtime events, and recovery
- [ ] Keep vulnerable findings scoped to the range so intentional targets cannot obscure actionable production findings

### 3. Exercises and portfolio evidence

- [ ] Define repeatable attack scenarios with expected preventive, detective, and recovery controls
- [ ] Execute an authorized exploit, capture evidence, contain the target, rebuild it, and verify recovery
- [ ] Write a sanitized incident report with timeline, root cause, detection gaps, remediation, and follow-up actions
- [ ] Demonstrate that the same technique is subsequently blocked, detected earlier, or produces a documented accepted limitation
- [ ] Publish a portfolio-safe architecture diagram and concise outcome metrics without credentials, live target details, or weaponized instructions

### 4. Vulnerability quiz range

#### Phase A: Contracts and notification boundary

- [x] Define a versioned internal scenario manifest with a deterministic seed, authorized CIDR, target answer key, decoys, and `notification_policy="never"`
- [x] Allocate a random `/27` only from the dedicated quiz pool and reject overlap with declared LAN, production, and existing Docker networks
- [x] Add an Alertmanager discard route for `notification_policy="never"` before any ntfy receiver and retain host-resource notifications
- [x] Discover live Docker networks at scenario creation and fail closed when their subnets cannot be inspected
- [ ] Prove with a live synthetic alert that range lifecycle events are discarded while an equivalent production alert still reaches ntfy

#### Phase B: Guided baseline and quiz catalog

- [x] Keep Juice Shop as the guided reference target with loopback-only browser access and no production or internet route
- [x] Define a reviewed quiz-template contract with vulnerability class, safe synthetic data, success evidence, root cause, mitigation, and related Juice Shop lesson
- [x] Build one coherent non-Juice-Shop assessment application with a distinct theme, locally served licensed or original assets, and realistic catalog, account, search, record, review, profile, support, and administrative workflows
- [ ] Implement secure and deliberately vulnerable variants behind reviewed feature seams; select compatible combinations from the seeded manifest instead of generating arbitrary unsafe source code
- [x] Randomize an unknown but bounded vulnerability count per round, include secure features and plausible dead ends, and guarantee every selected weakness is reachable and independently testable
- [x] Build the first three bounded templates: SQL injection, broken object-level authorization (IDOR), and stored XSS
- [ ] Include secure behavior and plausible dead ends so input fields do not automatically reveal the answer
- [x] Add deterministic vulnerable and fixed-mode tests for every template
- [ ] Keep unrestricted command execution, external SSRF, production credentials, real personal data, and runtime internet downloads outside the initial variant catalog

#### Phase C: Discovery rounds

- [ ] Build a digest-pinned attacker image with `nmap`, `curl`, and basic DNS or HTTP inspection tools; keep it disposable and off by default
- [ ] Place one quiz target and three to eight harmless decoy deployments at seeded static addresses inside the authorized `/27`
- [x] Build a reviewed decoy catalog with distinct branding, titles, headers, routes, response shapes, and varied HTTP ports, including documentation, status, marketing, inventory API, login, maintenance, and secure catalog services
- [x] Give decoys believable synthetic content, correctly enforced authentication or authorization where shown, and enough stable behavior for meaningful enumeration without accidental vulnerabilities
- [ ] Vary target, decoy selection, address, port, and presentation by seed while preserving deterministic replay and preventing default-server fingerprints from revealing the answer
- [ ] Reveal only the authorized CIDR, engagement mode, time limit, and optional credentials; keep the answer key server-side
- [ ] Provide browser access through a constrained range gateway without exposing arbitrary LAN proxying or target identity
- [ ] Verify target and every expected decoy from the attacker, validate the student-visible scan surface against the manifest, and fail a round when a deployment is missing or unexpected
- [ ] Verify positive discovery and target access plus negative production, LAN, Docker-host, and internet connectivity on every generated round
- [ ] Destroy target, decoys, credentials, answer key, and scenario network together; prove the next seed cannot inherit addresses, state, or discoveries from the prior round

#### Phase D: Assessment ledger and quiz experience

- [ ] Add guided, gray-box, and black-box round modes with increasing information scarcity
- [ ] Generate a student-safe engagement brief that states only authorization, scope, objective, time limit, mode, and optional credentials without target identity, address, port, vulnerability count, or answer-key leakage
- [ ] Create an immutable range-run record containing scenario ID, seed, mode, difficulty, start and end times, deployment status, reset status, and a reference to the private scenario manifest
- [ ] Persist assessment history outside disposable target and decoy containers so destroying a round cannot erase its journal, findings, validation results, or sanitized telemetry references
- [ ] Keep the private scenario manifest, learner assessment journal, and observed telemetry timeline as separate data stores with explicit access boundaries
- [ ] Define a versioned finding schema containing vulnerability class, affected component or endpoint, discovery notes, bounded and redacted evidence, reproduction summary, impact, severity, confidence, remediation, detection notes, hint usage, and timestamps
- [ ] Track each finding through `suspected`, `submitted`, `partially_validated`, `validated`, `rejected`, `duplicate`, `false_positive`, `remediated`, and `regression_verified` states without rewriting its prior history
- [ ] Add append-only attempt records for reconnaissance, hypotheses, validation attempts, hints, and notable defensive observations without requiring every request or payload to be retained
- [ ] Accept structured findings through a local-only assessment API and provide a simple range journal that remains usable after the exercise deployment is destroyed
- [ ] Validate findings with a deliberate combination of signed per-run proof tokens, prohibited-state assertions, telemetry correlation, bounded manual evidence, and an instructor override instead of requiring every vulnerability to expose a flag
- [ ] Ensure proof tokens identify only their run and finding, cannot reveal other selected vulnerabilities, and cannot be forged or reused across rounds
- [ ] Present progress according to engagement mode: guided mode may show lesson objectives, gray-box mode may show broad categories, and black-box mode must not reveal the target, vulnerability count, or remaining findings
- [ ] Reveal the expected answer, root cause, mitigation, Juice Shop cross-reference, and missed defensive evidence only after submission or surrender
- [ ] Classify reports against decoys as valid informational observations, correctly controlled behavior, or false positives and explain the distinction during review
- [ ] Track local progress, time to first useful finding, time to validation, false-positive rate, hints, repeated or missed concepts, detection coverage, remediation success, and secure regression results without committing personal history
- [ ] Generate an end-of-round comparison of deployed, found, missed, and falsely reported concepts together with detection and remediation status
- [ ] Export a sanitized Markdown assessment report and versioned JSON run archive; defer SARIF, JUnit, and CSV exports until the ledger contract is stable
- [ ] Add retention, redaction, backup, and deletion rules for attempt history, evidence, session tokens, proof tokens, uploaded samples, and generated credentials
- [ ] Reset every round to clean synthetic state and prevent prior addresses, answers, or credentials from leaking into the next seed

#### Phase E: Detection and portfolio evidence

- [ ] Label all range telemetry `environment="purple_range"`, `expected_vulnerable="true"`, and `notification_policy="never"`
- [ ] Exclude quiz lifecycle, expected findings, resets, and container churn from ntfy while preserving genuine `brain` resource-pressure alerts
- [ ] Correlate bounded application logs, exercise timestamps, Suricata evidence, and selected Falco events in a dedicated Grafana view
- [ ] Correlate validated findings with the immutable attempt and telemetry timelines so a post-round review can compare attacker action, application evidence, alert timing, and control response
- [ ] Define expected observables and at least one candidate detection for every reviewed vulnerability module before admitting it to the scenario catalog
- [ ] Score discovery, validation, detection, remediation, and regression verification separately instead of reducing the exercise to exploit count or completion speed
- [ ] Keep payloads, flags, answer keys, and exploit details out of Homepage, ntfy, and production security summaries
- [ ] Produce sanitized post-round reports and comparative metrics showing discovery, detection, containment, reset, and control improvement

#### Phase F: Deployment automation and acceptance

- [ ] Add shared `quiz-range-validate`, `quiz-range-deploy`, `quiz-range-verify`, `quiz-range-reset`, and `quiz-range-destroy` Make targets with bounded cleanup and no production deployment-event publication
- [ ] Add a manual `workflow_dispatch` GitHub Actions workflow on the self-hosted `brain` runner that accepts only mode and difficulty while generating the seed and answer key locally
- [ ] Prevent seeds, selected variants, target addresses, generated credentials, and answer keys from appearing in GitHub inputs, action logs, artifacts, caches, or job summaries
- [ ] Keep quiz deployment, reset, decoy churn, expected findings, and round destruction silent in ntfy while leaving genuine `brain` CPU, memory, disk, temperature, and availability alerts active
- [ ] Exercise successful deployment, partial decoy failure, target failure, isolation failure, verification failure, reset, and full destruction without changing the running Juice Shop guide or production services
- [ ] Add the range to Homepage only after live acceptance, exposing sanitized availability and launch guidance without target details, answer keys, findings, or operational controls

## Sprint 9: ADS-B Edge Node — Complete

- [x] Record receiver hardware, SDR model, network identity, and power or storage constraints
- [x] Replace the Homepage ADS-B placeholder with a monitored PiAware card that opens the local SkyAware map in a new tab
- [x] Add live PiAware statistics to its Homepage card using the same compact monitored-node layout, equal height, status badge, health colors, and restrained metric presentation as the `brain` card
- [x] Provision the Raspberry Pi receiver through the Sprint 7 automation baseline with a role-oriented hostname
- [x] Verify local aircraft decoding and feed freshness before adding remote telemetry
- [x] Install a constrained metrics exporter and monitor Pi host health, SDR connectivity, receiver processes, and feed freshness
- [x] Collect aircraft count, message rate, and reception-range metrics
- [x] Add a detailed Grafana dashboard without exposing receiver secrets, aircraft identities, or precise private location data
- [x] Keep ADS-B in Prometheus and document why collector integration remains deferred until durable storage or a non-Prometheus consumer justifies it
- [x] Document offline buffering, restart behavior, retention, and troubleshooting
- [x] Complete an outage and recovery exercise without affecting the controller node

## Post-Sprint 9 Hotfix: ntfy Notification Delivery

- [x] Confirm the phone platform and choose a reachability model: iPhone on the trusted home LAN only
- [x] Document the mobile delivery boundary, including the self-hosted iOS upstream poll-request flow and the requirement that the phone can reach the Homelab server to fetch message content
- [x] Deploy a digest-pinned ntfy server on `brain` with a persistent message cache, authentication database, health check, bounded retention, and explicit resource limits
- [x] Default to deny-all access, disable public signup, prohibit anonymous publishing, and create separate least-privilege publisher and subscriber credentials
- [x] Store ntfy credentials and Web Push keys outside Git; do not rely on an obscure topic name as the security boundary
- [x] Add Alertmanager and route existing Prometheus firing and resolved alerts through ntfy's Alertmanager webhook formatter
- [x] Define notification grouping, inhibition, severity-to-priority mapping, repeat intervals, quiet behavior, and recovery messages before enabling phone delivery
- [ ] Start with actionable events: critical service outages, sustained resource pressure, stale telemetry, backup failures, failed deployments, and meaningful security-state changes
- [x] Keep routine successes and transient failures out of the phone channel unless an explicit digest or low-priority policy calls for them
- [x] Keep notification bodies concise and free of secrets, tokens, private finding details, aircraft identities, and sensitive infrastructure metadata
- [ ] Add ntfy health, delivery failures, storage use, and Alertmanager status to `labctl`, Prometheus, Grafana, and the observability runbook without creating a notification feedback loop
- [ ] Add an equal-height ntfy card to Homepage after live phone delivery is verified, linking to its LAN web interface and showing a supported health state without exposing its topic or credentials
- [ ] Bump the Homepage semantic version and verify the ntfy card, link target, health behavior, responsive layout, and unavailable-state fallback during the manual deployment
- [ ] Back up and restore only the required ntfy state, document token rotation, and prove a clean rebuild can re-establish subscriptions safely
- [ ] Exercise firing, grouping, resolution, invalid credentials, ntfy outage, phone-off-LAN behavior, delayed delivery, and recovery without losing the underlying Prometheus alert state

### Notification Expansion

- [x] Add a ten-minute sustained outage threshold for monitored hardware nodes and send recovery notifications when they return
- [ ] Add an independent observer for `brain`; document that controller-hosted Prometheus, Alertmanager, and ntfy cannot report a complete controller or power outage by themselves
- [x] Build a local network inventory watcher with a versioned state model, bounded `/24` discovery, persistent first-seen and last-seen timestamps, and no cloud lookup dependency
- [x] Maintain an explicit known-device inventory and notify only after an unknown MAC is observed repeatedly across a confirmation window
- [x] Handle private/randomized MAC addresses and Wi-Fi roaming without producing repeated “new device” alerts; keep ordinary departures dashboard-only
- [x] Publish a versioned, read-only topology API with stable node identifiers, verified status, explicit known/unknown state, and declared or evidence-backed edges
- [x] Represent unverified clients on a shared LAN segment; do not invent switch ports, access-point associations, or physical links from ARP observations
- [x] Deploy a standalone Network Inventory Lab linked from Homepage, with evidence-backed topology, unidentified-device investigation, persistent operator identification, and a quiet unavailable state
- [x] Keep topology rendering replaceable and driven entirely by the API contract; do not couple scanner persistence to one graph library or browser layout
- [ ] Add sustained thermal or throttling alerts for `brain` and `piaware`, using measured baselines and hardware-appropriate thresholds
- [ ] Alert when encrypted backups fail or exceed their expected freshness window, then send one recovery after the next verified backup
- [ ] Route established weather and ADS-B stale conditions through Alertmanager without exposing readings, aircraft identities, or receiver location
- [ ] Notify on failed deployments and meaningful Aikido severity transitions while keeping routine successes and finding details out of phone messages
- [ ] Consider a quiet daily digest for updates and routine successes only after immediate alerts prove low-noise
- [ ] Add network-inventory and notification-delivery status to Grafana, `labctl`, the Homepage, backup scope, and restore testing
- [ ] Exercise duplicate suppression, randomized addresses, watcher restart, unknown-device acknowledgement, hardware outage, controller blind spot, and recovery

## Post-Sprint 9 Hotfix: Interactive Architecture DFD

- [x] Define a versioned, repository-managed model of deployed external entities, edge and controller processes, persistent stores, and directional flows
- [x] Build a LAN-only interactive explorer with flow-category filtering and component-level input/output tracing
- [x] Show trust boundaries, protocols, endpoints, and concise responsibilities without exposing credentials or inventing undocumented flows
- [x] Add an equal-height Architecture Map card to Homepage and bump the dashboard semantic version
- [x] Deploy the service on `brain`, verify its health and Homepage link, and review the rendered flows against the live system
- [ ] Require future service changes to update the data-flow model when they introduce or alter a meaningful flow

## Post-Sprint 9 Hotfix: Interview Talking Point Strip

- [ ] Add concise interview talking points to the Study Deck for the recent observability, PiAware, Ansible, backup, and clean-rebuild work
- [ ] Tag talking points by topic and keep their source material traceable to the deployed lab
- [ ] Add a Study Deck endpoint that records display history without marking a talking point as studied or answered
- [ ] Select undisplayed talking points first, then the least recently displayed eligible point
- [ ] Add light topic-aware variation that avoids immediate repeats and repetitive runs without defeating the least-recently-displayed policy
- [ ] Add a compact talking-point strip immediately below the Homepage weather strip, backed by the Study Deck endpoint
- [ ] Preserve the existing Homepage card layout and provide a quiet fallback when Study Deck is unavailable
- [ ] Test selection fairness, persisted display history, unavailable-service behavior, and responsive Homepage layout

## Post-Sprint 9 Hotfix: Threat Assessment and Aikido Controls

- [ ] Confirm the current Aikido plan permits the Public REST API endpoints used by the existing read-only status adapter
- [ ] Document that Aikido already performs nightly full scans for connected repositories; distinguish starting a scan from fetching the latest findings in UI labels, APIs, logs, and runbooks
- [ ] Document the Public API limit of 20 calls per rolling minute per workspace and budget token retrieval, issue export, optional scan initiation, and scan-status polling separately
- [ ] Re-enable cached server-side Aikido finding collection on a quiet daily cadence after the expected nightly scan window
- [ ] Add a credential-free LAN `Refresh findings` endpoint that updates the cached summary without starting another scan or exposing Aikido credentials and finding details
- [ ] Add a separate operator-only `Scan now` action only if plan entitlement and measured need justify it; scope it to the `homelab` repository and require explicit confirmation
- [ ] Enforce a server-side manual-refresh cooldown, single-flight lock, token reuse until expiry, request timeout, daily call budget, and `429 Retry-After` handling
- [ ] Keep the last successful result available when refresh fails, clearly distinguishing stale data from unavailable data
- [ ] Add a compact refresh button and last-checked time to the Homepage Aikido card without changing card height; keep scan initiation out of the card's normal click path
- [ ] Disable the button and show quiet in-progress or cooldown feedback while a refresh is running or temporarily unavailable
- [ ] Test successful refresh, repeated clicks, concurrent refreshes, API-plan denial, rate limiting, timeout, stale-cache fallback, call-budget exhaustion, and browser-origin restrictions

### Threat assessment explorer

- [ ] Add a versioned, human-reviewable threat model whose assets and attack surfaces reference existing Architecture Map component and flow identifiers
- [ ] Record each threat's scenario, affected boundary, likelihood, impact, existing controls, detection path, residual risk, owner, status, evidence, and next review date
- [ ] Seed the model with credential theft, exposed LAN services, compromised dependencies or images, unauthorized deployment, telemetry tampering, denial of service, backup loss, and edge-node compromise
- [ ] Add `Threats` and `Attack paths` views to the Architecture Map, with severity and mitigation filters plus component-level drill-down instead of drawing every possible path on the overview simultaneously
- [ ] Correlate Aikido severity totals and scan freshness with the assessment, but keep vulnerability details and actionable exploit instructions out of the Homepage and architecture APIs
- [ ] Produce a concise assessment summary showing highest residual risks, control gaps, stale evidence, and recommended next actions; label rules-based conclusions separately from scanner findings
- [ ] Require explicit authorization boundaries for active validation and defer exploit execution to the isolated purple-team range
- [ ] Add schema, cross-reference, redaction, risk-ranking, stale-review, and unavailable-Aikido tests

## Sprint 10: Family Links Portal

- [ ] Define a small, non-technical link catalog with the intended user before choosing categories or visual design
- [ ] Choose a memorable LAN-only hostname and document that `mom.links` uses a real public TLD, requiring intentional local DNS handling rather than an assumed private namespace
- [ ] Serve a simple responsive page with large readable link targets, clear labels, restrained navigation, and no Homelab operational controls
- [ ] Keep link content human-reviewable in Git while allowing routine updates through a low-friction workflow
- [ ] Provide a dedicated health check and a Homepage operator link without exposing the Homelab dashboard to the family-facing page
- [ ] Make the service LAN-only, credential-free for reading, and isolated from secrets, administrative APIs, and infrastructure metadata
- [ ] Define friendly unavailable-link behavior so one broken destination does not make the portal confusing
- [ ] Add backup, restore, deployment, rollback, and accessibility checks appropriate to a small static service
- [ ] Test the page on the devices and browsers its intended user actually uses

## Sprint 11: Optional Platform Expansion

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
- Locally built artifacts have inspectable dependency inventories and verifiable provenance
- CI providers call shared repository interfaces instead of embedding unique deployment logic
- Automation is reproducible from a clean checkout
- Backups are proven through restoration rather than assumed from successful backup jobs
- Deliberately vulnerable targets remain isolated, reproducible, disposable, and covered by documented detection and recovery exercises
- Study material remains traceable to the deployed lab and turns implementation decisions, failures, and recoveries into concise interview explanations
- Documentation matches deployed infrastructure
