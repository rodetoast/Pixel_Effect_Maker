"""Stateless bounded alive-copy enumeration; never samples random properties."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterator, Sequence
from app.models.particle_emitter import ParticleEmitterSettings, ParticleInstance


@dataclass(frozen=True)
class ParticleCycleCopy:
    canonical: ParticleInstance
    birth_frame: int
    cycle_index: int

    @property
    def copy_key(self) -> tuple[int, int]:
        return self.cycle_index, self.canonical.particle_id

    def __getattr__(self, name):
        # Noise and every sampled property retain the canonical slot identity.
        return getattr(self.canonical, name)


def iter_particle_cycle_copies(settings: ParticleEmitterSettings,
                              slots: Sequence[ParticleInstance], frame: int, *, visibility_extension_frames: int = 0) -> Iterator[ParticleCycleCopy]:
    """Caller validates settings. Work is O(slots + alive copies), not history.

    Existing births are composition-absolute. Subtract the emitter gate ONCE
    for integer bounds, then return absolute copy births to the existing renderer.
    """
    q = frame - settings.start_frame
    if q < 0:
        return
    period = settings.emission_period_frames
    for slot in slots:
        b = slot.birth_frame - settings.start_frame
        minimum = -(-(q - b - (slot.lifetime + visibility_extension_frames - 1)) // period)
        maximum = (q - b) // period
        for cycle in range(minimum, maximum + 1):
            yield ParticleCycleCopy(slot, slot.birth_frame + cycle * period, cycle)
