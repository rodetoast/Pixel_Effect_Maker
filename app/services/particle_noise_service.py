"""Process-independent, stateless smooth XY value noise for particle motion."""

from __future__ import annotations

import math


MASK64 = (1 << 64) - 1
_PARTICLE_SALT = 0xD1B54A32D192ED03
_X_SALT = 0x9E3779B97F4A7C15
_Y_SALT = 0x94D049BB133111EB
_LATTICE_SALT = 0xBF58476D1CE4E5B9
_UNIT53 = (1 << 53) - 1


def mix64(value: int) -> int:
    """Fixed SplitMix64 finalizer; no Python hash or RNG state."""
    value = (int(value) + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def particle_noise_seeds(emitter_seed: int, particle_id: int) -> tuple[int, int]:
    particle = mix64(int(emitter_seed) ^ mix64(int(particle_id) ^ _PARTICLE_SALT))
    return mix64(particle ^ _X_SALT), mix64(particle ^ _Y_SALT)


def lattice_value(channel_seed: int, index: int) -> float:
    """Return one stable lattice value in [-1,+1], with an exact zero birth anchor."""
    if index == 0:
        return 0.0
    bits = mix64(int(channel_seed) ^ mix64(int(index) ^ _LATTICE_SALT))
    return 2.0 * ((bits >> 11) / _UNIT53) - 1.0


def quintic_fade(fraction: float) -> float:
    return fraction * fraction * fraction * (fraction * (fraction * 6.0 - 15.0) + 10.0)


def smooth_value_noise(channel_seed: int, coordinate: float) -> float:
    left = math.floor(coordinate)
    fraction = coordinate - left
    a = lattice_value(channel_seed, left)
    b = lattice_value(channel_seed, left + 1)
    return a + (b - a) * quintic_fade(fraction)


def particle_noise_offset(
    emitter_seed: int, particle_id: int, age_frames: float,
    enabled: bool, strength: float, frequency: float,
) -> tuple[float, float]:
    """Return local-pixel XY offset using actual age, independent of Drag time."""
    if not enabled or strength == 0.0 or frequency == 0.0 or age_frames <= 0.0:
        return 0.0, 0.0
    coordinate = float(age_frames) * float(frequency)
    seed_x, seed_y = particle_noise_seeds(emitter_seed, particle_id)
    amplitude = float(strength)
    return (
        amplitude * smooth_value_noise(seed_x, coordinate),
        amplitude * smooth_value_noise(seed_y, coordinate),
    )
