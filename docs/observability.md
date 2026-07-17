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
