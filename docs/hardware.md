# Hardware Profile

## Controller Node: brain

- CPU: Intel Celeron N5095A
- Cores: 4
- Memory: 14 GB RAM
- Storage: Lexar NM620 1 TB NVMe; Ubuntu root logical volume is ~98 GB
- OS target: Ubuntu 26.04 LTS

## Role in the Homelab

`brain` serves as the central control plane host for:

- Infrastructure automation execution
- CI/CD job orchestration endpoints
- Local service composition and testing
- Monitoring and operational visibility tooling

## ADS-B Edge Node: piaware

- Model: Raspberry Pi 4 Model B Rev 1.4
- Architecture: AArch64
- Memory card: approximately 64 GB; root filesystem approximately 58 GB
- OS: Raspbian GNU/Linux 12 (Bookworm)
- Network address: `192.168.1.27`
- SDR: Realtek RTL2832U DVB-T USB receiver
- Workload: PiAware, `dump1090-fa`, and FlightAware feeder client

The receiver was verified with key-based SSH. The SDR is visible over USB,
`dump1090-fa` is producing local ADS-B data, and PiAware is connected upstream.
The private feeder identifier is intentionally excluded from repository
documentation.

## Capacity Notes

Given the current hardware footprint:

- Keep service density moderate
- Use lightweight workloads first
- Monitor memory and disk utilization before adding heavy services
- Prioritize reliability and reproducibility over workload count

## Current Monitoring

Glances runs alongside Homepage with host PID visibility and a read-only root filesystem mount. Homepage uses its internal API to display controller identity, CPU, memory, and root filesystem utilization on the `brain` card.

Glances refreshes the displayed metrics every five seconds. The card is classified after a 15-second continuous-data-loss grace period, so a single widget refresh does not cause a red status flash:

- Green: metrics are available and CPU, memory, and root filesystem usage are below 85%
- Yellow: the node is active but one or more metrics are at or above 85%
- Red: one or more metrics are at or above 95%, or required metrics are unavailable

Prometheus also scrapes Node Exporter every 15 seconds for durable host history.
Verified metric coverage includes:

- Four CPU cores, utilization counters, frequency, and throttling
- 15.996 GB physical memory and swap, cache, and pressure-related counters
- Root, boot, and EFI filesystem capacity plus NVMe disk I/O
- The active `enp3s0` Ethernet interface and its traffic and error counters
- CPU package and per-core temperatures from `platform_coretemp_0`
- NVMe composite and sensor temperatures from `nvme_nvme0`
- ACPI, Wi-Fi, and Ethernet-controller thermal readings

The physical NVMe device is approximately 1 TB, but the root logical volume is
approximately 98 GB. Capacity dashboards and alerts must use the mounted root
filesystem rather than assume the full physical device is allocated.

## Upgrade Considerations

Potential future upgrades to improve lab headroom:

- Increase NVMe capacity for logs, images, and state files
- Add RAM to support concurrent build and monitoring workloads
- Offload selected workloads to additional nodes once introduced
