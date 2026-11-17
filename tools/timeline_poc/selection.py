"""Runtime selection only. Never stores or mutates a Project/Resource."""

from dataclasses import dataclass, field
from collections.abc import Set


class FrameIntervals(Set):
    """Value-style disjoint half-open intervals, not one object per frame."""

    def __init__(self, intervals=()):
        merged = []
        for start, stop in sorted(intervals):
            if stop <= start:
                continue
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(stop, merged[-1][1]))
            else:
                merged.append((start, stop))
        self.intervals = tuple(merged)

    @classmethod
    def from_values(cls, values):
        if isinstance(values, cls):
            return values
        if isinstance(values, range) and values.step == 1:
            return cls(((values.start, values.stop),))
        return cls((n, n + 1) for n in values)

    def __contains__(self, value):
        return any(a <= value < b for a, b in self.intervals)

    def __len__(self):
        return sum(b - a for a, b in self.intervals)

    def __iter__(self):
        for a, b in self.intervals:
            yield from range(a, b)

    def __eq__(self, other):
        if isinstance(other, FrameIntervals):
            return self.intervals == other.intervals
        return super().__eq__(other)

    def __or__(self, other):
        return FrameIntervals(self.intervals + self.from_values(other).intervals)

    __ror__ = __or__

    def toggle(self, frame):
        if frame not in self:
            return self | {frame}
        return FrameIntervals(part for a, b in self.intervals
                              for part in ((a, min(b, frame)), (max(a, frame + 1), b)))


@dataclass(frozen=True)
class CellRange:
    anchor_frame: int
    anchor_row: int
    active_frame: int
    active_row: int

    @property
    def bounds(self):
        return (min(self.anchor_frame, self.active_frame), max(self.anchor_frame, self.active_frame) + 1,
                min(self.anchor_row, self.active_row), max(self.anchor_row, self.active_row) + 1)

    @property
    def size(self):
        a, b, c, d = self.bounds
        return (b - a) * (d - c)


@dataclass
class TimelineSelection:
    frames: FrameIntervals = field(default_factory=FrameIntervals)
    keys: set[tuple[int, int]] = field(default_factory=set)
    layers: set[int] = field(default_factory=set)
    playhead: int = 0
    anchor: int | None = None
    primary: int | None = None
    active_domain: str = "frames"
    cells: CellRange | None = None

    def __post_init__(self):
        self.frames = FrameIntervals.from_values(self.frames)

    def select_frame(self, frame, *, shift=False, ctrl=False):
        if shift and self.anchor is not None:
            values = FrameIntervals(((min(self.anchor, frame), max(self.anchor, frame) + 1),))
            self.frames = self.frames | values if ctrl else values
        elif ctrl:
            self.frames = self.frames.toggle(frame)
            self.anchor = frame
        else:
            self.frames = FrameIntervals(((frame, frame + 1),))
            self.anchor = frame
        self.primary = frame if frame in self.frames else (self.frames.intervals[0][0] if self.frames else None)
        self.active_domain = "frames"

    def select_key(self, row, frame, *, ctrl=False):
        key = (row, frame)
        if ctrl:
            self.keys.symmetric_difference_update({key})
        else:
            self.keys = {key}
        self.active_domain = "keys"

    def select_layer(self, row, *, ctrl=False):
        if ctrl:
            self.layers.symmetric_difference_update({row})
        else:
            self.layers = {row}
        self.active_domain = "layers"

    def seek(self, frame, frame_count):
        self.playhead = max(0, min(frame_count - 1, frame))
