# Network Baseline

## Scope

This document defines initial network assumptions for the controller node and future homelab expansion.

## Current Assumptions

- `brain` is reachable on the local trusted network
- SSH will be the primary remote administration path
- Internal services are initially private to the homelab network

## Naming and Access

- Hostname standard starts with stable, human-readable names
- Controller node hostname: `brain`
- Future nodes should follow consistent role-oriented naming

## Port and Exposure Strategy

- Do not expose management services directly to the public internet
- Prefer reverse proxy and authentication boundaries for UI tools
- Document every externally reachable service and reason

## Future Topics

- VLAN segmentation strategy
- Internal DNS conventions
- Certificate and TLS management
- Network policy for container and Kubernetes workloads
