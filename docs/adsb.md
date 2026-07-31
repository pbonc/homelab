# ADS-B Edge Node

The `piaware` Raspberry Pi at `192.168.1.27` is a dedicated ADS-B receiver.
It remains responsible for decoding and its existing PiAware services; Brain
only scrapes aggregate operational metrics.

## Discovery evidence

Read-only discovery on 2026-07-24 confirmed:

- `piaware`, `dump1090-fa`, and `lighttpd` were active and enabled.
- `/run/dump1090-fa/aircraft.json` was updating in under one second.
- The receiver was decoding aircraft and its message counter was increasing.
- The expected RTL2832U USB SDR was present.
- TCP port 9100 was available for the packaged Node Exporter.

The discovery intentionally did not collect feeder identifiers, receiver
coordinates, aircraft identities, callsigns, positions, or tracks.

## Metrics boundary

The Ansible-managed collector publishes only:

- decoder report age;
- aggregate visible-aircraft and last-minute aircraft counts;
- the cumulative decoder message counter;
- current registration-country counts inferred from ICAO address allocation;
- current operator counts inferred from a bounded callsign-prefix mapping;
- maximum, median, and 95th-percentile reception distance in nautical miles;
- expected SDR presence;
- receiver service state; and
- standard Node Exporter host metrics.

The collector writes an atomic Prometheus textfile every 15 seconds. If decoder
JSON cannot be read, the service fails and preserves the last valid file; the
generation timestamp then exposes staleness. Node Exporter listens only on the
Pi's trusted-LAN address. It is not intended for internet exposure.

## Deployment

From the Ubuntu WSL control environment:

```bash
cd /mnt/c/dev/homelab
export ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg"

make ansible-piaware-observability-check \
  ARGS="--limit piaware --private-key $HOME/.ssh/id_ed25519_homelab"

make ansible-piaware-observability \
  ARGS="--limit piaware --private-key $HOME/.ssh/id_ed25519_homelab"

make ansible-piaware-observability-check \
  ARGS="--limit piaware --private-key $HOME/.ssh/id_ed25519_homelab"
```

The final preview should report `changed=0`. Afterward, redeploy the
observability Compose model on Brain so Prometheus loads the `piaware-node`
scrape job.

## Verification

```bash
curl --fail --silent http://192.168.1.27:9100/metrics |
  grep '^piaware_'

curl --fail --silent \
  'http://192.168.1.23:9090/api/v1/query?query=up%7Bjob%3D%22piaware-node%22%7D'
```

The Prometheus query should return `1`. Do not add location labels or
per-aircraft fields to these metrics.

Country means the aircraft's inferred state of registration, not its departure,
destination, current location, owner, or operator. Operator counts are inferred
from recognized three-letter callsign prefixes and intentionally include an
`Unclassified` bucket. The classifier uses SkyAware's
locally installed ICAO range table and exports only aggregate counts.

Reception distance is calculated in memory from the locally installed receiver
position and current aircraft positions. Only aggregate distances and the count
of positioned aircraft are exported; neither endpoint's coordinates leave the
receiver.

## Grafana

The provisioned **ADS-B Receiver** dashboard is available at
`http://192.168.1.23:3001/d/homelab-adsb/ads-b-receiver`. It combines receiver
freshness, aggregate aircraft and message activity, SDR and service state, and
Pi host capacity. It deliberately has no map, coordinates, feeder identifier,
aircraft identifiers, callsigns, positions, or tracks.

## Buffering, restart, and retention

This integration reports current operational state; it is not an aircraft
event archive.

- `dump1090-fa` owns its runtime JSON under `/run`. The files are ephemeral and
  are recreated after boot.
- `piaware-metrics.timer` runs every 15 seconds with `Persistent=false`.
  Missed executions while the Pi is off are not replayed after startup.
- A successful collection atomically replaces `piaware.prom`. A failed
  collection preserves the last valid file, allowing the report and generation
  timestamps to become stale rather than replacing known-good data with a
  partial sample.
- Prometheus pulls the current Node Exporter surface. If the Pi, exporter, LAN,
  or Prometheus is unavailable, samples for that interval are absent and are
  not backfilled.
- Prometheus retains collected ADS-B and Pi hardware samples under the shared
  90-day or 10-GB policy, whichever limit is reached first.
- PiAware, `dump1090-fa`, Lighttpd, Node Exporter, and the metrics timer are
  enabled systemd units. A normal Pi restart should restore decoding,
  collection, and scraping without an operator-triggered replay.

Absence is therefore explicit: gaps mean no sample was collected, and stale
ages mean the last aggregate report is no longer current.

## Collector integration decision

ADS-B remains a Prometheus-only operational source. The generic Telemetry
Collector is intentionally not used because the current consumers need
bounded aggregate gauges and counters, Prometheus already supplies durable
history, and duplicating the same samples in InfluxDB would add another
failure path without a demonstrated consumer.

Revisit this boundary only when a non-Prometheus consumer, a durable
domain-event contract, or retention beyond the Prometheus policy is required.
Any future plugin must preserve the existing privacy boundary and must not turn
the telemetry platform into a per-aircraft or location archive.

## Operations and troubleshooting

Check the edge services and most recent collector run:

```bash
systemctl --no-pager --full status \
  piaware dump1090-fa lighttpd prometheus-node-exporter \
  piaware-metrics.timer

systemctl --no-pager --full status piaware-metrics.service
journalctl --unit piaware-metrics.service --since '-15 minutes' --no-pager
```

Inspect freshness without exposing aircraft details:

```bash
curl --fail --silent http://127.0.0.1:9100/metrics |
  grep -E '^piaware_(feed_report_age_seconds|metrics_generated_timestamp_seconds|service_up|sdr_present)'
```

If metrics are stale, verify in this order:

1. `dump1090-fa` is active and `/run/dump1090-fa/aircraft.json` has a recent
   modification time.
2. `piaware-metrics.timer` is active and its one-shot service has no recent
   error.
3. `prometheus-node-exporter` is listening on `192.168.1.27:9100`.
4. Prometheus reports `up{job="piaware-node"} == 1`.
5. `python3 -m labctl status` on Brain reports a current collector and decoder
   report.

Node Exporter binds only to the Pi's reserved LAN address. A systemd drop-in
waits up to two minutes for that address before each start, retries failures at
ten-second intervals, and disables systemd's rapid-start lockout. This handles
the observed boot sequence where PiAware obtained its Wi-Fi DHCP lease after
the packaged exporter had already exhausted its default restart attempts.

Do not delete `piaware.prom` during diagnosis: preserving it makes staleness
observable. Reapply the Ansible role if unit or exporter configuration has
drifted.

## Outage and recovery acceptance

The controlled drill in
[`docs/runbooks/piaware-outage.md`](runbooks/piaware-outage.md) stops only the
Pi decoder, verifies that the edge-node contract fails visibly, restores it
through a shell trap, and confirms recovery. It does not stop or modify Brain.

The exercise passed on 2026-07-24. With `dump1090-fa` stopped, the last valid
aggregate file was preserved as designed. After 78 seconds, `labctl status`
classified `adsb.piaware.metrics` as stale, reported the Homelab as degraded,
and returned `OUTAGE_EXIT=1` while every unrelated service remained healthy.
The trap restored the decoder; all four edge units returned active, fresh
metrics resumed, and the recovery status returned `RECOVERY_EXIT=0` without
restarting Prometheus, Grafana, or Brain.
