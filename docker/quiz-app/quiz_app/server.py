from __future__ import annotations

import html
import json
import os
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .authorization import EXPENSES, Expense, find_expense


USERS = {"alex": "training-only-41", "sam": "training-only-72"}
SESSIONS = {"session-alex": "alex", "session-sam": "sam"}


def current_user(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    morsel = cookie.get("expense_session")
    return SESSIONS.get(morsel.value) if morsel else None


def expense_payload(expense: Expense) -> dict[str, object]:
    return {
        "id": expense.expense_id,
        "merchant": expense.merchant,
        "amount": expense.amount,
        "description": expense.description,
    }


class QuizHandler(BaseHTTPRequestHandler):
    server_version = "ExpensePortal/1.0"

    @property
    def quiz_mode(self) -> str:
        return os.environ.get("QUIZ_MODE", "vulnerable")

    def log_message(self, format: str, *args: object) -> None:
        print(f"quiz-app {self.address_string()} {format % args}")

    def send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, status: HTTPStatus, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(HTTPStatus.OK, {"status": "healthy"})
            return
        if path == "/":
            self.handle_home()
            return
        if path.startswith("/api/expenses/"):
            self.handle_expense(path)
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/login":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        length = min(int(self.headers.get("Content-Length", "0")), 4096)
        form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        if USERS.get(username) != password:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "invalid_login"})
            return
        body = b"Signed in"
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/")
        self.send_header(
            "Set-Cookie",
            f"expense_session=session-{username}; HttpOnly; SameSite=Strict; Path=/",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_home(self) -> None:
        user = current_user(self.headers.get("Cookie"))
        if not user:
            self.send_html(
                HTTPStatus.OK,
                """<!doctype html><html><body><h1>Acme Expense Portal</h1>
                <p>Training account: alex / training-only-41</p>
                <form method='post' action='/login'>
                <input name='username' aria-label='Username'>
                <input name='password' type='password' aria-label='Password'>
                <button>Sign in</button></form></body></html>""",
            )
            return

        rows = "".join(
            f"<li><a href='/api/expenses/{item.expense_id}'>"
            f"Expense {item.expense_id}</a> — {html.escape(item.merchant)}</li>"
            for item in EXPENSES.values()
            if item.owner == user
        )
        self.send_html(
            HTTPStatus.OK,
            f"<!doctype html><html><body><h1>My expenses</h1><ul>{rows}</ul></body></html>",
        )

    def handle_expense(self, path: str) -> None:
        user = current_user(self.headers.get("Cookie"))
        if not user:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "authentication_required"})
            return
        try:
            expense_id = int(path.rsplit("/", 1)[1])
        except ValueError:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        expense = find_expense(user, expense_id, self.quiz_mode)
        if expense is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self.send_json(HTTPStatus.OK, expense_payload(expense))


def main() -> int:
    mode = os.environ.get("QUIZ_MODE", "vulnerable")
    if mode not in {"vulnerable", "fixed"}:
        raise SystemExit("QUIZ_MODE must be vulnerable or fixed")
    server = ThreadingHTTPServer(("0.0.0.0", 8080), QuizHandler)
    print(f"Synthetic expense portal listening on 8080 in {mode} mode")
    server.serve_forever()
    return 0
