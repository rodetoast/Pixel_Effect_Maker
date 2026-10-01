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
    return evaluate_scalar_points(modulation.points, normalized_age)


def evaluate_scalar_points(points, normalized_age: float) -> float:
    if normalized_age <= 0: return points[0].value
    if normalized_age >= 1: return points[-1].value
    left = points[0]
    for right in points[1:]:
        if normalized_age == right.time: return right.value
        if normalized_age < right.time:
            amount = ease((normalized_age-left.time)/(right.time-left.time), left.easing_to_next)
            return left.value + (right.value-left.value)*amount
        left = right
    return points[-1].value


def evaluate_lifetime_scalar_for_render(modulation, normalized_age):
    """Preserve legacy two-point endpoint rounding at the raster boundary.

    The public evaluator returns exact knots. Old alpha lerp at u=1 can differ
    by one floating ULP, affecting uint8 half-even rounding. Keep that arithmetic
    for two-point raster inputs only; multi-point curves use exact knot values.
    """
    if modulation.enabled and len(modulation.points) == 2:
        left, right = modulation.points
        amount = eased_lifetime_amount(normalized_age, left.easing_to_next)
        return left.value + (right.value-left.value)*amount
    return evaluate_lifetime_scalar(modulation, normalized_age)


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
    points = modulation.points
    if normalized_age <= 0: return points[0].rgb[channel] / 255.0
    if normalized_age >= 1: return points[-1].rgb[channel] / 255.0
    left = points[0]
    if len(points) == 2:
        right = points[1]
        amount = eased_lifetime_amount(normalized_age, left.easing_to_next) if eased_amount is None else eased_amount
        return (left.rgb[channel] + (right.rgb[channel]-left.rgb[channel])*amount) / 255.0
    for index in range(1, len(points)):
        right = points[index]
        if normalized_age == right.time: return right.rgb[channel] / 255.0
        if normalized_age < right.time:
            amount = ease((normalized_age-left.time)/(right.time-left.time), left.easing_to_next)
            return (left.rgb[channel] + (right.rgb[channel]-left.rgb[channel])*amount) / 255.0
        left = right
    return points[-1].rgb[channel] / 255.0
