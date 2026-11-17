"""Pure POC contracts; does not import Qt or any production app module."""

from dataclasses import FrozenInstanceError, asdict, replace
from math import ceil
import ast
from pathlib import Path

import pytest

from tools.timeline_poc.adapter import SyntheticTimelineAdapter
from tools.timeline_poc.geometry import HitTarget, TimelineGeometry
from tools.timeline_poc.interaction import TimelineInteraction
from tools.timeline_poc.selection import TimelineSelection


@pytest.mark.parametrize("count", [12, 120, 1000, 10000])
@pytest.mark.parametrize("frame_width", [8, 31.5, 160])
@pytest.mark.parametrize("offset", [0, 113.25, 1000])
def test_frame_row_roundtrip_and_visible_half_open_bounds(count, frame_width, offset):
    base = TimelineGeometry(count, 200, frame_width=frame_width)
    g = replace(base, scroll_x=min(offset, base.max_scroll_x), scroll_y=67.5)
    for frame in g.visible_frames():
        x = g.frame_x(frame)
        if g.header_width <= x < g.width:
            assert g.frame_at(x) == frame
            assert g.hit_test(x, 1) == HitTarget("ruler", frame)
    assert g.visible_frames().stop <= count
    assert len(g.visible_frames()) <= ceil(g.body_width / frame_width) + 1
    for row in g.visible_rows():
        if g.body_top <= g.row_y(row) < g.height:
            assert g.row_at(g.row_y(row)) == row
    assert g.hit_test(g.width, 1).kind == "outside"
    assert g.hit_test(-1, 1).kind == "outside"


@pytest.mark.parametrize("factor", [0.5, 1.15, 2])
def test_zoom_anchor_is_exact_before_native_scrollbar_integer_rounding(factor):
    g = TimelineGeometry(10000, 20, scroll_x=1000)
    x = 510
    next_g = g.zoom_at(x, factor)
    assert (x - g.header_width + g.scroll_x) / g.frame_width == pytest.approx(
        (x - next_g.header_width + next_g.scroll_x) / next_g.frame_width)
    assert next_g.frame_count == g.frame_count


@pytest.mark.parametrize("factor", [0, -1, float("nan"), float("inf")])
def test_invalid_zoom_rejected(factor):
    with pytest.raises(ValueError):
        TimelineGeometry(12, 3).zoom_at(300, factor)


def test_small_viewport_empty_visible_ranges_and_end_boundaries():
    g = TimelineGeometry(12, 4, width=40, height=20)
    assert not g.visible_frames() and not g.visible_rows()
    g = TimelineGeometry(12, 4)
    assert g.frame_at(g.header_width) == 0
    assert g.frame_at(g.header_width + 12 * g.frame_width) is None
    assert g.frame_at(-100, clamp=True) == 0
    assert g.frame_at(1000000, clamp=True) == 11
    assert g.hit_test(1, g.body_top).kind == "layer"


def test_shift_ctrl_anchor_and_all_domains_are_independent():
    s = TimelineSelection(playhead=11, keys={(0, 0)}, layers={2})
    s.select_frame(2)
    s.select_frame(5, shift=True)
    assert s.frames == {2, 3, 4, 5} and s.anchor == 2
    s.select_frame(3, ctrl=True)
    assert s.frames == {2, 4, 5} and s.anchor == 3
    s.select_frame(7, ctrl=True, shift=True)
    assert s.frames == {2, 3, 4, 5, 6, 7}
    assert s.playhead == 11 and s.keys == {(0, 0)} and s.layers == {2}
    s.seek(200, 120)
    assert s.playhead == 119 and s.frames == {2, 3, 4, 5, 6, 7}
    s.select_key(1, 8)
    s.select_layer(3)
    assert s.frames == {2, 3, 4, 5, 6, 7} and s.playhead == 119


def test_ctrl_can_remove_last_frame_without_moving_playhead():
    s = TimelineSelection(playhead=6)
    s.select_frame(3)
    s.select_frame(3, ctrl=True)
    assert s.frames == set() and s.primary is None and s.playhead == 6


def test_frame_drag_selects_only_after_threshold_escape_restores_snapshot():
    s = TimelineSelection(playhead=9, keys={(0, 0)}, layers={2})
    s.select_frame(1)
    before = asdict(s)
    controller = TimelineInteraction(s)
    g = TimelineGeometry(120, 24)
    controller.press(HitTarget("frame", 2), g.frame_x(2), 35)
    controller.move(g.frame_x(2) + 9, 35, g, 10)
    assert controller.mode == "pressed_frames" and s.frames == {2}
    controller.move(g.frame_x(6), 35, g, 10)
    assert s.frames == {2, 3, 4, 5, 6} and s.playhead == 9
    controller.key("escape", 120)
    assert asdict(s) == before and controller.mode == "idle"


def test_key_or_layer_drag_cannot_move_keys_or_document_frames():
    g = TimelineGeometry(120, 24)
    s = TimelineSelection(frames={4}, playhead=9)
    controller = TimelineInteraction(s)
    controller.press(HitTarget("key", 0, 0), g.frame_x(0), g.row_y(0))
    controller.move(g.frame_x(10), g.row_y(2), g, 10)
    controller.finish()
    assert s.keys == {(0, 0)} and s.frames == {4} and s.playhead == 9
    controller.press(HitTarget("layer", row=3), 20, g.row_y(3))
    controller.move(400, 300, g, 10)
    controller.finish()
    assert s.layers == {3} and s.keys == {(0, 0)}


def test_keyboard_plain_navigation_and_shift_selection_are_separate():
    s = TimelineSelection(playhead=6, frames={2}, primary=2, anchor=2)
    controller = TimelineInteraction(s)
    controller.key("right", 12)
    assert s.playhead == 7 and s.frames == {2}
    controller.key("right", 12, shift=True)
    assert s.frames == {2, 3} and s.playhead == 7
    controller.key("end", 12)
    assert s.playhead == 11 and s.frames == {2, 3}
    assert not controller.key("delete", 12)


@pytest.mark.parametrize("count,rows", [(12, 4), (120, 24), (1000, 200), (10000, 2000)])
def test_synthetic_adapter_enumerates_only_requested_sparse_span(count, rows):
    adapter = SyntheticTimelineAdapter(count, rows)
    for row in (0, rows - 1):
        start, stop = max(0, count - 20), count
        expected = [f for f in range(start, stop) if adapter.has_key(row, f)]
        assert list(adapter.keys_in(row, start, stop)) == expected
        assert len(adapter.__dict__) == 2
    with pytest.raises(FrozenInstanceError):
        adapter.frame_count = 1


def test_poc_source_has_no_production_import_or_document_loader():
    root = Path(__file__).resolve().parents[1] / "tools" / "timeline_poc"
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                assert all(not n.name.startswith("app") for n in node.names), path.name
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("app"), path.name
