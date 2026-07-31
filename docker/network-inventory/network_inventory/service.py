from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn

from .main import app, store
from .notifier import publish_unknown_device
from .scanner import scan


LOG = logging.getLogger("network-inventory")


def scan_forever(stop: threading.Event) -> None:
    interval = int(os.environ.get("NETWORK_INVENTORY_SCAN_INTERVAL_SECONDS", "60"))
    ntfy_url = os.environ.get("NETWORK_INVENTORY_NTFY_URL", "")
    ntfy_username = os.environ.get(
        "NETWORK_INVENTORY_NTFY_USERNAME", "homelab-publisher"
    )
    password_file = Path(
        os.environ.get(
            "NETWORK_INVENTORY_NTFY_PASSWORD_FILE",
            "/run/secrets/ntfy_publisher_password",
        )
    )
    while not stop.is_set():
        started = time.monotonic()
        try:
            observations = scan(store.network)
            result = store.record_scan(
                observations, completed_at=datetime.now(timezone.utc)
            )
            LOG.info(
                "scan completed: observations=%d newly_confirmed=%d",
                result["observations"],
                result["newly_confirmed"],
            )
            if ntfy_url:
                for device in store.pending_notifications():
                    try:
                        sent_at = datetime.now(timezone.utc)
                        publish_unknown_device(
                            device,
                            url=ntfy_url,
                            username=ntfy_username,
                            password_file=password_file,
                        )
                        store.mark_notification_sent(
                            str(device["mac"]), sent_at=sent_at
                        )
                        LOG.info(
                            "published new-device notification: node_id=%s",
                            device["node_id"],
                        )
                    except Exception:
                        LOG.exception(
                            "new-device notification failed: node_id=%s",
                            device["node_id"],
                        )
        except Exception:
            LOG.exception("network scan failed")
        elapsed = time.monotonic() - started
        stop.wait(max(1, interval - elapsed))


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("NETWORK_INVENTORY_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    stop = threading.Event()
    worker = threading.Thread(
        target=scan_forever,
        args=(stop,),
        name="network-scanner",
        daemon=True,
    )
    worker.start()
    try:
        uvicorn.run(app, host="0.0.0.0", port=8030, log_level="info")
    finally:
        stop.set()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
