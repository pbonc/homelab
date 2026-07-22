# Network Baseline

## Scope

This document records the verified network exposure of the controller and the
assumptions that future nodes and services must preserve.

## Trusted network

- Controller hostname: `brain`
- Controller address: `192.168.1.23`
- ADS-B edge hostname: `piaware`
- ADS-B edge address: `192.168.1.27`
- Current client network: trusted home LAN
- Primary administration path: SSH
- Public inbound exposure: none intended

Services currently bind plain HTTP to the LAN. The trusted-network boundary is
therefore part of their security model; ports must not be forwarded from the
internet without a deliberate authenticated reverse-proxy and TLS design.

## LAN endpoints

| Port | Service | Address | Access and purpose |
| ---: | --- | --- | --- |
| 22 | SSH | `dar@192.168.1.23` | Administrative access using public-key authentication |
| 3000 | Homepage | `http://192.168.1.23:3000` | Primary control surface |
| 8000 | Telemetry Collector | `http://192.168.1.23:8000` | Ecowitt ingestion and telemetry APIs |
| 8086 | InfluxDB | `http://192.168.1.23:8086` | Time-series API and administration |
| 3001 | Grafana | `http://192.168.1.23:3001` | Anonymous Viewer dashboards; authenticated administration |
| 8020 | Study Deck | `http://192.168.1.23:8020` | LAN-only study notes, quizzes, and local progress |
| 9090 | Prometheus | `http://192.168.1.23:9090` | Metrics queries and administration on the trusted LAN |
| 3100 | Loki | `http://192.168.1.23:3100` | Log query API consumed by trusted-LAN Grafana |

## Managed nodes

| Host | Address | Role | Administration |
| --- | --- | --- | --- |
| `brain` | `192.168.1.23` | Controller and service host | `dar`, public-key SSH |
| `piaware` | `192.168.1.27` | ADS-B receiver edge node | Temporary `pi` bootstrap account, public-key SSH |

All entries are trusted-LAN only. Homepage links should use these verified
addresses; planned services must not receive click targets.

## Private container endpoints

| Service | Private endpoint | Consumer |
| --- | --- | --- |
| Glances | `http://glances:61208` | Homepage |
| Docker socket proxy | `http://docker-proxy:2375` | Homepage |
| InfluxDB | `http://influxdb:8086` | Telemetry Collector and Grafana |

The Docker proxy is not published on the host. Glances also remains private to
the Homepage Compose network even though Homepage exposes its derived host
metrics.

## Expected traffic

### Inbound on the LAN

- Browser clients access Homepage, Grafana, InfluxDB, and telemetry APIs.
- The Ecowitt gateway sends weather reports to port 8000.
- Operators administer `brain` over SSH.

### Outbound from `brain`

- The GitHub Actions runner maintains its GitHub service connection.
- Docker pulls explicitly configured images from their registries.

The dormant Aikido adapter makes no outbound API calls. Aikido continues to scan
the repository through its GitHub App integration.

## Naming and future nodes

- Hostnames are stable, lowercase, and role-oriented.
- `brain` remains the controller identity.
- `piaware` is the role-oriented hostname for the ADS-B Raspberry Pi; its
  verified LAN address is `192.168.1.27`.
- `atlas` remains an inventory placeholder until hardware and networking are
  verified.

## Change requirements

Before exposing a new port or address:

1. Identify the owning service and operator.
2. Define whether it is private-container, trusted-LAN, or public.
3. Add a supported health check and document authentication.
4. Update this endpoint inventory and Homepage only after verification.
5. For any public exposure, add TLS, authentication, rate limiting, and a
   documented reason.

## Future network work

- Internal DNS conventions
- Certificate and TLS management
- VLAN segmentation for trusted clients, servers, IoT devices, and lab targets
- Firewall policy for controller, edge nodes, and container workloads
- Network policy if Kubernetes is eventually justified
