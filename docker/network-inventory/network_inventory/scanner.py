from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET

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


def scan(network: str, *, timeout_seconds: int = 50) -> list[Observation]:
    result = subprocess.run(
        ["nmap", "--privileged", "-sn", "-n", "-oX", "-", network],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "no error detail"
        raise RuntimeError(f"nmap exited {result.returncode}: {detail}")
    return parse_nmap_xml(result.stdout)
