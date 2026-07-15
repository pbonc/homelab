from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .status import _container_status


CONTAINERS = ("telemetry-collector", "influxdb", "grafana")


def _get_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not read {url}: {exc}") from exc


def _measurement(current: dict[str, Any], name: str) -> tuple[Any, str]:
    data = current.get("data") or {}
    measurement = (data.get("measurements") or {}).get(name) or {}
    return measurement.get("value", "unavailable"), measurement.get("unit", "")


def run_telemetry(base_url: str = "http://127.0.0.1:8000", json_output: bool = False) -> int:
    base_url = base_url.rstrip("/")
    containers = {name: _container_status(name) for name in CONTAINERS}
    try:
        health = _get_json(f"{base_url}/api/health")
        current = _get_json(f"{base_url}/api/current/weather")
    except RuntimeError as exc:
        print(f"[FAIL] Telemetry API: {exc}")
        return 1

    payload = {"containers": containers, "health": health, "weather": current}
    if json_output:
        print(json.dumps(payload, indent=2))
        return 0

    print("== Telemetry Platform ==")
    print()
    for name, state in containers.items():
        marker = "PASS" if state["status"] == "healthy" else "FAIL"
        print(f"[{marker}] {name}: {state['state']} / {state['health']}")
    print(f"[{'PASS' if health.get('status') == 'healthy' else 'FAIL'}] API: {health.get('status', 'unknown')}")
    print(f"[INFO] Active sources: {health.get('active_source_count', 0)}")
    print(f"[INFO] Last upload: {health.get('last_received_at') or 'none'}")
    print(f"[INFO] Weather freshness: {current.get('status', 'unknown')} ({current.get('age_seconds')}s old)")
    for label, field in (
        ("Outdoor temperature", "outdoor_temperature"),
        ("Outdoor humidity", "outdoor_humidity"),
        ("Wind speed", "wind_speed"),
        ("Rain rate", "rain_rate"),
    ):
        value, unit = _measurement(current, field)
        print(f"[INFO] {label}: {value} {unit}".rstrip())

    healthy = health.get("status") == "healthy" and all(
        state["status"] == "healthy" for state in containers.values()
    )
    return 0 if healthy else 1
