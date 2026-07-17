# Runtime Status Runbook

## Purpose

Use this runbook when `python3 -m labctl status` reports anything other than
`HEALTHY`, or when validating the Phase 5 status contract. Run checks directly
on `brain`; workstation execution intentionally reports runtime evidence as
`unavailable`.

## First response

Run both views and preserve the JSON output when investigating:

```bash
cd ~/git/homelab
python3 -m labctl status
python3 -m labctl status --json
echo $?
```

Exit codes:

- `0`: healthy, or no supported runtime evidence on this platform
- `1`: degraded, stale, or a noncritical failure
- `2`: confirmed critical failure

Do not restart every stack at once. Identify the first failed or stale check,
inspect its evidence, and change one component at a time.

## Docker or container failure

Inspect the host service and the affected container:

```bash
systemctl status docker --no-pager
docker ps --all
docker inspect CONTAINER --format '{{json .State}}'
docker logs --tail 100 CONTAINER
```

If Docker itself is inactive, capture its journal before restarting it:

```bash
journalctl --unit docker --since '-30 minutes' --no-pager
sudo systemctl restart docker
```

After recovery, confirm the expected Compose stacks rather than assuming
`restart: unless-stopped` restored every dependency.

## GitHub Actions runner failure

Discover and inspect the installed unit:

```bash
systemctl list-units --type=service --all --no-legend 'actions.runner.*'
systemctl status actions.runner.pbonc-homelab.brain.service --no-pager
journalctl --unit actions.runner.pbonc-homelab.brain.service --since '-30 minutes' --no-pager
```

Before restarting the runner, confirm that no deployment job is active. Restart
only the named unit, then verify it returns to `active (running)`.

## HTTP failure or high latency

Repeat the failing request locally on `brain`:

```bash
curl --fail --silent --show-error --max-time 3 URL
```

An HTTP failure with a healthy container usually indicates application
readiness, binding, or dependency trouble. A container failure and HTTP failure
together should be investigated from the container first.

Current local thresholds:

- Degraded when response latency exceeds 500 ms
- Failed when the request errors or exceeds 3 seconds

## Stale telemetry

The collector may be healthy while weather data is stale. Confirm the latest
receipt without exposing credentials:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
python3 -m labctl telemetry
```

Weather becomes stale after 180 seconds without a report. Check the Ecowitt
gateway, its customized-upload configuration, LAN reachability to port 8000,
and collector logs. Do not delete or rewrite historical measurements to repair
freshness.

## Stale or unavailable Aikido status

```bash
curl --fail --silent --show-error http://127.0.0.1:8010/api/status
docker logs --tail 100 security-status
```

The adapter may serve cached counts during an upstream failure. Never print its
secret files or access tokens while troubleshooting. Recreate the adapter only
after confirming its ignored secret files still exist.

## Invalid deployment metadata

Inspect, but do not hand-edit, the managed metadata:

```bash
python3 -m json.tool /srv/homelab/homepage/deployed.json
readlink -f /srv/homelab/homepage/current
readlink -f /srv/homelab/homepage/previous
```

Use `make homepage-deploy` or `make homepage-rollback` to restore managed
state. Manual edits can make the active Compose release disagree with recorded
metadata.

## Controlled acceptance exercises

Perform one exercise at a time and restore the component before continuing.
Capture the status output and exit code before, during, and after each exercise.

### Noncritical service-down exercise

Recovery command:

```bash
docker compose --env-file docker/security-status/.env --file docker/security-status/compose.yaml up --detach
```

Exercise:

```bash
docker compose --env-file docker/security-status/.env --file docker/security-status/compose.yaml stop security-status
python3 -m labctl status
echo $?
docker compose --env-file docker/security-status/.env --file docker/security-status/compose.yaml up --detach
python3 -m labctl status
```

Expected: `DEGRADED`, exit `1`, then `HEALTHY`.

### Runner-offline exercise

Do not run during an active workflow.

```bash
sudo systemctl stop actions.runner.pbonc-homelab.brain.service
python3 -m labctl status
echo $?
sudo systemctl start actions.runner.pbonc-homelab.brain.service
python3 -m labctl status
```

Expected: `DEGRADED`, exit `1`, then `HEALTHY`.

### Stale-data exercise

Use the deterministic unit test instead of interrupting the physical weather
station:

```bash
python3 -m unittest tests.test_status.StatusTests.test_http_probe_marks_old_telemetry_as_stale -v
```

Expected: the synthetic four-minute-old report is classified as `stale`.

### Unsupported-platform exercise

Run `python -m labctl status --json` from a non-Linux development workstation.

Expected: runtime checks are explicitly `unavailable`, overall state is
`unavailable`, and the exit code is `0` because no failure was confirmed.

## Acceptance record

| Scenario | Expected | Evidence |
| --- | --- | --- |
| Healthy baseline | Healthy / exit 0 | Passed on `brain`, 2026-07-17 |
| Stale telemetry classification | Deterministic stale state | Passed in automated tests |
| Unsupported workstation | Unavailable / exit 0 | Passed on Windows development workstation |
| Noncritical service down | Degraded / exit 1 / recovery | Pending controlled exercise |
| Runner offline | Degraded / exit 1 / recovery | Pending controlled exercise |
