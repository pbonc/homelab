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
