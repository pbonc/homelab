# Runtime Status Contract

## Purpose

`python -m labctl status` is the operator-facing runtime summary for the
homelab. Human output and `--json` use the same checks and overall-state
calculation. The JSON representation conforms to
`schemas/status-v1.schema.json`.

Repository-path checks remain context rather than runtime health signals.
Missing optional scaffolding must not imply that a deployed service is down.

## Versioning

The initial schema version is `1.0.0`. Additive optional detail fields may be
introduced without changing the major version. Removing or renaming fields,
changing their meaning, or changing status precedence requires a new major
schema.

Every document contains a UTC `generated_at` timestamp. Every check contains
an `observed_at` timestamp describing when its evidence was collected.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `healthy` | The check succeeded within its documented threshold |
| `degraded` | The service works but an actionable warning or partial failure exists |
| `stale` | The last valid application data is older than its documented threshold |
| `unavailable` | The check cannot be performed or has no usable evidence |
| `failed` | The check completed and found a service or contract failure |

`unavailable` is not a synonym for `failed`. For example, a Linux
`systemctl` check is unavailable on a Windows workstation, while an inactive
Docker service on `brain` is failed.

## Criticality and overall state

| Criticality | Current use |
| --- | --- |
| `critical` | Docker and Homepage; loss removes the primary control surface |
| `important` | Deployment metadata, telemetry storage and ingestion, Grafana, Aikido status, and the CI runner |
| `informational` | Supporting views such as Glances that do not define platform availability |

Overall-state precedence is:

1. `failed` when any critical check fails.
2. `unavailable` when every runtime check is unavailable.
3. `degraded` for any noncritical failure, degraded or stale check, or an
   unavailable critical check when other evidence is available.
4. `healthy` otherwise.

## Exit codes

| Code | Overall state | Automation meaning |
| --- | --- | --- |
| `0` | `healthy` or wholly `unavailable` | No confirmed actionable failure |
| `1` | `degraded` or `stale` | Actionable warning or partial failure |
| `2` | `failed` | Critical runtime failure |

Unsupported local-platform checks remain explicit in JSON but do not fail
automation without confirmed runtime evidence.

## Initial service inventory

| Check ID | Criticality | Owner | Evidence now | Planned evidence |
| --- | --- | --- | --- | --- |
| `docker.service` | Critical | Homelab operator | `systemctl is-active docker` | None |
| `homepage.container` | Critical | Homelab operator | Docker container health | HTTP latency and reachability |
| `glances.container` | Informational | Homelab operator | Docker container health | API freshness |
| `homepage.release` | Important | Homelab operator | Managed release metadata | Deployment-event correlation |
| `github.runner` | Important | Homelab operator | Not implemented | Host service state and last activity |
| `telemetry.collector` | Important | Homelab operator | Not implemented | Health endpoint and data freshness |
| `telemetry.influxdb` | Important | Homelab operator | Not implemented | Health endpoint and write readiness |
| `telemetry.grafana` | Important | Homelab operator | Not implemented | Health endpoint and response latency |
| `security.aikido` | Important | Homelab operator | Not implemented | Adapter health, cache freshness, and upstream state |

Thresholds for HTTP latency and stale data will be recorded only after the
initial probes are measured on `brain`.
