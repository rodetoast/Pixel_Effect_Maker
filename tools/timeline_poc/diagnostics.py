"""Independent bounded checks/metrics; deliberately not in the core registry."""

from dataclasses import asdict, replace
import platform
from statistics import median
from time import perf_counter
import tracemalloc

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QCoreApplication, QElapsedTimer, QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QFont, QFontInfo, QImage, QMouseEvent, QRawFont, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QWidget

from .adapter import SyntheticTimelineAdapter
from .geometry import HitTarget, TimelineGeometry
from .fonts import timeline_font
from .interaction import TimelineInteraction
from .selection import TimelineSelection
from .view import TimelineViewport


def wait_until(predicate, timeout_ms=1500):
    timer = QElapsedTimer()
    timer.start()
    while not predicate():
        if timer.elapsed() >= timeout_ms:
            raise AssertionError("Qt completion timeout")
        QApplication.processEvents()


def close_widget(widget):
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def geometry_checks():
    checks = 0
    for count in (12, 120, 1000, 10000):
        for width in (8.0, 31.5, 160.0):
            for offset in (0, 7.25, max(0, count * width - 700)):
                g = TimelineGeometry(count, 200, frame_width=width, scroll_x=offset, scroll_y=13.5)
                for frame in g.visible_frames():
                    x = g.frame_x(frame)
                    if g.header_width <= x < g.width:
                        assert g.frame_at(x) == frame, "frame roundtrip"
                        assert g.hit_test(x, g.ruler_height + 1).frame == frame
                        checks += 1
                for row in g.visible_rows():
                    y = g.row_y(row)
                    if g.body_top <= y < g.height:
                        assert g.row_at(y) == row, "row roundtrip"
                assert g.hit_test(-1, 10).kind == "outside"
                assert g.hit_test(g.width, 10).kind == "outside"
                x = g.header_width + 160
                zoomed = g.zoom_at(x, 1.15)
                if 0 < zoomed.scroll_x < zoomed.max_scroll_x:
                    assert abs((x - g.header_width + g.scroll_x) / g.frame_width -
                               (x - zoomed.header_width + zoomed.scroll_x) / zoomed.frame_width) < 1e-8
    return {"frame_roundtrips": checks, "counts": [12, 120, 1000, 10000]}


def selection_checks():
    state = TimelineSelection(playhead=9)
    state.select_key(1, 5)
    state.select_layer(3)
    state.select_frame(2)
    state.select_frame(6, shift=True)
    assert state.frames == set(range(2, 7))
    state.select_frame(4, ctrl=True)
    assert state.frames == {2, 3, 5, 6}
    assert state.keys == {(1, 5)} and state.layers == {3} and state.playhead == 9
    state.seek(0, 120)
    assert state.frames == {2, 3, 5, 6}
    state.select_frame(119)
    state.select_frame(119, ctrl=True)
    assert not state.frames and state.primary is None
    g = TimelineGeometry(120, 20)
    control = TimelineInteraction(state)
    before = asdict(state)
    control.press(HitTarget("frame", 2), 200, 30)
    control.move(201, 30, g, 10)
    assert control.mode == "pressed_frames" and state.frames == {2}
    control.move(g.frame_x(6), 30, g, 10)
    assert state.frames == set(range(2, 7)) and control.mode == "drag_frames"
    control.cancel()
    assert asdict(state) == before
    return {"independent_domains": ["frames", "keys", "layers", "playhead"], "cancel_restored": True}


def send_move(view, point, button=Qt.MouseButton.LeftButton):
    event = QMouseEvent(QEvent.Type.MouseMove, QPointF(point), QPointF(point),
                       Qt.MouseButton.NoButton, button, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view.viewport(), event)


def qt_checks(view):
    """Only synthetic QTest input; selection and playhead have separate oracles."""
    g = view.geometry_state
    header = lambda n: QPoint(round(g.frame_x(n)), round(g.ruler_height + g.frame_header_height / 2))
    click = lambda n, mods=Qt.KeyboardModifier.NoModifier: QTest.mouseClick(
        view.viewport(), Qt.MouseButton.LeftButton, mods, header(n))
    click(2)
    click(6, Qt.KeyboardModifier.ShiftModifier)
    click(4, Qt.KeyboardModifier.ControlModifier)
    assert view.selection.frames == {2, 3, 5, 6}
    assert view.selection.playhead == 0, "frame selection must not seek"
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=header(2))
    send_move(view, header(8))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=header(8))
    assert view.selection.frames == set(range(2, 9))
    selected = set(view.selection.frames)
    ruler = QPoint(round(g.frame_x(5)), 10)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=ruler)
    end = QPoint(round(g.frame_x(8)), 10)
    send_move(view, end)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert view.selection.playhead == 8 and view.selection.frames == selected
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert view.selection.playhead == 9 and view.selection.frames == selected
    key_point = QPoint(round(g.frame_x(0)), round(g.row_y(0)))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=key_point)
    assert view.selection.keys == {(0, 0)} and view.selection.frames == selected
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(25, round(g.row_y(1))))
    assert view.selection.layers == {1} and view.selection.keys == {(0, 0)}

    view.horizontalScrollBar().setValue(190)
    view.verticalScrollBar().setValue(40)
    g = view.geometry_state
    x = g.header_width + 140
    coordinate = (x - g.header_width + g.scroll_x) / g.frame_width
    wheel = QWheelEvent(QPointF(x, 100), QPointF(x, 100), QPoint(), QPoint(0, 120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(view.viewport(), wheel)
    g = view.geometry_state
    zoom_error_dip = abs((x - g.header_width + g.scroll_x) - coordinate * g.frame_width)
    assert zoom_error_dip <= 0.500001
    for frame in g.visible_frames():
        if g.header_width <= g.frame_x(frame) < g.width:
            assert view.hit_test(g.frame_x(frame), g.ruler_height + 2).frame == frame
    assert view.selection.playhead == 9 and view.selection.frames == selected
    point = QPoint(500, 160)
    before = (view.horizontalScrollBar().value(), view.verticalScrollBar().value())
    QTest.mousePress(view.viewport(), Qt.MouseButton.MiddleButton, pos=point)
    send_move(view, point - QPoint(60, 20), Qt.MouseButton.MiddleButton)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.MiddleButton, pos=point - QPoint(60, 20))
    assert view.horizontalScrollBar().value() > before[0] and view.verticalScrollBar().value() > before[1]
    assert view.interaction.mode == "idle"
    # No unbounded timer/worker exists in this POC. Cancel must discard only
    # tentative selection, and native focus/Tab are left to Qt.
    g = view.geometry_state
    before_selection = asdict(view.selection)
    target = g.visible_frames().start + 2
    point = QPoint(round(g.frame_x(target)), round(g.ruler_height + 4))
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    QTest.keyClick(view, Qt.Key.Key_Escape)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert asdict(view.selection) == before_selection
    QTest.keyClick(view, Qt.Key.Key_End)
    assert view.selection.playhead == 119 and view.selection.frames == selected
    QTest.keyClick(view, Qt.Key.Key_Home)
    assert view.selection.playhead == 0 and view.selection.frames == selected
    QTest.keyClick(view, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    assert view.selection.playhead == 0, "shift selection must not seek"
    assert view.accessibleName() and view.accessibleDescription()
    assert view.adapter == SyntheticTimelineAdapter(120, 24), "synthetic data mutated"
    return {"mouse_keyboard": True, "zoom_anchor_error_dip": zoom_error_dip}


def _redraw_metrics(widget, samples=9):
    elapsed = []
    for _ in range(samples):
        start = perf_counter()
        widget.viewport().grab()
        elapsed.append((perf_counter() - start) * 1000)
    return {"samples": samples, "grab_median_ms": median(elapsed),
            "grab_p95_ms": sorted(elapsed)[-1]}


def benchmark_view(app, frames, rows):
    tracemalloc.start()
    start = perf_counter()
    view = TimelineViewport(SyntheticTimelineAdapter(frames, rows))
    init_ms = (perf_counter() - start) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    try:
        view.resize(900, 440)
        view.show()
        wait_until(lambda: view.paint_count > 0)
        g = view.geometry_state
        view.horizontalScrollBar().setValue(min(g.max_scroll_x, frames // 2 * 32))
        view.verticalScrollBar().setValue(min(g.max_scroll_y, rows // 2 * round(g.row_height)))
        metrics = _redraw_metrics(view)
        stats = view.last_paint
        g = view.geometry_state
        assert stats["frame_headers"] == len(g.visible_frames())
        assert stats["row_headers"] == stats["key_queries"] == len(g.visible_rows())
        expected_keys = sum(len(view.adapter.keys_in(row, g.visible_frames().start, g.visible_frames().stop))
                            for row in g.visible_rows())
        assert stats["keys_drawn"] == expected_keys
        assert len(view.findChildren(QWidget)) < 12
        # Exercise actual View hit testing (including key lookup), not merely
        # theoretical O(1) mapping. Points span body + both frozen headers.
        start = perf_counter()
        hits = {}
        for index in range(1000):
            target = view.hit_test((index * 37) % max(1, g.width), (index * 23) % max(1, g.height))
            hits[target.kind] = hits.get(target.kind, 0) + 1
        hit_ms = (perf_counter() - start) * 1000
        return {"frames": frames, "tracks": rows, "init_ms": init_ms,
                "python_traced_peak_bytes": peak, "qwidget_descendants": len(view.findChildren(QWidget)),
                "qtable_descendants": len(view.findChildren(QTableWidget)),
                "hit_test_queries": 1000, "hit_test_total_ms": hit_ms, "hit_target_counts": hits,
                **metrics, "paint": stats.copy()}
    finally:
        close_widget(view)


def benchmark_table(frames, rows):
    """Minimal generic table, NOT production refresh/render or feature parity."""
    tracemalloc.start()
    start = perf_counter()
    table = QTableWidget(rows, frames)
    table.setFont(timeline_font())
    table.setUpdatesEnabled(False)
    for row in range(rows):
        for frame in range(frames):
            table.setItem(row, frame, QTableWidgetItem("·"))
    table.horizontalHeader().setDefaultSectionSize(32)
    table.verticalHeader().setDefaultSectionSize(28)
    init_ms = (perf_counter() - start) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    try:
        table.resize(900, 440)
        table.setUpdatesEnabled(True)
        table.show()
        QApplication.processEvents()
        return {"frames": frames, "tracks": rows, "items_allocated": frames * rows,
                "init_ms": init_ms, "python_traced_peak_bytes": peak, **_redraw_metrics(table)}
    finally:
        close_widget(table)


def visual_matrix(app, output):
    images = []
    for scale in (1, 1.25, 1.5):
        for language in ("en", "ko"):
            for theme in ("light", "dark"):
                view = TimelineViewport(SyntheticTimelineAdapter(10000, 200), language=language, theme=theme)
                try:
                    font = QFont(view.font())
                    font.setPointSizeF(9 * scale)
                    view.setFont(font)
                    view.resize(620 if language == "ko" else 900, 440)
                    view.show()
                    wait_until(lambda: view.paint_count > 0)
                    view.selection.select_frame(3)
                    view.selection.select_frame(8, shift=True)
                    view.selection.select_key(0, 12)
                    view.selection.select_layer(1)
                    view.selection.playhead = 5
                    image = view.viewport().grab()
                    name = f"{language}-{theme}-font{round(scale * 100)}.png"
                    assert image.save(str(output / name)), "screenshot save"
                    g = view.geometry_state
                    raw_font = QRawFont.fromFont(view.font())
                    assert raw_font.isValid() and raw_font.familyName(), "font must resolve to an installed family"
                    assert all(raw_font.supportsCharacter(code) for code in (49, 65, 54620)), "Latin/digit/Korean glyph support"
                    assert g.row_height >= view.fontMetrics().height() + 8
                    assert g.frame_header_height >= view.fontMetrics().height() + 6
                    assert image.width() == round(view.viewport().width() * image.devicePixelRatioF())
                    loaded = QImage(str(output / name))
                    assert not loaded.isNull() and loaded.width() == image.width()
                    images.append({"file": name, "language": language, "theme": theme,
                                   "font_scale": scale, "dpr": image.devicePixelRatioF(),
                                   "resolved_font": QFontInfo(view.font()).family(),
                                   "physical_width": image.width(), "physical_height": image.height(),
                                   "row_height_dip": g.row_height,
                                   "visible_frames": len(g.visible_frames()), "visible_rows": len(g.visible_rows())})
                finally:
                    close_widget(view)
    return images


def run_probe(output, *, compare_table=False):
    app = QApplication.instance() or QApplication([])
    report = {"schema_version": 1, "status": "PASS", "synthetic_only": True,
              "environment": {"platform": platform.system(), "python": platform.python_version(),
                              "pyside": pyside_version, "qt_platform": app.platformName(), "style": app.style().objectName()},
              "checks": [], "metrics": [], "screenshots": [], "table_baseline": [],
              "limitations": ["No virtual-cell accessibility interface", "No native Windows/IME/manual QA",
                              "Font scale and process DPR are independent synthetic checks",
                              "QWidget.grab includes paint+image allocation, not screen latency",
                              "tracemalloc excludes Qt native allocations; minimal table is not production parity"]}
    view = TimelineViewport()
    view.resize(900, 440)
    view.show()
    wait_until(lambda: view.paint_count > 0)
    report["dpr"] = view.devicePixelRatioF()
    try:
        for name, function in (("geometry", geometry_checks), ("selection", selection_checks),
                               ("qt_input", lambda: qt_checks(view))):
            try:
                result = function()
                report["checks"].append({"id": name, "status": "PASS", "observed": result})
            except Exception as error:
                report["checks"].append({"id": name, "status": "FAIL", "reason": type(error).__name__ + ": " + str(error)[:240]})
                report["status"] = "FAIL"
    finally:
        close_widget(view)
    try:
        for frames in (12, 120, 1000, 10000):
            for rows in (4, 24, 200):
                report["metrics"].append(benchmark_view(app, frames, rows))
        report["screenshots"] = visual_matrix(app, output)
        if compare_table:
            for frames, rows in ((12, 24), (120, 24), (1000, 24), (10000, 4)):
                report["table_baseline"].append(benchmark_table(frames, rows))
    except Exception as error:
        report["status"] = "FAIL"
        report["checks"].append({"id": "viewport_metrics_visual", "status": "FAIL",
                                 "reason": type(error).__name__ + ": " + str(error)[:240]})
    report["application_top_level_widgets_after_cleanup"] = len(app.topLevelWidgets())
    from .navigation_probe import run_navigation_checks
    report["navigation"] = run_navigation_checks(output)
    if report["navigation"]["status"] != "PASS":
        report["status"] = "FAIL"
    report["application_top_level_widgets_after_navigation"] = len(app.topLevelWidgets())
    return report
