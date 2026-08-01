# Network Inventory and Topology Contract

## Purpose

The network inventory watcher detects devices on the trusted home `/24`,
persists first-seen and last-seen state, and identifies repeatedly observed
unknown devices for notification. Its read-only topology API also supplies the
Homepage network map.

Discovery and presentation are separate concerns. The watcher owns identity,
state, confirmation, and evidence. The Homepage owns layout and interaction.
Changing graph libraries must never require migrating scanner state.

## Truth boundary

ARP and bounded host discovery can demonstrate that an address and MAC were
observed on the local broadcast domain. They cannot prove a physical switch
port, Wi-Fi access point, cable, or traffic path. The initial topology therefore
contains:

- declared infrastructure nodes such as the router, `brain`, and `piaware`;
- one shared trusted-LAN segment;
- observed clients attached to that segment; and
- declared service-hosting edges where repository configuration is the source.

Every edge records its source as `declared` or `observed`. The API does not emit
speculative physical relationships merely to make the visualization attractive.

## Version 1 API

`GET /api/v1/topology` returns:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-07-31T00:00:00Z",
  "discovery": {
    "state": "healthy",
    "last_completed_at": "2026-07-31T00:00:00Z",
    "network": "192.168.1.0/24"
  },
  "nodes": [
    {
      "id": "host-brain",
      "name": "brain",
      "kind": "controller",
      "status": "online",
      "known": true,
      "addresses": ["192.168.1.23"],
      "mac": null,
      "vendor": null,
      "first_seen_at": "2026-07-31T00:00:00Z",
      "last_seen_at": "2026-07-31T00:00:00Z",
      "source": "declared"
    }
  ],
  "edges": [
    {
      "id": "lan-brain",
      "source_id": "segment-trusted-lan",
      "target_id": "host-brain",
      "kind": "membership",
      "evidence": "declared"
    }
  ]
}
```

Node identifiers are stable and are not derived from a current IP address.
Addresses may change without creating a new node. Timestamps are UTC RFC 3339.
The API is read-only, credential-free on the trusted LAN, and contains no
router credentials, notification credentials, traffic contents, or cloud vendor
lookups.

`GET /api/v1/health` reports API and discovery freshness separately. A working
API with an old scan is `stale`, not healthy and not unavailable.

## Identity and confirmation

The initial durable identity is the normalized MAC address. Known devices map
that identity to a stable repository-managed name and kind. Unknown devices
receive an opaque stable node ID and remain unacknowledged until explicitly
added to the known inventory.

A new-device event requires sightings in at least two completed scans separated
by a confirmation interval. A single sighting never pages the phone. One
identity generates one notification until it is acknowledged or expires and is
later rediscovered under an explicit re-notification policy.

Locally administered MAC addresses are labeled as private/randomized. They use a
longer confirmation window and conservative notification policy. Ordinary
departures and address changes update the map but do not create immediate phone
notifications.

## Persistence

SQLite stores devices, addresses, observations, notification state, and scan
runs. Writes are transactional. The database survives container recreation and
is included in encrypted backup and restore tests. Raw scan output is not
retained after observations are normalized.

The service runs a bounded, unprivileged Nmap host-discovery sweep of only
`192.168.1.0/24` once per minute, then reads Brain's resulting kernel ARP table.
Host networking makes that neighbor table reflect the controller's LAN. The
container remains non-root, drops every Linux capability, and is not run with
Docker's privileged mode. It performs no port scan, DNS lookup, cloud lookup,
or traffic capture.

When an unknown device crosses its confirmation threshold, the service
publishes one authenticated message to the existing `homelab-alerts` topic and
records delivery in SQLite. A failed publish remains pending and is retried
after the next scan; routine offline transitions do not notify.

The first completed scan containing at least one device is a silent baseline:
empty or failed startup scans cannot consume it. Existing unknown devices
appear in inventory but never generate a delayed notification merely because
the watcher was installed. Devices first observed after that baseline follow
the normal confirmation policy.

## Network Inventory Lab

The service hosts a standalone, credential-free LAN interface at
`http://192.168.1.23:8030/`. Homepage links to it from the monitored Network
Inventory card rather than injecting custom elements into Homepage's internal
layout.

The lab shows summary counts, evidence-backed shared-LAN membership, and a
focused table of unidentified devices with current IP, MAC address, first seen,
last seen, status, and private/randomized-MAC indication. Operator working
labels and connection classifications remain in that browser's local storage
and are saved only through an explicit Apply action. They are never promoted to
trusted server state automatically. After verifying an identity, the operator
can copy a proposed JSON record into the repository-managed known-device
inventory.

The unidentified-device table is sorted by numeric IPv4 address. An Apply
operation improves only the local investigation view. Moving a device from
unidentified to identified is intentionally a GitOps change: copy its proposed
record into `docker/network-inventory/config/known-devices.json`, review and
commit it, then redeploy Network Inventory.

Ethernet and Wi-Fi groupings are either declared in the known-device inventory
or classified by the operator. ARP cannot determine the connection medium, so
unclassified devices remain explicitly unknown. Manufacturer clues come from
Nmap's packaged local OUI database without a cloud lookup. Active OS
fingerprinting and port scanning remain disabled; adding either would require a
separate security and accuracy decision.

The UI polls the versioned topology API every 30 seconds. It uses no graph
library, external assets, cloud service, or administrative credentials.
