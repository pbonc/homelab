# PiAware Outage and Recovery

Use this controlled exercise to prove that an ADS-B decoder outage is visible
and that recovery does not require restarting the controller. Run it from the
Ubuntu WSL control environment. The drill briefly interrupts local decoding
and external feeding on `piaware`; it does not alter Brain.

## Preconditions

- The production inventory resolves `piaware` to `192.168.1.27`.
- The Homelab administrator key can connect as `dar`.
- `python3 -m labctl status` on Brain is healthy before the drill.
- No receiver maintenance or package upgrade is in progress.

Verify the baseline:

```bash
ssh -o BatchMode=yes \
  -i "$HOME/.ssh/id_ed25519_homelab" \
  dar@192.168.1.27 \
  'systemctl is-active dump1090-fa piaware-metrics.timer prometheus-node-exporter'

ssh -o BatchMode=yes \
  -i "$HOME/.ssh/id_ed25519_homelab" \
  dar@192.168.1.23 \
  'cd ~/git/homelab && python3 -m labctl status'
```

All four edge units and the overall Homelab status must be healthy before
continuing.

## Controlled outage

Run the following as one block. The local trap restores the decoder when the
block finishes or is interrupted, while the Brain status check occurs during
the outage:

```bash
PIAWARE_KEY="$HOME/.ssh/id_ed25519_homelab"

restore_decoder() {
  ssh -o BatchMode=yes \
    -i "$PIAWARE_KEY" \
    dar@192.168.1.27 \
    'sudo systemctl start dump1090-fa'
}
trap restore_decoder EXIT HUP INT TERM

ssh -o BatchMode=yes \
  -i "$PIAWARE_KEY" \
  dar@192.168.1.27 \
  'sudo systemctl stop dump1090-fa'

sleep 20

ssh -o BatchMode=yes \
  -i "$PIAWARE_KEY" \
  dar@192.168.1.23 \
  'cd ~/git/homelab; python3 -m labctl status'
outage_exit=$?
echo "OUTAGE_EXIT=$outage_exit"

restore_decoder
trap - EXIT HUP INT TERM
```

Expected evidence:

- `adsb.piaware.metrics` becomes failed because `dump1090-fa` is down, or stale
  if observation occurs after collection stops producing current data;
- the PiAware Homepage card becomes critical or unavailable after its refresh;
- Brain and unrelated Homelab services remain available; and
- the status command returns a nonzero actionable result.

## Recovery verification

Allow up to 60 seconds for the decoder, aggregate collector, Prometheus scrape,
Homepage refresh, and status probe to converge:

```bash
ssh -o BatchMode=yes \
  -i "$HOME/.ssh/id_ed25519_homelab" \
  dar@192.168.1.27 \
  'systemctl is-active dump1090-fa piaware piaware-metrics.timer prometheus-node-exporter'

sleep 60

ssh -o BatchMode=yes \
  -i "$HOME/.ssh/id_ed25519_homelab" \
  dar@192.168.1.23 '
    cd ~/git/homelab
    python3 -m labctl status
    echo "RECOVERY_EXIT=$?"
  '
```

Acceptance requires:

- every listed edge service reports `active`;
- `adsb.piaware.metrics` is healthy with report and collector ages below 60
  seconds;
- `RECOVERY_EXIT=0`;
- the PiAware Homepage card returns to active; and
- the ADS-B Grafana dashboard resumes without restarting Prometheus, Grafana,
  or Brain.

If recovery fails, start `dump1090-fa` explicitly and use the troubleshooting
sequence in [`docs/adsb.md`](../adsb.md). Do not reboot Brain as part of this
exercise.
