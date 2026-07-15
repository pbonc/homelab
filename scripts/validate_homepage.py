#!/usr/bin/env python3
"""Validate Homepage's truthful-dashboard configuration without extra packages."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docker" / "homepage" / "config"
TEXT_FILES = [
    ROOT / "Makefile",
    ROOT / "docker" / "homepage" / "compose.yaml",
    ROOT / "docker" / "homepage" / "version.env",
    *sorted(CONFIG.glob("*.yaml")),
    *sorted(CONFIG.glob("*.css")),
    *sorted(CONFIG.glob("*.js")),
]


def read_utf8(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        errors.append(f"{path.relative_to(ROOT)} is not valid UTF-8: {exc}")
        return ""


def service_cards(text: str) -> list[tuple[str, dict[str, str]]]:
    cards: list[tuple[str, dict[str, str]]] = []
    name: str | None = None
    fields: dict[str, str] = {}

    for line in text.splitlines():
        match = re.match(r"^    - ([^:]+):\s*$", line)
        if match:
            if name is not None:
                cards.append((name, fields))
            name = match.group(1)
            fields = {}
            continue

        field = re.match(r'^        ([a-zA-Z]+):\s*["\']?(.*?)["\']?\s*$', line)
        if name is not None and field:
            fields[field.group(1)] = field.group(2)

    if name is not None:
        cards.append((name, fields))
    return cards


def main() -> int:
    errors: list[str] = []
    contents = {path: read_utf8(path, errors) for path in TEXT_FILES}
    services_path = CONFIG / "services.yaml"
    services = contents[services_path]

    if any(marker in text for text in contents.values() for marker in ("Ã", "â€", "âš", "ðŸ")):
        errors.append("configuration contains likely mojibake")

    cards = service_cards(services)
    if not cards:
        errors.append("services.yaml contains no service cards")

    real_links = 0
    for name, fields in cards:
        description = fields.get("description", "")
        href = fields.get("href")
        if ("Planned |" in description or "Future |" in description) and href:
            errors.append(f"{name} is not deployed but has a click target: {href}")
        if href:
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{name} has an invalid URL: {href}")
            if parsed.hostname and parsed.hostname.endswith(".local"):
                errors.append(f"{name} uses a placeholder .local URL: {href}")
            real_links += 1

    if real_links == 0:
        errors.append("services.yaml contains no real click targets")

    for path, text in contents.items():
        if path.suffix != ".yaml":
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = re.match(r"^\s*(?:href|siteMonitor|url):\s*[\"']?(.*?)[\"']?\s*$", line)
            if not match:
                continue
            href = match.group(1)
            parsed = urlparse(href)
            location = f"{path.relative_to(ROOT)}:{line_number}"
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{location} has an invalid URL: {href}")
            if parsed.hostname and parsed.hostname.endswith(".local"):
                errors.append(f"{location} uses a placeholder .local URL: {href}")

    custom_js = contents[CONFIG / "custom.js"]
    for retired_reference in ("status.json", "setInterval", "innerText"):
        if retired_reference in custom_js:
            errors.append(f"custom.js still contains retired status logic: {retired_reference}")

    makefile = contents[ROOT / "Makefile"]
    if "homepage-status:" in makefile:
        errors.append("Makefile still exposes the unsupported Homepage JSON export")

    version_env = contents[ROOT / "docker" / "homepage" / "version.env"]
    if not re.search(r"^HOMEPAGE_VAR_DASHBOARD_VERSION=\d+\.\d+\.\d+$", version_env, re.MULTILINE):
        errors.append("version.env must define a semantic dashboard version")
    if "{{HOMEPAGE_VAR_DASHBOARD_VERSION}}" not in services:
        errors.append("Homepage card does not display the dashboard version")

    compose = contents[ROOT / "docker" / "homepage" / "compose.yaml"]
    if re.search(r"^\s*image:\s*\S*:latest(?:-full)?\s*$", compose, re.MULTILINE):
        errors.append("compose.yaml uses a mutable latest image tag")
    for image in re.findall(r"^\s*image:\s*(\S+)\s*$", compose, re.MULTILINE):
        if "@sha256:" not in image:
            errors.append(f"compose.yaml image is not digest-pinned: {image}")
    if "HOMEPAGE_ALLOWED_HOSTS=*" in compose:
        errors.append("compose.yaml permits wildcard Homepage host headers")
    if "HOMEPAGE_ALLOWED_HOSTS=192.168.1.23:3000,brain:3000" not in compose:
        errors.append("compose.yaml does not define the trusted Homepage hosts")
    if "http://127.0.0.1:3000/api/healthcheck" not in compose:
        errors.append("compose.yaml does not define the Homepage API healthcheck")
    if "/var/run/docker.sock:/var/run/docker.sock:ro" not in compose:
        errors.append("compose.yaml does not mount the Docker socket read-only into its proxy")
    if "POST=0" not in compose or "CONTAINERS=1" not in compose:
        errors.append("compose.yaml does not restrict the Docker socket proxy to read-only container access")
    if re.search(r"homepage:\s.*?/var/run/docker.sock", compose, re.DOTALL):
        homepage_block = compose.partition("  docker-proxy:")[0]
        if "/var/run/docker.sock" in homepage_block:
            errors.append("Homepage service mounts the Docker socket directly")

    docker_config = contents[CONFIG / "docker.yaml"]
    if "host: docker-proxy" not in docker_config or "port: 2375" not in docker_config:
        errors.append("docker.yaml does not use the restricted Docker socket proxy")
    if "server: brain-docker" not in services or "container: homepage" not in services:
        errors.append("Homepage card does not use Docker integration")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    print(f"[PASS] Homepage configuration: {len(cards)} cards, {real_links} real links, UTF-8 clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
