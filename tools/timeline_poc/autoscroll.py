"""Pure edge detection and elapsed-time integration; Qt timer lives in View."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgePolicy:
    threshold: float = 28
    max_units_per_second: float = 24

    def velocity(self, pointer, low, high, unit):
        if high <= low:
            return 0.0
        band = min(self.threshold, (high - low) / 3)
        if pointer < low + band:
            sign, distance = -1, low + band - pointer
        elif pointer > high - band:
            sign, distance = 1, pointer - (high - band)
        else:
            return 0.0
        # Slow entry, continuous growth outside, then a strict DIP/s cap.
        strength = min(1.0, distance / (band * 3))
        return sign * unit * self.max_units_per_second * strength

    def motion(self, g, x, y, mode, elapsed):
        if mode not in {"drag_frames", "drag_cells"}:
            return 0.0, 0.0
        dt = max(0.0, min(0.05, elapsed))  # discard long stalled backlog
        vx = self.velocity(x, g.header_width, g.width, g.frame_width) if g.body_width else 0
        vy = self.velocity(y, g.body_top, g.height, g.row_height) if mode == "drag_cells" and g.body_height else 0
        dx, dy = vx * dt, vy * dt
        return (max(0, min(g.max_scroll_x, g.scroll_x + dx)) - g.scroll_x,
                max(0, min(g.max_scroll_y, g.scroll_y + dy)) - g.scroll_y)
