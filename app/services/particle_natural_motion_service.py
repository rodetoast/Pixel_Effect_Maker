"""Small deterministic natural-motion contributions for particle paths."""

from __future__ import annotations

import math


def gravity_displacement(age_frames: float, enabled: bool, strength: float) -> float:
    """Return signed Y displacement for constant acceleration in px/frame^2."""
    if not enabled or strength == 0.0:
        return 0.0
    age = max(0.0, float(age_frames))
    value = 0.5 * float(strength) * age * age
    return value if math.isfinite(value) else math.copysign(float("1.7976931348623157e308"), value)
