# Hardware Profile

## Controller Node: brain

- CPU: Intel Celeron N5095A
- Cores: 4
- Memory: 14 GB RAM
- Storage: ~100 GB NVMe
- OS target: Ubuntu 26.04 LTS

## Role in the Homelab

`brain` serves as the central control plane host for:

- Infrastructure automation execution
- CI/CD job orchestration endpoints
- Local service composition and testing
- Monitoring and operational visibility tooling

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

## Upgrade Considerations

Potential future upgrades to improve lab headroom:

- Increase NVMe capacity for logs, images, and state files
- Add RAM to support concurrent build and monitoring workloads
- Offload selected workloads to additional nodes once introduced
