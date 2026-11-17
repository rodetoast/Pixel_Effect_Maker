"""Pure logical-pixel geometry; Qt already converts event coordinates from DPR."""

from dataclasses import dataclass, replace
from math import ceil, floor, isfinite


@dataclass(frozen=True)
class HitTarget:
    kind: str
    frame: int | None = None
    row: int | None = None


@dataclass(frozen=True)
class TimelineGeometry:
    frame_count: int
    row_count: int
    width: float = 900
    height: float = 440
    frame_width: float = 32
    row_height: float = 28
    header_width: float = 184
    ruler_height: float = 28
    frame_header_height: float = 26
    scroll_x: float = 0
    scroll_y: float = 0

    def __post_init__(self):
        if self.frame_count < 1 or self.row_count < 1:
            raise ValueError("positive counts required")
        values = (self.width, self.height, self.frame_width, self.row_height,
                  self.header_width, self.ruler_height, self.frame_header_height,
                  self.scroll_x, self.scroll_y)
        if not all(isfinite(v) and v >= 0 for v in values):
            raise ValueError("finite nonnegative geometry required")
        if min(self.frame_width, self.row_height, self.ruler_height, self.frame_header_height) <= 0:
            raise ValueError("positive cell sizes required")

    @property
    def body_top(self):
        return self.ruler_height + self.frame_header_height

    @property
    def body_width(self):
        return max(0, self.width - self.header_width)

    @property
    def body_height(self):
        return max(0, self.height - self.body_top)

    @property
    def max_scroll_x(self):
        return max(0, ceil(self.frame_count * self.frame_width - self.body_width))

    @property
    def max_scroll_y(self):
        return max(0, ceil(self.row_count * self.row_height - self.body_height))

    def frame_x(self, index, center=True):
        return self.header_width + (index + (0.5 if center else 0)) * self.frame_width - self.scroll_x

    def row_y(self, row, center=True):
        return self.body_top + (row + (0.5 if center else 0)) * self.row_height - self.scroll_y

    def frame_at(self, x, clamp=False):
        value = floor((x - self.header_width + self.scroll_x) / self.frame_width)
        return max(0, min(self.frame_count - 1, value)) if clamp else (
            value if self.header_width <= x < self.width and 0 <= value < self.frame_count else None)

    def row_at(self, y, clamp=False):
        value = floor((y - self.body_top + self.scroll_y) / self.row_height)
        if clamp:
            return max(0, min(self.row_count - 1, value))
        return value if self.body_top <= y < self.height and 0 <= value < self.row_count else None

    def visible_frames(self):
        if not self.body_width:
            return range(0)
        return range(min(self.frame_count, floor(self.scroll_x / self.frame_width)),
                     min(self.frame_count, ceil((self.scroll_x + self.body_width) / self.frame_width)))

    def visible_rows(self):
        if not self.body_height:
            return range(0)
        return range(min(self.row_count, floor(self.scroll_y / self.row_height)),
                     min(self.row_count, ceil((self.scroll_y + self.body_height) / self.row_height)))

    def hit_test(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return HitTarget("outside")
        frame, row = self.frame_at(x), self.row_at(y)
        if x < self.header_width:
            return HitTarget("layer", row=row) if row is not None else HitTarget("corner")
        if frame is None:
            return HitTarget("empty")
        if y < self.ruler_height:
            return HitTarget("ruler", frame=frame)
        if y < self.body_top:
            return HitTarget("frame", frame=frame)
        return HitTarget("cell", frame, row) if row is not None else HitTarget("empty")

    def zoom_at(self, x, factor):
        if not isfinite(factor) or factor <= 0:
            raise ValueError("positive zoom required")
        x = max(self.header_width, min(x, self.width))
        coordinate = (x - self.header_width + self.scroll_x) / self.frame_width
        width = min(160.0, max(8.0, self.frame_width * factor))
        result = replace(self, frame_width=width)
        offset = coordinate * width - (x - self.header_width)
        return replace(result, scroll_x=max(0, min(result.max_scroll_x, offset)))


def ruler_steps(label_width, frame_width):
    """Shared 1/2/5 hierarchy, frame numbers anchored to index zero."""
    required = max(1, ceil(label_width / frame_width))
    power = 1
    while power * 5 < required:
        power *= 10
    minor = next(n * power for n in (1, 2, 5, 10) if n * power >= required)
    return minor, minor * 5
