from __future__ import annotations

from dataclasses import asdict, dataclass


SECURE_BASELINE = "secure-baseline"


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
    if name != SECURE_BASELINE:
        raise ValueError(f"unknown or unreviewed variant set: {name}")
    return FeatureVariants()
