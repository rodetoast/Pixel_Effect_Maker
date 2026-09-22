"""Small deterministic natural-motion contributions for particle paths."""

from __future__ import annotations

import math


def effective_motion_age(age_frames: float, enabled: bool, strength: float) -> float:
    """Analytic exponentially damped base-motion clock in frames (not lifetime)."""
    age = max(0.0, float(age_frames))
    if not enabled or strength == 0.0 or age == 0.0:
        return age
    # expm1 preserves useful precision even for a very small d * age.
    return -math.expm1(-float(strength) * age) / float(strength)


def gravity_displacement(age_frames: float, enabled: bool, strength: float) -> float:
    """Return signed Y displacement for constant acceleration in px/frame^2."""
    if not enabled or strength == 0.0:
        return 0.0
    age = max(0.0, float(age_frames))
    value = 0.5 * float(strength) * age * age
    return value if math.isfinite(value) else math.copysign(float("1.7976931348623157e308"), value)
