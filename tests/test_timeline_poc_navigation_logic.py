"""Phase1.5 navigation/edge math, no Qt/application imports."""

from dataclasses import asdict, replace
import sys

import pytest

from tools.timeline_poc.autoscroll import EdgePolicy
from tools.timeline_poc.geometry import HitTarget, TimelineGeometry, ruler_steps
from tools.timeline_poc.interaction import TimelineInteraction
from tools.timeline_poc.navigation import wheel_motion
from tools.timeline_poc.selection import CellRange, FrameIntervals, TimelineSelection


def test_phase1_small_horizontal_wheel_rounding_reproducer():
    # Exact former per-event expression: one angle unit at minimum zoom is
    # 8 * 3 / 120 = .2 DIP, rounded back into the same integer scrollbar.
    old = 1000
    for _ in range(10):
        old = round(old + 8 * 3 / 120)
    assert old == 1000
    g = TimelineGeometry(10000, 200, frame_width=8, scroll_x=1000)
    for _ in range(10):
        _, dx, _ = wheel_motion(g, (0, -1), (0, 0), shift=True)
        g = replace(g, scroll_x=g.scroll_x + dx)
    assert g.scroll_x == pytest.approx(1002)


@pytest.mark.parametrize("pixels,angle,shift,expected", [
    ((0, 0), (0, 120), False, (0, -84)),
    ((0, 0), (0, 120), True, (-96, 0)),
    ((0, 0), (120, 0), False, (-96, 0)),
    ((0, 2), (0, 120), False, (0, -2)),
    ((3, 2), (0, 0), False, (-3, -2)),
    ((0, 2), (0, 120), True, (-2, 0)),
    ((2, 0), (0, 120), True, (-2, 0)),
    ((0, 0), (0, 1), False, (0, -0.7)),
])
def test_wheel_axes_source_precedence_and_fractional_units(pixels, angle, shift, expected):
    kind, dx, dy = wheel_motion(TimelineGeometry(10000, 200), angle, pixels, shift=shift)
    assert kind == "scroll" and (dx, dy) == pytest.approx(expected)


@pytest.mark.parametrize("delta", [1, 15, 120, -120])
def test_zoom_roundtrip_no_integer_drift(delta):
    g = TimelineGeometry(10000, 200, scroll_x=1234.125)
    before = g
    for _ in range(100):
        _, factor, _ = wheel_motion(g, (0, delta), (0, 0), ctrl=True)
        g = g.zoom_at(530, factor).zoom_at(530, 1 / factor)
    assert g.frame_width == pytest.approx(before.frame_width)
    assert g.scroll_x == pytest.approx(before.scroll_x, abs=1e-7)


def test_zoom_limits_and_os_zero_scroll_lines():
    g = TimelineGeometry(10000, 200, frame_width=8, scroll_x=100.125)
    assert g.zoom_at(500, 0.5) == g
    g = replace(g, frame_width=160)
    assert g.zoom_at(500, 2) == g
    assert wheel_motion(g, (0, 120), (0, 0), lines=0)[1:] == (0, 0)


@pytest.mark.parametrize("pointer,sign", [(199, -1), (200, -1), (215, -1), (899, 1), (900, 1), (930, 1)])
def test_edge_velocity_sign_monotonic_and_cap(pointer, sign):
    p = EdgePolicy()
    v = p.velocity(pointer, 200, 900, 32)
    assert v * sign > 0
    assert abs(v) <= 32 * 24
    assert p.velocity(500, 200, 900, 32) == 0
    assert abs(p.velocity(950, 200, 900, 32)) > abs(p.velocity(900, 200, 900, 32))


@pytest.mark.parametrize("mode", ["idle", "pan", "scrub", "pressed_frames", "key_click_only"])
def test_nonselection_modes_never_autoscroll(mode):
    assert EdgePolicy().motion(TimelineGeometry(10000, 200), 1000, 500, mode, 0.016) == (0, 0)


def test_elapsed_time_direction_diagonal_frozen_headers_and_bounds():
    p = EdgePolicy()
    g = TimelineGeometry(10000, 200, scroll_x=300, scroll_y=200)
    dx, dy = p.motion(g, g.width + 50, g.height + 50, "drag_cells", 0.02)
    assert dx > 0 and dy > 0
    assert p.motion(g, g.width + 50, g.height + 50, "drag_frames", 0.02)[1] == 0
    dx2, dy2 = p.motion(g, g.header_width - 50, g.body_top - 50, "drag_cells", 0.02)
    assert dx2 < 0 and dy2 < 0
    # Elapsed-time equivalence away from bounds; no per-event speed dependency.
    half = p.motion(g, 1000, 500, "drag_cells", 0.01)
    full = p.motion(g, 1000, 500, "drag_cells", 0.02)
    assert full == pytest.approx(tuple(v * 2 for v in half))
    assert p.motion(g, 1000, 500, "drag_cells", 10) == p.motion(g, 1000, 500, "drag_cells", 0.05)
    top = replace(g, scroll_x=0, scroll_y=0)
    assert p.motion(top, -100, -100, "drag_cells", 0.02) == (0, 0)
    end = replace(g, scroll_x=g.max_scroll_x, scroll_y=g.max_scroll_y)
    assert p.motion(end, 1000, 500, "drag_cells", 0.02) == (0, 0)


def test_intervals_preserve_ctrl_shift_contract_without_materializing_frames():
    s = TimelineSelection()
    s.select_frame(0)
    s.select_frame(99999, shift=True)
    assert len(s.frames) == 100000 and s.frames.intervals == ((0, 100000),)
    assert sys.getsizeof(s.frames.intervals) < 200
    s.select_frame(5, ctrl=True)
    assert s.frames.intervals == ((0, 5), (6, 100000))
    s.select_frame(5, ctrl=True)
    assert s.frames.intervals == ((0, 100000),)


def test_cell_range_is_constant_size_and_independent_with_frozen_anchor():
    g = TimelineGeometry(10000, 200)
    s = TimelineSelection(frames={2, 3}, keys={(0, 0)}, layers={4}, playhead=7)
    before = asdict(s)
    interaction = TimelineInteraction(s)
    interaction.press(HitTarget("cell_range", 5, 3), g.frame_x(5), g.row_y(3))
    interaction.move(1000000, 1000000, g, 10)
    assert s.cells == CellRange(5, 3, 9999, 199)
    assert s.cells.size == 9995 * 197 and len(s.cells.__dict__) == 4
    assert s.frames == {2, 3} and s.keys == {(0, 0)} and s.layers == {4} and s.playhead == 7
    scrolled = replace(g, scroll_x=3000, scroll_y=1000)
    interaction.move(500, 300, scrolled, 10)
    assert (s.cells.anchor_frame, s.cells.anchor_row) == (5, 3)
    assert s.cells.active_frame == scrolled.frame_at(500, clamp=True)
    interaction.cancel()
    assert asdict(s) == before


@pytest.mark.parametrize("width", [8, 15.9, 32, 80, 160])
def test_shared_ruler_density_has_room_and_regular_major_minor_hierarchy(width):
    minor, major = ruler_steps(47, width)
    assert minor * width >= 47 and major == minor * 5
