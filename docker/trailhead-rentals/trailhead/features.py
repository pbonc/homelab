from __future__ import annotations

from dataclasses import asdict, dataclass


SECURE_BASELINE = "secure-baseline"
REVIEWED_VARIANT_SETS = {
    SECURE_BASELINE: {},
    "lesson-idor": {"rental_authorization": "authentication-only"},
    "lesson-sqli": {"search": "concatenated-sql"},
    "lesson-stored-xss": {"review_rendering": "raw"},
    "lesson-idor-sqli": {
        "rental_authorization": "authentication-only",
        "search": "concatenated-sql",
    },
    "lesson-idor-stored-xss": {
        "rental_authorization": "authentication-only",
        "review_rendering": "raw",
    },
    "lesson-sqli-stored-xss": {
        "search": "concatenated-sql",
        "review_rendering": "raw",
    },
    "lesson-idor-sqli-stored-xss": {
        "rental_authorization": "authentication-only",
        "search": "concatenated-sql",
        "review_rendering": "raw",
    },
}


@dataclass(frozen=True)
class FeatureVariants:
    search: str = "parameterized"
    rental_authorization: str = "owner-required"
    review_rendering: str = "encoded"
    profile_updates: str = "allowlisted"
    api_projection: str = "minimal"
    admin_authorization: str = "role-required"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def load_variant_set(name: str) -> FeatureVariants:
    changes = REVIEWED_VARIANT_SETS.get(name)
    if changes is None:
        raise ValueError(f"unknown or unreviewed variant set: {name}")
    return FeatureVariants(**changes)
