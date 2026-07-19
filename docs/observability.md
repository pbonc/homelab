# Metrics and Observability

## Metrics foundation

The initial observability stack runs Prometheus and Node Exporter on `brain`.
Prometheus is available only on the trusted LAN at
`http://192.168.1.23:9090`; Node Exporter is reachable only from the private
Compose network and is not published to the host or LAN.

The stack source lives in `docker/observability/` and uses digest-pinned images.
Both containers drop all Linux capabilities, prevent privilege escalation, and
use read-only root filesystems. Node Exporter receives read-only host views of
`/proc`, `/sys`, and `/` so it can report host rather than container metrics.

## Storage and retention

Prometheus stores its time-series database in the `prometheus-data` named
volume. Samples are retained for at most 90 days or 10 GB, whichever limit is
reached first. The size cap protects the roughly 100 GB system disk while the
time cap makes the intended history explicit. Review actual growth after a
representative baseline before increasing either limit.

The named volume survives container recreation and `docker compose down`. Do
not use `docker compose down --volumes` during routine maintenance.

## Operations

Validate and start the stack from the repository root:

```bash
make observability-config
make observability-up
```

Verify both scrape targets through Prometheus:

```bash
curl --fail --silent --show-error http://192.168.1.23:9090/-/ready
curl --fail --silent --show-error \
  'http://192.168.1.23:9090/api/v1/query?query=up'
```

Expected targets are `prometheus` and `node`, both with value `1`. Inspect the
stack with:

```bash
docker compose --file docker/observability/compose.yaml ps
docker compose --file docker/observability/compose.yaml logs --tail 100
```

Stop the containers without deleting stored metrics:

```bash
make observability-down
```

## Deployment record

The initial deployment on `brain` passed on 2026-07-17. Prometheus reported
ready, and both the `prometheus` and `node` scrape targets reported `up` with no
scrape errors.

## Verified `brain` selectors

Use `instance="brain"` for host panels. The primary hardware selectors are:

- CPU: `node_cpu_seconds_total` and `node_cpu_scaling_frequency_hertz`
- Memory: `node_memory_MemTotal_bytes` and `node_memory_MemAvailable_bytes`
- Root capacity: `node_filesystem_*{mountpoint="/"}`
- NVMe I/O: `node_disk_*{device="nvme0n1"}`
- LAN traffic: `node_network_*{device="enp3s0"}`
- CPU package temperature: `node_thermal_zone_temp{type="x86_pkg_temp"}`
- NVMe temperatures: `node_hwmon_temp_celsius{chip="nvme_nvme0"}`

Docker bridge and `veth` interfaces should be excluded from host-level network
panels unless container-network behavior is the subject of the panel.

## Grafana hardware dashboard

Grafana provisions the `Brain Hardware` dashboard at
`/d/homelab-hardware/brain-hardware`. It contains current CPU, memory, root
filesystem, CPU package temperature, NVMe temperature, and uptime cards plus
historical utilization, capacity, disk throughput, LAN traffic, and temperature
panels.

The initial deployment passed on `brain` on 2026-07-17. Grafana loaded all 12
panels, inserted the `prometheus-homelab` datasource, and its datasource health
check successfully queried the Prometheus API.

## Availability and freshness

Blackbox Exporter probes the public HTTP health surface of Homepage, the
Telemetry Collector, InfluxDB, Grafana, Aikido status, and Prometheus every 15
seconds. The exporter is internal to the observability Compose network; only
Prometheus queries it.

The Telemetry Collector independently publishes Prometheus metrics at
`/metrics` for storage reachability, latest-report timestamp, report age, and
the configured stale classification. This keeps two failure modes distinct:

- `probe_success == 0`: the service endpoint cannot complete its HTTP contract
- `probe_success == 1` with `telemetry_source_stale == 1`: the collector is
  reachable, but its latest weather report is too old

Grafana provisions these signals in the `Platform Health` dashboard at
`/d/homelab-platform-health/platform-health`.

The initial deployment passed on `brain` on 2026-07-19. All six HTTP probes
reported `probe_success == 1`, telemetry storage reported up, the live weather
report was current, and Grafana loaded all five Platform Health panels.
