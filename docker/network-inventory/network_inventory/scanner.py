from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
import ipaddress
from pathlib import Path

from .store import Observation


def parse_nmap_xml(payload: str) -> list[Observation]:
    root = ET.fromstring(payload)
    observations: list[Observation] = []
    for host in root.findall("host"):
        status = host.find("status")
        if status is None or status.get("state") != "up":
            continue
        addresses = {
            item.get("addrtype"): item
            for item in host.findall("address")
            if item.get("addr")
        }
        ipv4 = addresses.get("ipv4")
        mac = addresses.get("mac")
        if ipv4 is None or mac is None:
            continue
        hostname_element = host.find("./hostnames/hostname")
        observations.append(
            Observation(
                mac=mac.get("addr", ""),
                address=ipv4.get("addr", ""),
                hostname=(
                    hostname_element.get("name")
                    if hostname_element is not None
                    else None
                ),
                vendor=mac.get("vendor"),
            )
        )
    return observations


def parse_arp_table(payload: str, network: str) -> list[Observation]:
    subnet = ipaddress.ip_network(network, strict=True)
    observations: list[Observation] = []
    for line in payload.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 6:
            continue
        address, _hardware_type, flags, mac, _mask, _device = fields[:6]
        try:
            parsed_address = ipaddress.ip_address(address)
            complete = int(flags, 16) & 0x2
        except ValueError:
            continue
        if (
            parsed_address not in subnet
            or not complete
            or mac == "00:00:00:00:00:00"
        ):
            continue
        observations.append(Observation(mac=mac, address=address))
    return observations


def scan(
    network: str,
    *,
    timeout_seconds: int = 50,
    arp_path: Path = Path("/proc/net/arp"),
) -> list[Observation]:
    result = subprocess.run(
        ["nmap", "--unprivileged", "-sn", "-n", "-oX", "-", network],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "no error detail"
        raise RuntimeError(f"nmap exited {result.returncode}: {detail}")
    return parse_arp_table(arp_path.read_text(encoding="ascii"), network)
