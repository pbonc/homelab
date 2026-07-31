from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass
from pathlib import Path


MAC_PATTERN = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")
ALLOWED_KINDS = {
    "gateway",
    "controller",
    "adsb-edge",
    "server",
    "client",
    "iot",
    "printer",
    "unknown",
}


def normalize_mac(value: str) -> str:
    normalized = value.strip().lower().replace("-", ":")
    if not MAC_PATTERN.fullmatch(normalized):
        raise ValueError("invalid MAC address")
    return normalized


def is_private_mac(value: str) -> bool:
    first_octet = int(normalize_mac(value).split(":", 1)[0], 16)
    return bool(first_octet & 0x02)


@dataclass(frozen=True)
class KnownDevice:
    id: str
    name: str
    kind: str
    address: str | None
    mac: str | None


class KnownInventory:
    def __init__(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0.0":
            raise ValueError("unsupported known-device schema version")
        devices = []
        for item in payload.get("devices", []):
            address = item.get("address")
            if address is not None:
                ipaddress.ip_address(address)
            mac = normalize_mac(item["mac"]) if item.get("mac") else None
            kind = str(item["kind"])
            if kind not in ALLOWED_KINDS:
                raise ValueError(f"unsupported device kind: {kind}")
            devices.append(
                KnownDevice(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    kind=kind,
                    address=address,
                    mac=mac,
                )
            )
        ids = [device.id for device in devices]
        macs = [device.mac for device in devices if device.mac]
        if len(ids) != len(set(ids)) or len(macs) != len(set(macs)):
            raise ValueError("duplicate known-device identity")
        self.devices = tuple(devices)
        self.by_mac = {device.mac: device for device in devices if device.mac}
        self.by_address = {
            device.address: device for device in devices if device.address
        }
