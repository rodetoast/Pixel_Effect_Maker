"""Pure, allocation-free particle lifetime scalar evaluation."""

from __future__ import annotations

from app.models.particle_emitter import LifetimeScalarModulation
from app.services.emitter_service import ease


def normalized_lifetime_age(age: float, lifetime: float) -> float:
    """Map the visible birth-to-last-alive span to 0..1 safely.

    A one-frame or corrupt non-positive lifetime has no interval, so it uses
    the end state, matching the existing particle alpha convention.
    """
    if lifetime <= 1:
        return 1.0
    return max(0.0, min(1.0, float(age) / (float(lifetime) - 1.0)))


def evaluate_lifetime_scalar(
    modulation: LifetimeScalarModulation,
    normalized_age: float,
    disabled_value: float = 1.0,
) -> float:
    """Evaluate one scalar channel without mutation or per-frame allocation."""
    if not modulation.enabled:
        return disabled_value
    amount = ease(max(0.0, min(1.0, float(normalized_age))), modulation.easing)
    return modulation.start + (modulation.end - modulation.start) * amount
