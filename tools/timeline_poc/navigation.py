"""Pure wheel normalization. Fractional offsets are kept by the View geometry."""

from math import copysign


def wheel_motion(g, angle, pixels, *, shift=False, ctrl=False, lines=3):
    """Return (kind, dx, dy) or (zoom, factor, 0). Qt deltas already carry OS sign.

    Prefer pixelDelta when supplied; never add angleDelta a second time.
    Horizontal trackpad/native-wheel axes work without Shift too.
    """
    ax, ay = angle
    px, py = pixels
    has_pixels = bool(px or py)
    if ctrl:
        steps = (py or px) / 120 if has_pixels else (ay or ax) / 120
        return "zoom", 1.15 ** max(-10, min(10, steps)), 0
    if has_pixels:
        dx, dy = (-py if py else -px, 0) if shift else (-px, -py)
    elif shift:
        dx, dy = -(ay or ax) / 120 * min(48, g.frame_width) * lines, 0
    else:
        dx, dy = -ax / 120 * min(48, g.frame_width) * lines, -ay / 120 * g.row_height * lines
    def bounded(value, span):
        return copysign(min(abs(value), max(1, span)), value)
    return "scroll", bounded(dx, g.body_width), bounded(dy, g.body_height)
