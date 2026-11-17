"""Immutable, arithmetic synthetic tracks: no frame/cell array or image cache."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticTimelineAdapter:
    frame_count: int = 120
    row_count: int = 24

    def __post_init__(self):
        if not 1 <= self.frame_count <= 1_000_000 or not 1 <= self.row_count <= 10_000:
            raise ValueError("synthetic limits: 1..1000000 frames / 1..10000 tracks")

    def row_label(self, row, language="en"):
        name = "레이어" if language == "ko" else "Layer"
        prop = "회전 / 불투명도 — 합성 트랙" if language == "ko" else "Rotation / Opacity — Synthetic track"
        return f"{name} {row + 1:03d} · {prop}"

    def keys_in(self, row, start, stop):
        """Only enumerate visible sparse key positions, with no all-frame scan."""
        period = 12 + row % 5
        phase = row % period
        first = max(phase, phase + ((start - phase + period - 1) // period) * period)
        return range(first, min(stop, self.frame_count), period)

    def has_key(self, row, frame):
        return 0 <= row < self.row_count and 0 <= frame < self.frame_count and (
            frame - row % (12 + row % 5)) % (12 + row % 5) == 0
