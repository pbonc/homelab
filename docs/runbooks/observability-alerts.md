# Observability Alert Runbook

## Scope

Prometheus evaluates these alerts locally. There is no paging integration yet;
operators inspect active and pending alerts at
`http://192.168.1.23:9090/alerts`. Sustained `for` windows intentionally filter
container restarts and brief LAN interruptions.

## Homepage or service unavailable

1. Confirm the probe and its duration in Prometheus using
   `probe_success{service="<name>"}` and `probe_duration_seconds{service="<name>"}`.
2. Run `python3 -m labctl status` from the repository on `brain`.
3. Inspect the owning container with `docker inspect <container>` and
   `docker logs --tail 100 <container>`.
4. Restart only the affected Compose service after preserving useful logs.
5. Confirm the probe returns to `1`; document the cause if the alert reached
   firing state.

## Prometheus target down

1. Open `http://192.168.1.23:9090/targets` and identify the failed scrape.
2. Distinguish exporter failure from application failure: a blackbox target can
   be healthy while the probed application is not.
3. Check the target container, network, and mounted configuration.
4. Run `promtool check config` before restarting Prometheus after rule changes.

## Host resource pressure

1. Correlate the alert with the Brain Hardware dashboard and the relevant
   recording rule.
2. For CPU or memory, identify sustained consumers with `top` and
   `docker stats --no-stream`; do not kill processes solely from an alert.
3. For disk, use `df -h /` and identify growth by service or volume. Preserve
   state and logs before cleanup.
4. Escalate disk pressure at 90%; databases can fail before the filesystem is
   completely full.

## Slow HTTP probe

1. Compare the five-minute recording rule with raw `probe_duration_seconds`.
2. Check whether latency is isolated to one service or affects the entire LAN.
3. Review application logs and host saturation. Treat a single five-second
   startup timeout as noise unless the ten-minute alert window is satisfied.

## Initial baseline and thresholds

The 2026-07-19 baseline observed approximately 7% CPU, 10% memory, 17% root
disk, and normal average HTTP probe latency between 2 and 17 ms. Initial alerts
therefore use substantial headroom:

| Signal | Warning | Critical | Sustained window |
| --- | ---: | ---: | ---: |
| CPU | 85% | — | 15 minutes |
| Memory | 85% | — | 15 minutes |
| Root disk | 80% | 90% | 30 / 10 minutes |
| HTTP probe latency | 500 ms average | — | 10 minutes |
| Homepage failure | — | Failed | 2 minutes |
| Other service failure | Failed | — | 3 minutes |
| Prometheus scrape failure | Failed | — | 5 minutes |

Review thresholds after workload or storage changes. Alert changes require a
documented baseline and a `promtool` validation; do not tune merely to silence a
real incident.
