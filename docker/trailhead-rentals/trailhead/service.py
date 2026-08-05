from __future__ import annotations

import sqlite3

from .data import PRODUCTS, RENTALS, USERS, Product, Rental
from .features import FeatureVariants


def search_products(query: str, variants: FeatureVariants) -> list[Product]:
    if variants.search not in {"parameterized", "concatenated-sql"}:
        raise ValueError("unreviewed search variant")

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE products (product_id TEXT, name TEXT, category TEXT, rate INTEGER, summary TEXT, accent TEXT, glyph TEXT)"
        )
        connection.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    item.product_id,
                    item.name,
                    item.category,
                    item.rate,
                    item.summary,
                    item.accent,
                    item.glyph,
                )
                for item in PRODUCTS
            ],
        )
        needle = query.strip()
        if not needle:
            rows = connection.execute("SELECT * FROM products ORDER BY rowid").fetchall()
        elif variants.search == "parameterized":
            pattern = f"%{needle}%"
            rows = connection.execute(
                "SELECT * FROM products WHERE name LIKE ? OR category LIKE ? OR summary LIKE ? ORDER BY rowid",
                (pattern, pattern, pattern),
            ).fetchall()
        else:
            # Reviewed lesson variant: the query is intentionally concatenated.
            statement = (
                "SELECT * FROM products WHERE name LIKE '%"
                + needle
                + "%' OR category LIKE '%"
                + needle
                + "%' OR summary LIKE '%"
                + needle
                + "%' ORDER BY rowid"
            )
            try:
                rows = connection.execute(statement).fetchall()
            except sqlite3.Error:
                return []
        return [Product(*row) for row in rows]
    finally:
        connection.close()


def rental_for_user(
    username: str,
    rental_id: int,
    variants: FeatureVariants,
) -> Rental | None:
    if variants.rental_authorization not in {"owner-required", "authentication-only"}:
        raise ValueError("unreviewed rental authorization variant")
    rental = RENTALS.get(rental_id)
    if rental is None:
        return None
    if variants.rental_authorization == "owner-required" and rental.owner != username:
        return None
    return rental


def profile_for_user(username: str, variants: FeatureVariants) -> dict[str, str] | None:
    if variants.api_projection != "minimal":
        raise ValueError("unreviewed API projection variant")
    user = USERS.get(username)
    if not user:
        return None
    return {"username": username, "name": user["name"], "email": user["email"]}


def admin_summary(username: str, variants: FeatureVariants) -> dict[str, int] | None:
    if variants.admin_authorization != "role-required":
        raise ValueError("unreviewed admin authorization variant")
    user = USERS.get(username)
    if not user or user["role"] != "admin":
        return None
    return {
        "active_rentals": len(RENTALS),
        "catalog_items": len(PRODUCTS),
        "member_accounts": sum(1 for item in USERS.values() if item["role"] == "member"),
    }
