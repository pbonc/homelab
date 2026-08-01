from __future__ import annotations

import base64
import urllib.request
from pathlib import Path


def publish_unknown_device(
    device: dict[str, str | bool | None],
    *,
    url: str,
    username: str,
    password_file: Path,
    timeout_seconds: int = 10,
) -> None:
    password = password_file.read_text(encoding="utf-8").strip()
    credentials = base64.b64encode(
        f"{username}:{password}".encode("utf-8")
    ).decode("ascii")
    qualifiers = []
    if device.get("address"):
        qualifiers.append(f"IP {device['address']}")
    if device.get("hostname"):
        qualifiers.append(f"hostname {device['hostname']}")
    if device.get("vendor"):
        qualifiers.append(f"vendor {device['vendor']}")
    if device.get("private_address"):
        qualifiers.append("private/randomized MAC")
    detail = "; ".join(qualifiers) if qualifiers else "no IP, hostname, or vendor reported"
    message = (
        f"{device['mac']} was repeatedly observed on the trusted LAN; {detail}."
    )
    request = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "text/plain; charset=utf-8",
            "Title": "Unknown device detected",
            "Priority": "4",
            "Tags": "warning,computer",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 300:
            raise RuntimeError(f"ntfy returned HTTP {response.status}")
