from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    category: str
    rate: int
    summary: str
    accent: str
    glyph: str


@dataclass(frozen=True)
class Rental:
    rental_id: int
    owner: str
    product_id: str
    start_date: str
    return_date: str
    status: str


@dataclass(frozen=True)
class Review:
    author: str
    product_id: str
    rating: int
    comment: str


PRODUCTS = (
    Product("tent-alpine-2", "Alpine Two Tent", "Shelter", 38, "Storm-ready shelter for two with a compact trail footprint.", "pine", "△"),
    Product("pack-ridge-48", "Ridge 48 Pack", "Packs", 24, "Balanced multi-day pack with an adjustable ventilated frame.", "clay", "▱"),
    Product("kayak-current", "Current Solo Kayak", "Water", 52, "Stable touring hull supplied with paddle, PFD, and dry bag.", "lake", "≈"),
    Product("stove-ember", "Ember Camp Stove", "Camp kitchen", 12, "Compact two-burner stove for a reliable meal after a long day.", "ember", "✦"),
    Product("sleep-cloud-20", "Cloud 20 Sleep Kit", "Sleep", 19, "Warm synthetic bag and insulated pad packed as one trail kit.", "dusk", "☾"),
    Product("bike-switchback", "Switchback Trail Bike", "Bikes", 64, "Hardtail mountain bike tuned for forest roads and flowing singletrack.", "moss", "◇"),
)

RENTALS = {
    72041: Rental(72041, "alex", "tent-alpine-2", "2026-08-14", "2026-08-17", "Confirmed"),
    72042: Rental(72042, "sam", "kayak-current", "2026-08-09", "2026-08-10", "Ready for pickup"),
    72043: Rental(72043, "alex", "stove-ember", "2026-09-02", "2026-09-04", "Reserved"),
}

REVIEWS = (
    Review("Mira", "tent-alpine-2", 5, "Quiet in the wind and genuinely simple to pitch."),
    Review("Jon", "pack-ridge-48", 4, "Comfortable through a full weekend. Hip pockets are excellent."),
    Review("Tess", "kayak-current", 5, "Predictable handling and the included dry bag was a nice touch."),
)

USERS = {
    "alex": {"password": "trail-only-41", "name": "Alex Morgan", "role": "member", "email": "alex@example.test"},
    "sam": {"password": "trail-only-72", "name": "Sam Rivera", "role": "member", "email": "sam@example.test"},
    "ranger": {"password": "trail-admin-19", "name": "Riley Park", "role": "admin", "email": "ranger@example.test"},
}
