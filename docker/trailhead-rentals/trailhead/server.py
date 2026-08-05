from __future__ import annotations

import html
import json
import mimetypes
import os
import secrets
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from .data import PRODUCTS, RENTALS, REVIEWS, USERS, Product, Review
from .features import SECURE_BASELINE, FeatureVariants, load_variant_set
from .service import admin_summary, profile_for_user, rental_for_user, search_products


STATIC_ROOT = Path(__file__).resolve().parents[1] / "static"
SESSIONS: dict[str, str] = {}
SESSION_LOCK = threading.Lock()
SUBMITTED_REVIEWS: list[Review] = []
SUPPORT_TICKETS: list[dict[str, str]] = []


def variants() -> FeatureVariants:
    return load_variant_set(os.environ.get("TRAILHEAD_VARIANT_SET", SECURE_BASELINE))


def session_user(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    morsel = cookie.get("trailhead_session")
    if not morsel:
        return None
    with SESSION_LOCK:
        return SESSIONS.get(morsel.value)


def product_by_id(product_id: str) -> Product | None:
    return next((product for product in PRODUCTS if product.product_id == product_id), None)


def layout(title: str, content: str, username: str | None = None) -> str:
    account = (
        f"<a href='/account'>{html.escape(USERS[username]['name'])}</a>"
        if username
        else "<a href='/login'>Sign in</a>"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · Trailhead Rentals</title><link rel="stylesheet" href="/static/app.css"></head>
<body><header class="topbar"><a class="brand" href="/"><span>▲</span> Trailhead Rentals</a>
<nav class="nav" aria-label="Primary"><a href="/">Gear</a><a href="/reviews">Field notes</a><a href="/support">Support</a>{account}</nav></header>
<main class="shell">{content}</main><footer class="shell">Synthetic assessment application · No real customers, payments, or inventory</footer></body></html>"""


def product_cards(products: list[Product]) -> str:
    if not products:
        return "<div class='panel'><p>No gear matched that search.</p></div>"
    cards = []
    for product in products:
        cards.append(
            f"""<article class="product"><div class="product-art {html.escape(product.accent)}" aria-hidden="true">{html.escape(product.glyph)}</div>
<div class="product-body"><span class="eyebrow">{html.escape(product.category)}</span><h3>{html.escape(product.name)}</h3>
<p>{html.escape(product.summary)}</p><div class="meta"><span class="rate">${product.rate}/day</span>
<a class="button secondary" href="/gear/{quote(product.product_id)}">View gear</a></div></div></article>"""
        )
    return f"<div class='grid'>{''.join(cards)}</div>"


class TrailheadHandler(BaseHTTPRequestHandler):
    server_version = "TrailheadRentals/0.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"trailhead {self.address_string()} {format % args}")

    def security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        script_policy = (
            "script-src 'self' 'unsafe-inline'; "
            if variants().review_rendering == "raw"
            else "script-src 'self'; "
        )
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            + script_policy
            + "style-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        )
        self.send_header("Cache-Control", "no-store")

    def send_body(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.security_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, status: HTTPStatus, body: str) -> None:
        self.send_body(status, body.encode("utf-8"), "text/html; charset=utf-8")

    def send_json(self, status: HTTPStatus, payload: object) -> None:
        self.send_body(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def redirect(self, location: str, cookie: str | None = None) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", "0")
        self.security_headers()
        self.end_headers()

    def read_form(self) -> dict[str, str]:
        length = min(int(self.headers.get("Content-Length", "0")), 8192)
        parsed = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
        return {key: values[0] for key, values in parsed.items() if values}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/static/"):
            self.handle_static(path)
        elif path == "/api/health":
            self.send_json(HTTPStatus.OK, {"status": "healthy"})
        elif path == "/api/catalog":
            self.handle_catalog_api(parse_qs(parsed.query).get("q", [""])[0])
        elif path.startswith("/api/rentals/"):
            self.handle_rental_api(path)
        elif path == "/api/profile":
            self.handle_profile_api()
        elif path == "/api/admin/summary":
            self.handle_admin_api()
        elif path == "/":
            self.handle_home(parse_qs(parsed.query).get("q", [""])[0])
        elif path.startswith("/gear/"):
            self.handle_product(path)
        elif path == "/login":
            self.handle_login_page()
        elif path == "/account":
            self.handle_account()
        elif path == "/rentals":
            self.handle_rentals()
        elif path == "/reviews":
            self.handle_reviews()
        elif path == "/support":
            self.handle_support()
        elif path == "/admin":
            self.handle_admin()
        else:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/login":
            self.handle_login()
        elif path == "/logout":
            self.handle_logout()
        elif path == "/reviews":
            self.handle_review_submission()
        elif path == "/support":
            self.handle_support_submission()
        else:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def handle_static(self, path: str) -> None:
        relative = path.removeprefix("/static/")
        candidate = (STATIC_ROOT / relative).resolve()
        if not candidate.is_relative_to(STATIC_ROOT.resolve()) or not candidate.is_file():
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self.send_body(HTTPStatus.OK, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")

    def handle_home(self, query: str) -> None:
        user = session_user(self.headers.get("Cookie"))
        results = search_products(query, variants())
        content = f"""<section class="hero"><div><span class="eyebrow">Borrow better · roam farther</span>
<h1>Good gear. No garage required.</h1><p>Reserve trail-tested equipment for a weekend outside. Every item is inspected, fitted, and ready for pickup from our Cedar Junction workshop.</p>
<a class="button" href="#catalog">Explore the gear</a></div><div class="trail-card"><strong>Make room for the trip, not the equipment.</strong></div></section>
<section id="catalog"><div class="section-head"><div><span class="eyebrow">Cedar Junction collection</span><h2>Choose your trail kit</h2></div>
<form class="search" method="get" action="/"><label class="eyebrow" for="q">Search gear</label><input id="q" name="q" value="{html.escape(query)}" placeholder="Tent, water, bikes…"><button>Search</button></form></div>
{product_cards(results)}</section>"""
        self.send_html(HTTPStatus.OK, layout("Gear rental", content, user))

    def handle_product(self, path: str) -> None:
        user = session_user(self.headers.get("Cookie"))
        product = product_by_id(path.rsplit("/", 1)[1])
        if not product:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        related = [review for review in (*REVIEWS, *SUBMITTED_REVIEWS) if review.product_id == product.product_id]
        notes = "".join(self.render_review(item) for item in related) or "<li>No field notes yet.</li>"
        content = f"""<section class="hero"><div><span class="eyebrow">{html.escape(product.category)}</span><h1>{html.escape(product.name)}</h1>
<p>{html.escape(product.summary)}</p><span class="rate">${product.rate} per day</span></div><div class="product-art {html.escape(product.accent)}" aria-hidden="true">{html.escape(product.glyph)}</div></section>
<section class="split"><div class="panel"><h2>Included with every rental</h2><p>Fit check, safety inspection, basic accessories, and a straightforward return window.</p></div>
<div class="panel"><h2>Recent field notes</h2><ul class="list">{notes}</ul></div></section>"""
        self.send_html(HTTPStatus.OK, layout(product.name, content, user))

    def handle_login_page(self, error: str = "") -> None:
        user = session_user(self.headers.get("Cookie"))
        if user:
            self.redirect("/account")
            return
        notice = f"<div class='notice error'>{html.escape(error)}</div>" if error else ""
        content = f"""<section class="hero"><div><span class="eyebrow">Member access</span><h1>Welcome back outside.</h1><p>Use the synthetic training account shown here. No real credentials belong in this application.</p></div>
<form class="panel stack" method="post" action="/login"><h2>Sign in</h2>{notice}<div class="notice">Training member: alex / trail-only-41</div>
<label>Username<input name="username" autocomplete="username" required></label><label>Password<input name="password" type="password" autocomplete="current-password" required></label><button>Sign in</button></form></section>"""
        self.send_html(HTTPStatus.OK, layout("Sign in", content))

    def handle_login(self) -> None:
        form = self.read_form()
        username = form.get("username", "")
        password = form.get("password", "")
        user = USERS.get(username)
        if not user or not secrets.compare_digest(user["password"], password):
            self.handle_login_page("That username or password was not recognized.")
            return
        token = secrets.token_urlsafe(32)
        with SESSION_LOCK:
            SESSIONS[token] = username
        self.redirect("/account", f"trailhead_session={token}; HttpOnly; SameSite=Strict; Path=/")

    def handle_logout(self) -> None:
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            cookie = SimpleCookie(); cookie.load(cookie_header)
            morsel = cookie.get("trailhead_session")
            if morsel:
                with SESSION_LOCK: SESSIONS.pop(morsel.value, None)
        self.redirect("/", "trailhead_session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/")

    def require_user(self) -> str | None:
        user = session_user(self.headers.get("Cookie"))
        if not user:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "authentication_required"})
        return user

    def handle_account(self) -> None:
        user = session_user(self.headers.get("Cookie"))
        if not user:
            self.redirect("/login")
            return
        profile = profile_for_user(user, variants())
        admin_link = "<a class='button secondary' href='/admin'>Operations</a>" if USERS[user]["role"] == "admin" else ""
        content = f"""<section class="hero"><div><span class="eyebrow">Member account</span><h1>Hi, {html.escape(profile['name'])}.</h1><p>{html.escape(profile['email'])}</p>
<a class="button" href="/rentals">View rentals</a> {admin_link}</div><form method="post" action="/logout"><button>Sign out</button></form></section>"""
        self.send_html(HTTPStatus.OK, layout("Account", content, user))

    def handle_rentals(self) -> None:
        user = session_user(self.headers.get("Cookie"))
        if not user:
            self.redirect("/login")
            return
        rows = []
        for rental in RENTALS.values():
            if rental.owner != user: continue
            product = product_by_id(rental.product_id)
            rows.append(f"<li><span class='pill'>{html.escape(rental.status)}</span> <strong>{html.escape(product.name)}</strong><br>{rental.start_date} to {rental.return_date} · <a href='/api/rentals/{rental.rental_id}'>receipt JSON</a></li>")
        content = f"<section class='hero'><div><span class='eyebrow'>Member history</span><h1>Your rentals.</h1></div></section><section class='panel'><ul class='list'>{''.join(rows)}</ul></section>"
        self.send_html(HTTPStatus.OK, layout("Rentals", content, user))

    def handle_reviews(self) -> None:
        user = session_user(self.headers.get("Cookie"))
        reviews = (*REVIEWS, *SUBMITTED_REVIEWS)
        items = "".join(self.render_review(item, include_product=True) for item in reviews)
        form = ""
        if user:
            options = "".join(f"<option value='{html.escape(item.product_id)}'>{html.escape(item.name)}</option>" for item in PRODUCTS)
            form = f"<form class='panel stack' method='post' action='/reviews'><h2>Add a field note</h2><select name='product_id'>{options}</select><select name='rating'><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select><textarea name='comment' maxlength='400' required></textarea><button>Publish note</button></form>"
        content = f"<section class='hero'><div><span class='eyebrow'>Community notes</span><h1>Reports from the trail.</h1></div></section><section class='split'><div class='panel'><ul class='list'>{items}</ul></div>{form}</section>"
        self.send_html(HTTPStatus.OK, layout("Field notes", content, user))

    def render_review(self, item: Review, include_product: bool = False) -> str:
        current = variants()
        if current.review_rendering not in {"encoded", "raw"}:
            raise ValueError("unreviewed review-rendering variant")
        author = html.escape(item.author)
        comment = (
            html.escape(item.comment)
            if current.review_rendering == "encoded"
            else item.comment
        )
        product = product_by_id(item.product_id)
        context = f" on {html.escape(product.name)}" if include_product and product else ""
        return f"<li><strong>{author}</strong>{context} · {item.rating}/5<br>{comment}</li>"

    def handle_review_submission(self) -> None:
        user = self.require_user()
        if not user: return
        form = self.read_form(); product = product_by_id(form.get("product_id", ""))
        try: rating = int(form.get("rating", "0"))
        except ValueError: rating = 0
        comment = form.get("comment", "").strip()[:400]
        if not product or rating not in range(1, 6) or not comment:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_review"}); return
        SUBMITTED_REVIEWS.append(Review(USERS[user]["name"], product.product_id, rating, comment))
        self.redirect("/reviews")

    def handle_support(self) -> None:
        user = session_user(self.headers.get("Cookie"))
        content = """<section class='hero'><div><span class='eyebrow'>Workshop support</span><h1>Questions before the trail?</h1><p>Send a synthetic support request. This demonstration does not deliver email or contact an external service.</p></div>
<form class='panel stack' method='post' action='/support'><label>Name<input name='name' maxlength='80' required></label><label>Reply address<input name='email' type='email' maxlength='120' required></label><label>Question<textarea name='message' maxlength='600' required></textarea></label><button>Send request</button></form></section>"""
        self.send_html(HTTPStatus.OK, layout("Support", content, user))

    def handle_support_submission(self) -> None:
        form = self.read_form(); name = form.get("name", "").strip()[:80]; email = form.get("email", "").strip()[:120]; message = form.get("message", "").strip()[:600]
        if not name or "@" not in email or not message:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_support_request"}); return
        SUPPORT_TICKETS.append({"name": name, "email": email, "message": message})
        self.send_html(HTTPStatus.ACCEPTED, layout("Request received", "<section class='hero'><div><span class='eyebrow'>Request received</span><h1>We packed your question.</h1><p>This synthetic request remains only in memory and disappears when the container stops.</p><a class='button' href='/'>Return to gear</a></div></section>"))

    def handle_catalog_api(self, query: str) -> None:
        items = search_products(query, variants())
        self.send_json(HTTPStatus.OK, [{"id": item.product_id, "name": item.name, "category": item.category, "daily_rate": item.rate} for item in items])

    def handle_rental_api(self, path: str) -> None:
        user = self.require_user()
        if not user: return
        try: rental_id = int(path.rsplit("/", 1)[1])
        except ValueError: self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"}); return
        rental = rental_for_user(user, rental_id, variants())
        if not rental: self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"}); return
        self.send_json(HTTPStatus.OK, {"id": rental.rental_id, "product_id": rental.product_id, "start_date": rental.start_date, "return_date": rental.return_date, "status": rental.status})

    def handle_profile_api(self) -> None:
        user = self.require_user()
        if user: self.send_json(HTTPStatus.OK, profile_for_user(user, variants()))

    def handle_admin_api(self) -> None:
        user = self.require_user()
        if not user: return
        summary = admin_summary(user, variants())
        if summary is None: self.send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"}); return
        self.send_json(HTTPStatus.OK, summary)

    def handle_admin(self) -> None:
        user = session_user(self.headers.get("Cookie"))
        if not user: self.redirect("/login"); return
        summary = admin_summary(user, variants())
        if summary is None: self.send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"}); return
        content = f"<section class='hero'><div><span class='eyebrow'>Workshop operations</span><h1>Morning readiness.</h1></div></section><section class='grid'><div class='panel'><h2>{summary['active_rentals']}</h2><p>Active rentals</p></div><div class='panel'><h2>{summary['catalog_items']}</h2><p>Catalog items</p></div><div class='panel'><h2>{summary['member_accounts']}</h2><p>Member accounts</p></div></section>"
        self.send_html(HTTPStatus.OK, layout("Operations", content, user))


def main() -> int:
    load_variant_set(os.environ.get("TRAILHEAD_VARIANT_SET", SECURE_BASELINE))
    server = ThreadingHTTPServer(("0.0.0.0", 8080), TrailheadHandler)
    print("Trailhead Rentals secure baseline listening on 8080")
    server.serve_forever()
    return 0
