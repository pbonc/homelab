from __future__ import annotations

import hashlib
import ipaddress
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import KnownInventory, is_private_mac, normalize_mac


SCHEMA_VERSION = "1.0.0"


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def opaque_id(mac: str) -> str:
    digest = hashlib.sha256(normalize_mac(mac).encode("ascii")).hexdigest()
    return f"device-{digest[:12]}"


@dataclass(frozen=True)
class Observation:
    mac: str
    address: str
    hostname: str | None = None
    vendor: str | None = None

    def normalized(self) -> "Observation":
        mac = normalize_mac(self.mac)
        address = str(ipaddress.ip_address(self.address))
        hostname = self.hostname.strip()[:120] if self.hostname else None
        vendor = self.vendor.strip()[:120] if self.vendor else None
        return Observation(mac=mac, address=address, hostname=hostname, vendor=vendor)


class InventoryStore:
    def __init__(
        self,
        path: Path,
        known: KnownInventory,
        *,
        network: str = "192.168.1.0/24",
        confirmation_seconds: int = 300,
        private_confirmation_seconds: int = 1800,
        offline_seconds: int = 300,
        stale_seconds: int = 300,
    ) -> None:
        self.path = path
        self.known = known
        self.network = str(ipaddress.ip_network(network, strict=True))
        self.confirmation_seconds = confirmation_seconds
        self.private_confirmation_seconds = private_confirmation_seconds
        self.offline_seconds = offline_seconds
        self.stale_seconds = stale_seconds
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    completed_at TEXT NOT NULL,
                    network TEXT NOT NULL,
                    state TEXT NOT NULL,
                    observation_count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS devices (
                    mac TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL UNIQUE,
                    hostname TEXT,
                    vendor TEXT,
                    private_address INTEGER NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    sightings INTEGER NOT NULL,
                    confirmed_at TEXT,
                    notification_sent_at TEXT
                );
                CREATE TABLE IF NOT EXISTS addresses (
                    mac TEXT NOT NULL,
                    address TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (mac, address),
                    FOREIGN KEY (mac) REFERENCES devices(mac) ON DELETE CASCADE
                );
                """
            )

    def record_scan(
        self,
        observations: list[Observation],
        *,
        completed_at: datetime,
    ) -> dict[str, int]:
        when = utc_text(completed_at)
        normalized_items = [item.normalized() for item in observations]
        normalized = {item.mac: item for item in normalized_items}
        network = ipaddress.ip_network(self.network)
        if any(ipaddress.ip_address(item.address) not in network for item in normalized.values()):
            raise ValueError("observation is outside configured network")

        newly_confirmed = 0
        with self._connect() as connection:
            baseline = (
                connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
                == 0
            )
            connection.execute(
                """INSERT INTO scan_runs
                   (completed_at, network, state, observation_count)
                   VALUES (?, ?, 'completed', ?)""",
                (when, self.network, len(normalized)),
            )
            for item in normalized.values():
                existing = connection.execute(
                    "SELECT * FROM devices WHERE mac = ?", (item.mac,)
                ).fetchone()
                known = self.known.by_mac.get(item.mac) or self.known.by_address.get(
                    item.address
                )
                node_id = known.id if known else opaque_id(item.mac)
                private = int(is_private_mac(item.mac))
                if existing is None:
                    connection.execute(
                        """INSERT INTO devices
                           (mac, node_id, hostname, vendor, private_address,
                            first_seen_at, last_seen_at, sightings,
                            notification_sent_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                        (
                            item.mac,
                            node_id,
                            item.hostname,
                            item.vendor,
                            private,
                            when,
                            when,
                            when if baseline and known is None else None,
                        ),
                    )
                    first_seen = completed_at
                    sightings = 1
                    confirmed_at = None
                else:
                    first_seen = parse_utc(existing["first_seen_at"])
                    sightings = int(existing["sightings"]) + 1
                    confirmed_at = existing["confirmed_at"]
                    connection.execute(
                        """UPDATE devices SET
                           hostname=COALESCE(?, hostname),
                           vendor=COALESCE(?, vendor),
                           last_seen_at=?,
                           sightings=?
                           WHERE mac=?""",
                        (item.hostname, item.vendor, when, sightings, item.mac),
                    )
                required_age = (
                    self.private_confirmation_seconds
                    if private
                    else self.confirmation_seconds
                )
                age = (completed_at - first_seen).total_seconds()
                required_sightings = 3 if private else 2
                if (
                    known is None
                    and confirmed_at is None
                    and sightings >= required_sightings
                    and age >= required_age
                ):
                    connection.execute(
                        "UPDATE devices SET confirmed_at=? WHERE mac=?",
                        (when, item.mac),
                    )
                    newly_confirmed += 1
                connection.execute(
                    """INSERT INTO addresses
                       (mac, address, first_seen_at, last_seen_at)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(mac, address) DO UPDATE SET
                         last_seen_at=excluded.last_seen_at""",
                    (item.mac, item.address, when, when),
                )
        return {
            "observations": len(normalized),
            "newly_confirmed": newly_confirmed,
        }

    def record_scan_failure(self, *, completed_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO scan_runs
                   (completed_at, network, state, observation_count)
                   VALUES (?, ?, 'failed', 0)""",
                (utc_text(completed_at), self.network),
            )

    def pending_notifications(self) -> list[dict[str, str | bool | None]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT mac, node_id, hostname, vendor, private_address,
                          first_seen_at, last_seen_at
                   FROM devices
                   WHERE confirmed_at IS NOT NULL
                     AND notification_sent_at IS NULL
                   ORDER BY confirmed_at, node_id"""
            ).fetchall()
        return [
            {
                "mac": row["mac"],
                "node_id": row["node_id"],
                "hostname": row["hostname"],
                "vendor": row["vendor"],
                "private_address": bool(row["private_address"]),
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
            }
            for row in rows
        ]

    def mark_notification_sent(self, mac: str, *, sent_at: datetime) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE devices SET notification_sent_at=?
                   WHERE mac=? AND confirmed_at IS NOT NULL""",
                (utc_text(sent_at), normalize_mac(mac)),
            )
            if cursor.rowcount != 1:
                raise ValueError("confirmed device was not found")

    def health(self, now: datetime) -> dict[str, object]:
        with self._connect() as connection:
            latest = connection.execute(
                "SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if latest is None:
            return {
                "status": "initializing",
                "last_completed_at": None,
                "age_seconds": None,
                "network": self.network,
            }
        age = max(0, int((now - parse_utc(latest["completed_at"])).total_seconds()))
        return {
            "status": (
                "failed"
                if latest["state"] == "failed"
                else ("stale" if age > self.stale_seconds else "healthy")
            ),
            "last_completed_at": latest["completed_at"],
            "age_seconds": age,
            "network": latest["network"],
        }

    def topology(self, now: datetime) -> dict[str, object]:
        health = self.health(now)
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM devices ORDER BY node_id").fetchall()
            addresses = connection.execute(
                "SELECT * FROM addresses ORDER BY mac, last_seen_at DESC"
            ).fetchall()
        by_mac: dict[str, list[str]] = {}
        for row in addresses:
            by_mac.setdefault(row["mac"], []).append(row["address"])

        nodes: list[dict[str, object]] = [
            {
                "id": "segment-trusted-lan",
                "name": "Trusted LAN",
                "kind": "network",
                "status": health["status"],
                "known": True,
                "addresses": [self.network],
                "mac": None,
                "vendor": None,
                "first_seen_at": None,
                "last_seen_at": health["last_completed_at"],
                "source": "declared",
                "private_address": False,
                "confirmed": True,
            }
        ]
        observed_ids = {row["node_id"] for row in rows}
        for device in self.known.devices:
            if device.id not in observed_ids:
                nodes.append(
                    {
                        "id": device.id,
                        "name": device.name,
                        "kind": device.kind,
                        "status": "unknown",
                        "known": True,
                        "addresses": [device.address] if device.address else [],
                        "mac": device.mac,
                        "vendor": None,
                        "first_seen_at": None,
                        "last_seen_at": None,
                        "source": "declared",
                        "private_address": bool(
                            device.mac and is_private_mac(device.mac)
                        ),
                        "confirmed": True,
                    }
                )
        for row in rows:
            known = self.known.by_mac.get(row["mac"])
            if known is None:
                known = next(
                    (
                        self.known.by_address[address]
                        for address in by_mac.get(row["mac"], [])
                        if address in self.known.by_address
                    ),
                    None,
                )
            age = (now - parse_utc(row["last_seen_at"])).total_seconds()
            nodes.append(
                {
                    "id": row["node_id"],
                    "name": known.name if known else (row["hostname"] or "Unknown device"),
                    "kind": known.kind if known else "unknown",
                    "status": "online" if age <= self.offline_seconds else "offline",
                    "known": known is not None,
                    "addresses": by_mac.get(row["mac"], []),
                    "mac": row["mac"],
                    "vendor": row["vendor"],
                    "first_seen_at": row["first_seen_at"],
                    "last_seen_at": row["last_seen_at"],
                    "source": "observed",
                    "private_address": bool(row["private_address"]),
                    "confirmed": known is not None or row["confirmed_at"] is not None,
                }
            )
        edges = [
            {
                "id": f"lan-{node['id']}",
                "source_id": "segment-trusted-lan",
                "target_id": node["id"],
                "kind": "membership",
                "evidence": "observed" if node["source"] == "observed" else "declared",
            }
            for node in nodes
            if node["id"] != "segment-trusted-lan"
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_text(now),
            "discovery": {
                "state": health["status"],
                "last_completed_at": health["last_completed_at"],
                "network": self.network,
            },
            "nodes": nodes,
            "edges": edges,
        }
