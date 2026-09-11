"""Pure, allocation-free particle lifetime scalar evaluation."""

from __future__ import annotations

from app.models.particle_emitter import LifetimeColorModulation, LifetimeScalarModulation
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
    amount = eased_lifetime_amount(normalized_age, modulation.easing)
    return modulation.start + (modulation.end - modulation.start) * amount


def eased_lifetime_amount(normalized_age: float, easing: str) -> float:
    """Apply the shared lifetime clamp and easing contract."""
    return ease(max(0.0, min(1.0, float(normalized_age))), easing)


def evaluate_lifetime_color_component(
    modulation: LifetimeColorModulation,
    normalized_age: float,
    channel: int,
    *,
    eased_amount: float | None = None,
) -> float:
    """Return one RGB tint factor in 0..1 without creating a color object."""
    if not modulation.enabled:
        return 1.0
    amount = eased_lifetime_amount(normalized_age, modulation.easing) if eased_amount is None else eased_amount
    return (modulation.start_rgb[channel] + (modulation.end_rgb[channel] - modulation.start_rgb[channel]) * amount) / 255.0
