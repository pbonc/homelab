from __future__ import annotations

from .data import PRODUCTS, RENTALS, USERS, Product, Rental
from .features import FeatureVariants


def search_products(query: str, variants: FeatureVariants) -> list[Product]:
    if variants.search != "parameterized":
        raise ValueError("unreviewed search variant")
    needle = query.casefold().strip()
    if not needle:
        return list(PRODUCTS)
    return [
        product
        for product in PRODUCTS
        if needle in product.name.casefold()
        or needle in product.category.casefold()
        or needle in product.summary.casefold()
    ]


def rental_for_user(
    username: str,
    rental_id: int,
    variants: FeatureVariants,
) -> Rental | None:
    if variants.rental_authorization != "owner-required":
        raise ValueError("unreviewed rental authorization variant")
    rental = RENTALS.get(rental_id)
    if rental is None or rental.owner != username:
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
