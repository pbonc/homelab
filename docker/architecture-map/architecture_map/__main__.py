from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
MODEL = ROOT / "model" / "architecture.json"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'")
        super().end_headers()

    def send_json(self, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self.send_json({"status": "healthy", "version": __version__})
        elif self.path == "/api/model":
            self.send_json(json.loads(MODEL.read_text(encoding="utf-8")))
        else:
            super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        print(f"architecture-map: {format % args}")


def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", 8040), Handler).serve_forever()


if __name__ == "__main__":
    main()
