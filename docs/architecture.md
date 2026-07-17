# Architecture

## Purpose

`brain` is the controller and current workload node for the homelab. It runs
the control surface, telemetry platform, security-status adapter, and CI runner.
Additional nodes should use the same documented contracts rather than becoming
special cases.

## Design principles

- Keep components loosely coupled and script-driven
- Prefer declarative, versioned configuration
- Keep local and CI execution paths identical through Make targets
- Treat health, freshness, and availability as different states
- Keep credentials server-side and outside repository history
- Add platforms only when they solve a measured operational need

## Current topology

### Controller node: `brain`

`brain` runs three Compose-managed groups plus one host service:

| Group | Components | Responsibility |
| --- | --- | --- |
| Homepage | Homepage, Glances, read-only Docker socket proxy | LAN control surface and host summary |
| Telemetry | Telemetry Collector, InfluxDB, Grafana | Ingestion, durable time-series storage, APIs, and dashboards |
| Security status | Aikido status adapter | Server-side OAuth, cached workspace severity summary, and LAN-safe status API |
| Host service | GitHub Actions runner | Manually triggered validation and production deployment jobs |

The Homepage stack is deployed through immutable releases under
`/srv/homelab/homepage`. Telemetry and security status currently run from
their repository Compose definitions on `brain`.

### Planned nodes

- ADS-B Raspberry Pi: future edge receiver, after the Ansible baseline exists
- `atlas`: future GPU-capable node with no current workload or address

## Data and control flows

### Deployment

1. An operator triggers a release manually.
2. GitHub Actions or a local operator calls the repository Make target.
3. The release script acquires the deployment lock and stages an immutable
   Homepage release.
4. Compose activates the candidate and verification checks container health and
   HTTP readiness.
5. Failure restores the last-known-good release; success records version,
   commit, deployer, and timestamp.

### Weather telemetry

1. The Ecowitt gateway sends reports over the trusted LAN to the Telemetry
   Collector.
2. The collector normalizes measurements and writes them to InfluxDB.
3. Grafana queries InfluxDB for weather dashboards.
4. Homepage fetches only the collector's current weather API for its summary
   strip.

### Security status

1. The security-status adapter reads ignored file-backed Aikido client
   credentials.
2. It obtains short-lived OAuth access tokens and polls workspace-wide open
   issues every 15 minutes.
3. It exposes only aggregate severity counts and cache freshness on the LAN.
4. Homepage reads that sanitized endpoint every minute and colors the Aikido
   card from the worst open severity.

### Runtime status

`python -m labctl status` evaluates the host Docker service, all deployed
containers, the GitHub Actions runner, release metadata, HTTP reachability,
latency, weather freshness, and Aikido cache freshness. Human and JSON output
share the versioned contract documented in `docs/status.md`.

## Security boundaries

- Homepage reaches Docker only through a private socket proxy limited to
  read-only container queries.
- The raw Docker socket is never mounted into Homepage or published to the LAN.
- Aikido client credentials stay in ignored file-backed secrets and never enter
  Homepage configuration or responses.
- Grafana permits anonymous Viewer access on the trusted LAN; administrative
  access still requires credentials.
- Management services are not intentionally exposed to the public internet.
- Current HTTP endpoints rely on the trusted LAN boundary and do not yet use
  internal TLS.

## Current phase

Phases 0 through 4 are complete. Phase 5 is establishing a versioned runtime
health contract, truthful service checks, failure semantics, and operational
runbooks before Prometheus, hardware dashboards, logs, or additional nodes are
introduced.
