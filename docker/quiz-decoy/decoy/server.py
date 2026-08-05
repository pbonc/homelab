from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .profiles import PROFILES, Response


class DecoyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        profile_id = os.environ.get("DECOY_PROFILE", "documentation")
        profile = PROFILES.get(profile_id)
        if profile is None:
            self._send(500, Response("application/json", json.dumps({"error": "invalid_profile"})), "Decoy/closed")
            return
        path = urlsplit(self.path).path
        if path == "/health":
            response = Response("application/json", '{"status":"healthy"}')
            self._send(200, response, profile.server_header)
            return
        response = profile.routes.get(path)
        if response is None:
            self._send(404, Response("application/json", '{"error":"not_found"}'), profile.server_header)
            return
        status = 401 if path == "/work-orders" else 200
        self._send(status, response, profile.server_header)

    def _send(self, status: int, response: Response, server_header: str) -> None:
        payload = response.body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Decoy-Service", server_header)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve() -> None:
    profile_id = os.environ.get("DECOY_PROFILE", "documentation")
    if profile_id not in PROFILES:
        raise SystemExit(f"unknown decoy profile: {profile_id}")
    port = int(os.environ.get("DECOY_PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), DecoyHandler).serve_forever()
