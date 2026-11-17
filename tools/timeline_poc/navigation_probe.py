"""Phase1.5 real Qt-event probes; no direct calls to timer callbacks."""

from dataclasses import asdict
from statistics import median
from time import perf_counter
import tracemalloc

from PySide6.QtCore import QAbstractEventDispatcher, QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QFocusEvent, QHelpEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolTip, QWidget

from .adapter import SyntheticTimelineAdapter
from .diagnostics import close_widget, send_move, wait_until
from .selection import CellRange
from .view import TimelineViewport


def wheel(view, angle=(0, 0), pixels=(0, 0), mods=Qt.KeyboardModifier.NoModifier, inverted=False):
    g = view.geometry_state
    point = QPointF(g.header_width + 150, g.body_top + 80)
    event = QWheelEvent(point, point, QPoint(*pixels), QPoint(*angle), Qt.MouseButton.NoButton,
                        mods, Qt.ScrollPhase.ScrollUpdate, inverted)
    QApplication.sendEvent(view.viewport(), event)
    assert event.isAccepted()


def make_view():
    view = TimelineViewport(SyntheticTimelineAdapter(10000, 200))
    view.resize(900, 440)
    view.show()
    wait_until(lambda: view.paint_count > 0)
    return view


def navigation_case():
    view = make_view()
    try:
        g = view.geometry_state
        view.set_scroll(1000.125, 1000.125)
        before = view.geometry_state
        for _ in range(10):
            wheel(view, angle=(0, -1))
        g = view.geometry_state
        expected = before.scroll_y + before.row_height * QApplication.styleHints().wheelScrollLines() * 10 / 120
        assert abs(g.scroll_y - expected) < 1e-7 and g.scroll_x == before.scroll_x
        before = g
        wheel(view, angle=(0, -120), pixels=(0, -2))
        assert view.geometry_state.scroll_y == before.scroll_y + 2  # not angle+pixel
        before = view.geometry_state
        wheel(view, pixels=(-3, 0))
        assert view.geometry_state.scroll_x == before.scroll_x + 3
        before = view.geometry_state
        wheel(view, pixels=(0, -2), mods=Qt.KeyboardModifier.ShiftModifier)
        assert view.geometry_state.scroll_x == before.scroll_x + 2 and view.geometry_state.scroll_y == before.scroll_y
        before = view.geometry_state
        wheel(view, pixels=(0, 2), inverted=True)
        assert view.geometry_state.scroll_y == before.scroll_y - 2  # do not invert OS sign again
        before = view.geometry_state
        for _ in range(50):
            wheel(view, angle=(0, 15), mods=Qt.KeyboardModifier.ControlModifier)
            wheel(view, angle=(0, -15), mods=Qt.KeyboardModifier.ControlModifier)
        g = view.geometry_state
        error = abs(g.scroll_x - before.scroll_x)
        assert error < 1e-7 and abs(g.frame_width - before.frame_width) < 1e-8
        view.zoom_at(g.header_width + 100, 100)
        at_max = view.geometry_state
        view.zoom_at(at_max.header_width + 100, 2)
        assert view.geometry_state == at_max
        view.zoom_at(at_max.header_width + 100, 0.001)
        at_min = view.geometry_state
        view.zoom_at(at_min.header_width + 100, 0.5)
        assert view.geometry_state == at_min
        view.resize(620, 350)
        QApplication.processEvents()
        g = view.geometry_state
        assert view.horizontalScrollBar().maximum() == g.max_scroll_x
        assert view.verticalScrollBar().maximum() == g.max_scroll_y
        assert abs(view.horizontalScrollBar().value() - g.scroll_x) <= 0.5
        assert abs(view.verticalScrollBar().value() - g.scroll_y) <= 0.5
        for frame in g.visible_frames():
            if g.header_width <= g.frame_x(frame) < g.width:
                assert view.hit_test(g.frame_x(frame), g.ruler_height + 2).frame == frame
        assert not view.auto_timer.isActive()
        return {"wheel_sources_and_axes": True, "roundtrip50_error_dip": error,
                "zoom_limits_resize": True}
    finally:
        close_widget(view)


def begin_drag(view, direction="right", cells=False):
    view.set_body_mode("cells" if cells else "frames")
    view.set_scroll(1200, 1000)
    view.selection.select_frame(3)
    view.selection.select_key(0, 0)
    view.selection.select_layer(1)
    view.selection.playhead = 7
    snapshot = asdict(view.selection)
    g = view.geometry_state
    frame, row = g.visible_frames().start + 2, g.visible_rows().start + 2
    while view.adapter.has_key(row, frame):
        frame += 1
    point = QPoint(round(g.frame_x(frame)), round(g.row_y(row) if cells else g.ruler_height + 6))
    x = g.width + 60 if "right" in direction else g.header_width - 60 if "left" in direction else point.x()
    y = g.height + 60 if "down" in direction else g.body_top - 60 if "up" in direction else point.y()
    end = QPoint(round(x), round(y))
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    send_move(view, end)
    return snapshot, point, end, frame, row


def checkpoint_after_stop(view):
    assert not view.auto_timer.isActive()
    assert not QAbstractEventDispatcher.instance().registeredTimers(view.auto_timer)
    before = (view.auto_ticks, view.geometry_state.scroll_x, view.geometry_state.scroll_y, asdict(view.selection))
    # Observe future event-loop progress with another real timer, not a sleep.
    marker = QTimer(view)
    marker.setInterval(20)
    observations = []
    marker.timeout.connect(lambda: observations.append(True))
    marker.start()
    try:
        wait_until(lambda: len(observations) >= 2)
    finally:
        marker.stop()
        marker.deleteLater()
    assert before == (view.auto_ticks, view.geometry_state.scroll_x, view.geometry_state.scroll_y, asdict(view.selection))


def edge_case(direction, cells, frame_width=32):
    view = make_view()
    try:
        view.zoom_at(view.geometry_state.header_width, frame_width / 32)
        before, point, end, frame, row = begin_drag(view, direction, cells)
        initial = view.geometry_state
        pointer = view._pointer
        first_endpoint = view.selection.cells if cells else view.selection.primary
        wait_until(lambda: view.auto_ticks >= 3)
        g = view.geometry_state
        assert pointer == view._pointer  # no additional MouseMove events
        assert view.selection.playhead == 7 and view.selection.keys == {(0, 0)} and view.selection.layers == {1}
        if "right" in direction:
            assert g.scroll_x > initial.scroll_x
        if "left" in direction:
            assert g.scroll_x < initial.scroll_x
        if "down" in direction:
            assert g.scroll_y > initial.scroll_y
        if "up" in direction:
            assert g.scroll_y < initial.scroll_y
        if cells:
            assert view.selection.frames == {3}
            assert (view.selection.cells.anchor_frame, view.selection.cells.anchor_row) == (frame, row)
            assert view.selection.cells != first_endpoint
            assert view.selection.cells.active_frame == g.frame_at(end.x(), clamp=True)
            assert view.selection.cells.active_row == g.row_at(end.y(), clamp=True)
        else:
            assert view.selection.anchor == frame and view.selection.primary != first_endpoint
            assert g.scroll_y == initial.scroll_y and view.selection.cells is None
        assert abs(view.horizontalScrollBar().value() - g.scroll_x) <= 0.5
        assert abs(view.verticalScrollBar().value() - g.scroll_y) <= 0.5
        view.viewport().grab()
        assert view.last_paint["frame_headers"] == len(g.visible_frames())
        ticks, cost = view.auto_ticks, list(view.auto_tick_ms)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
        checkpoint_after_stop(view)
        return {"direction": direction, "mode": "cells" if cells else "frames", "stationary_ticks": ticks,
                "frame_width": frame_width,
                "tick_median_ms": median(cost), "tick_max_ms": max(cost),
                "paint_frames": view.last_paint["frame_headers"], "paint_rows": view.last_paint["row_headers"]}
    finally:
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(300, 100))
        close_widget(view)


def lifecycle_case(reason):
    view = make_view()
    try:
        before, point, end, _, _ = begin_drag(view, "right_down", cells=True)
        wait_until(lambda: view.auto_ticks >= 2)
        if reason == "escape":
            QTest.keyClick(view, Qt.Key.Key_Escape)
        elif reason == "focus":
            QApplication.sendEvent(view, QFocusEvent(QEvent.Type.FocusOut))
        elif reason == "capture":
            QApplication.sendEvent(view.viewport(), QEvent(QEvent.Type.UngrabMouse))
        elif reason == "hide":
            view.hide()
        elif reason == "close":
            view.close()
        assert view.interaction.mode == "idle" and asdict(view.selection) == before
        checkpoint_after_stop(view)
        return {"stop_reason": reason, "restored": True, "registered_auto_timers": 0}
    finally:
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(300, 100))
        close_widget(view)


def boundaries_case():
    view = make_view()
    try:
        for target_end in (False, True):
            view.set_body_mode("cells")
            g = view.geometry_state
            view.set_scroll(g.max_scroll_x - 2 if target_end else 2, g.max_scroll_y - 2 if target_end else 2)
            g = view.geometry_state
            frame, row = g.visible_frames().start + 2, g.visible_rows().start + 2
            while view.adapter.has_key(row, frame):
                frame += 1
            start = QPoint(round(g.frame_x(frame)), round(g.row_y(row)))
            end = QPoint(round(g.width + 100 if target_end else g.header_width - 100),
                         round(g.height + 100 if target_end else g.body_top - 100))
            QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
            send_move(view, end)
            ticks = view.auto_ticks
            wait_until(lambda: view.auto_ticks > ticks and not view.auto_timer.isActive())
            g = view.geometry_state
            assert g.scroll_x == (g.max_scroll_x if target_end else 0)
            assert g.scroll_y == (g.max_scroll_y if target_end else 0)
            QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
        # Returning to the body interior stops edge ownership immediately.
        _, start, end, _, _ = begin_drag(view, "right", False)
        wait_until(lambda: view.auto_ticks > 2)
        send_move(view, QPoint(500, 120))
        assert not view.auto_timer.isActive() and view.interaction.mode == "drag_frames"
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(500, 120))
        return {"start_end_stop": True, "edge_exit_stop": True}
    finally:
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(300, 100))
        close_widget(view)


def shell_visual_case(output):
    from .__main__ import create_demo
    window = create_demo(SyntheticTimelineAdapter(10000, 200))
    view = window.timeline
    try:
        window.show()
        wait_until(lambda: view.paint_count > 0)
        window.selection_mode.setCurrentIndex(1)
        assert view.body_mode == "cells"
        view.set_scroll(500, 200)
        g = view.geometry_state
        view.selection.cells = CellRange(g.visible_frames().start + 2, g.visible_rows().start + 1, 5000, 150)
        view.selection.active_domain = "cells"
        view.selection.playhead = g.visible_frames().start + 5
        view._notify()
        image = window.grab()
        assert image.save(str(output / "navigation-shell-ko-dark.png"))
        g = view.geometry_state
        event = QHelpEvent(QEvent.Type.ToolTip, QPoint(20, round(g.row_y(g.visible_rows().start + 1))), QPoint(20, 100))
        QApplication.sendEvent(view.viewport(), event)
        assert "레이어" in QToolTip.text() and "합성 트랙" in QToolTip.text()
        QToolTip.hideText()
        assert view.last_paint["cell_range_rects"] == 1
        window.language_selector.setCurrentIndex(1)
        window.theme_selector.setCurrentIndex(1)
        window.resize(620, 570)
        QApplication.processEvents()
        assert view.language == "en" and view.theme == "light" and view.body_mode == "cells"
        assert window.grab().save(str(output / "navigation-shell-en-light-narrow.png"))
        width = view.geometry_state.frame_width
        QTest.mouseClick(window.zoom_controls[1], Qt.MouseButton.LeftButton)
        assert view.geometry_state.frame_width > width
        QTest.mouseClick(window.zoom_controls[0], Qt.MouseButton.LeftButton)
        assert abs(view.geometry_state.frame_width - width) < 1e-8
        QTest.mouseClick(window.zoom_controls[2], Qt.MouseButton.LeftButton)
        assert view.geometry_state.frame_width == 8
        QTest.mouseClick(window.zoom_controls[3], Qt.MouseButton.LeftButton)
        assert view.geometry_state.frame_width == 32
        return {"mode_control": True, "long_label_tooltip": True,
                "screenshots": ["navigation-shell-ko-dark.png", "navigation-shell-en-light-narrow.png"]}
    finally:
        close_widget(window)


def large_selection_case():
    view = make_view()
    try:
        tracemalloc.start()
        start = perf_counter()
        view.selection.select_frame(0)
        view.selection.select_frame(9999, shift=True)
        view.selection.cells = CellRange(0, 0, 9999, 199)
        elapsed = (perf_counter() - start) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        view.set_scroll(5000, 1000)
        view.viewport().grab()
        assert len(view.selection.frames.intervals) == 1 and view.selection.cells.size == 2_000_000
        assert len(view.selection.cells.__dict__) == 4 and len(view.findChildren(QWidget)) == 5
        return {"frames": 10000, "tracks": 200, "logical_cells": 2_000_000,
                "frame_intervals": 1, "cell_range_fields": 4, "selection_ms": elapsed,
                "python_traced_peak_bytes": peak, "qwidget_descendants": 5,
                "visible_paint": view.last_paint.copy()}
    finally:
        close_widget(view)


def nonselection_case():
    view = make_view()
    try:
        view.selection.select_frame(3)
        for button, y in ((Qt.MouseButton.MiddleButton, 150), (Qt.MouseButton.LeftButton, 10)):
            view.set_scroll(1200, 1000)
            start = QPoint(500, y)
            end = QPoint(1050, 550)
            QTest.mousePress(view.viewport(), button, pos=start)
            send_move(view, end, button)
            assert not view.auto_timer.isActive() and view.auto_ticks == 0
            assert view.selection.frames == {3}
            QTest.keyClick(view, Qt.Key.Key_Escape)
            assert view.interaction.mode == "idle" and view.selection.frames == {3}
            QTest.mouseRelease(view.viewport(), button, pos=end)
        checkpoint_after_stop(view)
        return {"pan_scrub_do_not_own_timer": True, "escape_stops_pan": True}
    finally:
        close_widget(view)


def handle_case():
    view = make_view()
    try:
        view.zoom_at(view.geometry_state.header_width, 0.25)
        view.selection.playhead = 6
        view.selection.select_frame(3)
        g = view.geometry_state
        # At 8 DIP/frame the extended handle target overlaps a neighboring
        # frame; it must still grab this playhead rather than seek that frame.
        point = QPoint(round(g.frame_x(6) + 9), 8)
        assert g.frame_at(point.x()) != 6
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
        assert view.selection.playhead == 6 and view.selection.frames == {3}
        return {"handle_hit_width_dip": 20, "no_neighbor_jump": True}
    finally:
        close_widget(view)


def run_navigation_checks(output):
    checks = []
    cases = [("wheel_zoom_resize", navigation_case), ("bounds_edge_exit", boundaries_case),
             ("pan_scrub_exclusion", nonselection_case),
             ("playhead_handle", handle_case),
             ("shell_tooltip", lambda: shell_visual_case(output)), ("large_selection", large_selection_case)]
    cases += [("edge_" + direction + ("_cells" if cells else "_frames"),
               lambda direction=direction, cells=cells: edge_case(direction, cells))
              for direction, cells in (("right", False), ("left", False), ("right", True), ("left", True),
                                       ("down", True), ("up", True), ("right_down", True), ("left_up", True))]
    cases += [("stop_" + reason, lambda reason=reason: lifecycle_case(reason))
              for reason in ("escape", "focus", "capture", "hide", "close")]
    cases += [("edge_zoom_" + str(width), lambda width=width: edge_case("right_down", True, width))
              for width in (8, 160)]
    for name, function in cases:
        try:
            checks.append({"id": name, "status": "PASS", "observed": function()})
        except Exception as error:
            checks.append({"id": name, "status": "FAIL", "reason": type(error).__name__ + ": " + str(error)[:180]})
    return {"status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL", "checks": checks}
