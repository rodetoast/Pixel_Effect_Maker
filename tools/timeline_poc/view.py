"""Standalone QAbstractScrollArea; all paint and events use viewport DIP space."""

from dataclasses import replace
from time import perf_counter

from PySide6.QtCore import QElapsedTimer, QEvent, QTimer, Signal, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QToolTip

from .adapter import SyntheticTimelineAdapter
from .geometry import HitTarget, TimelineGeometry
from .fonts import timeline_font
from .interaction import TimelineInteraction
from .paint import LABELS, TimelinePaint, TimelinePalette
from .selection import TimelineSelection
from .navigation import wheel_motion
from .autoscroll import EdgePolicy


class TimelineViewport(QAbstractScrollArea):
    state_changed = Signal()

    def __init__(self, adapter=None, *, language="en", theme="dark", parent=None):
        super().__init__(parent)
        self.adapter = adapter or SyntheticTimelineAdapter()
        self.selection = TimelineSelection()
        self.interaction = TimelineInteraction(self.selection)
        self.timeline_paint = TimelinePaint()
        self.geometry_state = TimelineGeometry(self.adapter.frame_count, self.adapter.row_count)
        self.last_paint = {}
        self.paint_count = 0
        self.body_mode = "frames"
        self._updating_scroll = False
        self._selection_held = False
        self._pointer = (0, 0)
        self.edge_policy = EdgePolicy()
        self.auto_timer = QTimer(self)
        self.auto_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.auto_timer.setInterval(16)
        self.auto_timer.timeout.connect(self._auto_tick)
        self._auto_clock = QElapsedTimer()
        self.auto_ticks = 0
        self.auto_tick_ms = []
        self.language, self.theme = language, theme
        self.colors = TimelinePalette.for_theme(theme)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFont(timeline_font())
        self.viewport().setMouseTracking(True)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.set_labels(language)
        self.sync_geometry()

    def set_labels(self, language):
        if language not in LABELS:
            raise ValueError("language must be en or ko")
        self.language = language
        self.setAccessibleName(LABELS[language]["title"])
        self.setAccessibleDescription(LABELS[language]["help"])
        self.viewport().setToolTip(LABELS[language]["help"])
        self.viewport().update()

    def set_theme(self, theme):
        self.colors = TimelinePalette.for_theme(theme)
        self.theme = theme
        self.viewport().update()

    def sync_geometry(self):
        if not hasattr(self, "geometry_state"):
            return
        fm = self.fontMetrics()
        self.geometry_state = replace(self.geometry_state,
            width=self.viewport().width(), height=self.viewport().height(),
            row_height=max(28, fm.height() + 10),
            ruler_height=max(28, fm.height() + 8), frame_header_height=max(26, fm.height() + 8),
            header_width=min(220, max(110, self.viewport().width() * 0.25)))
        g = self.geometry_state
        self.geometry_state = replace(g, scroll_x=min(g.scroll_x, g.max_scroll_x),
                                      scroll_y=min(g.scroll_y, g.max_scroll_y))
        self._updating_scroll = True
        self.horizontalScrollBar().setRange(0, g.max_scroll_x)
        self.horizontalScrollBar().setPageStep(int(g.body_width))
        self.horizontalScrollBar().setSingleStep(max(1, round(g.frame_width)))
        self.verticalScrollBar().setRange(0, g.max_scroll_y)
        self.verticalScrollBar().setPageStep(int(g.body_height))
        self.verticalScrollBar().setSingleStep(round(g.row_height))
        self.horizontalScrollBar().setValue(round(self.geometry_state.scroll_x))
        self.verticalScrollBar().setValue(round(self.geometry_state.scroll_y))
        self._updating_scroll = False

    def scrollContentsBy(self, dx, dy):
        if hasattr(self, "geometry_state") and not self._updating_scroll:
            g = self.geometry_state
            self.geometry_state = replace(g,
                scroll_x=self.horizontalScrollBar().value() if dx else g.scroll_x,
                scroll_y=self.verticalScrollBar().value() if dy else g.scroll_y)
            self._refresh_selection_endpoint()
            self.viewport().update()

    def set_scroll(self, x, y):
        g = self.geometry_state
        self.geometry_state = replace(g, scroll_x=max(0, min(g.max_scroll_x, x)),
                                      scroll_y=max(0, min(g.max_scroll_y, y)))
        self._updating_scroll = True
        self.horizontalScrollBar().setValue(round(self.geometry_state.scroll_x))
        self.verticalScrollBar().setValue(round(self.geometry_state.scroll_y))
        self._updating_scroll = False
        self._refresh_selection_endpoint()
        self.viewport().update()

    def set_body_mode(self, mode):
        if mode not in {"frames", "cells"}:
            raise ValueError("body mode must be frames or cells")
        self.cancel_gesture()
        self.body_mode = mode
        self._notify()

    def cancel_gesture(self):
        self.auto_timer.stop()
        self._selection_held = False
        self.interaction.cancel()
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def _refresh_selection_endpoint(self):
        if self.interaction.mode in {"drag_frames", "drag_cells"}:
            self.interaction.move(*self._pointer, self.geometry_state, QApplication.startDragDistance())

    def _update_auto_timer(self):
        g = self.geometry_state
        delta = self.edge_policy.motion(g, *self._pointer, self.interaction.mode, 0.016)
        if self._selection_held and self.isVisible() and self.viewport().isVisible() and any(delta):
            if not self.auto_timer.isActive():
                self._auto_clock.start()
                self.auto_timer.start()
        else:
            self.auto_timer.stop()

    def _auto_tick(self):
        start = perf_counter()
        if (not self._selection_held or not self.isVisible() or not self.viewport().isVisible()
                or not QApplication.mouseButtons() & Qt.MouseButton.LeftButton
                or self.interaction.mode not in {"drag_frames", "drag_cells"}):
            self.auto_timer.stop()
            return
        elapsed = self._auto_clock.nsecsElapsed() / 1e9
        self._auto_clock.restart()
        dx, dy = self.edge_policy.motion(self.geometry_state, *self._pointer, self.interaction.mode, elapsed)
        if not (dx or dy):
            self.auto_timer.stop()
            return
        g = self.geometry_state
        self.set_scroll(g.scroll_x + dx, g.scroll_y + dy)
        self.auto_ticks += 1
        self._notify()
        self._update_auto_timer()
        # Bounded instrumentation; never queue per-tick work or model rebuilds.
        self.auto_tick_ms.append((perf_counter() - start) * 1000)
        if len(self.auto_tick_ms) > 128:
            del self.auto_tick_ms[:-128]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_geometry()
        self._refresh_selection_endpoint()
        self._update_auto_timer()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self.sync_geometry()

    def paintEvent(self, event):
        start = perf_counter()
        painter = QPainter(self.viewport())
        self.last_paint = self.timeline_paint.draw(painter, self.geometry_state, self.adapter,
            self.selection, self.colors, self.language, self.hasFocus())
        painter.end()
        self.paint_count += 1
        self.last_paint["paint_ms"] = (perf_counter() - start) * 1000
        self.last_paint["dpr"] = self.devicePixelRatioF()

    def hit_test(self, x, y):
        g = self.geometry_state
        target = g.hit_test(x, y)
        if target.kind == "ruler" and y <= 18 and abs(x - g.frame_x(self.selection.playhead)) <= 10:
            return HitTarget("ruler", self.selection.playhead)
        if target.kind == "cell":
            for frame in (target.frame, target.frame - 1, target.frame + 1):
                if self.adapter.has_key(target.row, frame) and (
                    abs(x - g.frame_x(frame)) <= 7 and abs(y - g.row_y(target.row)) <= 7):
                    return HitTarget("key", frame, target.row)
            if self.body_mode == "cells":
                return HitTarget("cell_range", target.frame, target.row)
        return target

    def _notify(self):
        self.viewport().update()
        self.state_changed.emit()

    def mousePressEvent(self, event):
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            super().mousePressEvent(event)
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        point, mods = event.position(), event.modifiers()
        self._pointer = (point.x(), point.y())
        self.auto_timer.stop()
        self._selection_held = event.button() == Qt.MouseButton.LeftButton
        g = self.geometry_state
        self.interaction.press(self.hit_test(point.x(), point.y()), point.x(), point.y(),
            button="middle" if event.button() == Qt.MouseButton.MiddleButton else "left",
            shift=bool(mods & Qt.KeyboardModifier.ShiftModifier),
            ctrl=bool(mods & Qt.KeyboardModifier.ControlModifier), scroll=(g.scroll_x, g.scroll_y))
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor if self.interaction.mode == "pan"
                                  else Qt.CursorShape.CrossCursor)
        self._notify()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.interaction.mode == "idle":
            super().mouseMoveEvent(event)
            return
        point = event.position()
        self._pointer = (point.x(), point.y())
        scroll = self.interaction.move(point.x(), point.y(), self.geometry_state, QApplication.startDragDistance())
        if scroll is not None:
            self.set_scroll(*scroll)
        self._update_auto_timer()
        self._notify()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self.auto_timer.stop()
            self._selection_held = False
            self.interaction.finish()
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            self._notify()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def focusOutEvent(self, event):
        self.cancel_gesture()
        self.viewport().update()
        super().focusOutEvent(event)

    def closeEvent(self, event):
        self.cancel_gesture()
        super().closeEvent(event)

    def hideEvent(self, event):
        if hasattr(self, "auto_timer"):
            self.cancel_gesture()
        super().hideEvent(event)

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.ToolTip and hasattr(self, "geometry_state"):
            hit = self.hit_test(event.pos().x(), event.pos().y())
            text = self.adapter.row_label(hit.row, self.language) if hit.kind == "layer" else LABELS[self.language]["help"]
            QToolTip.showText(event.globalPos(), text, self.viewport())
            return True
        if event.type() == QEvent.Type.UngrabMouse and hasattr(self, "interaction") and self.interaction.mode != "idle":
            self.cancel_gesture()
            self._notify()
        if event.type() == QEvent.Type.Hide and hasattr(self, "auto_timer"):
            self.cancel_gesture()
        return super().viewportEvent(event)

    def zoom_at(self, x, factor):
        zoomed = self.geometry_state.zoom_at(x, factor)
        self.geometry_state = zoomed
        self.sync_geometry()
        self.set_scroll(zoomed.scroll_x, zoomed.scroll_y)
        self.viewport().update()
        self.state_changed.emit()

    def wheelEvent(self, event):
        mods, pixels, angle = event.modifiers(), event.pixelDelta(), event.angleDelta()
        kind, a, b = wheel_motion(self.geometry_state, (angle.x(), angle.y()), (pixels.x(), pixels.y()),
            shift=bool(mods & Qt.KeyboardModifier.ShiftModifier),
            ctrl=bool(mods & Qt.KeyboardModifier.ControlModifier), lines=QApplication.styleHints().wheelScrollLines())
        if kind == "zoom":
            self.zoom_at(event.position().x(), a)
        else:
            g = self.geometry_state
            self.set_scroll(g.scroll_x + a, g.scroll_y + b)
        event.accept()

    def keyPressEvent(self, event):
        names = {Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right", Qt.Key.Key_Home: "home",
                 Qt.Key.Key_End: "end", Qt.Key.Key_Escape: "escape"}
        mods = event.modifiers()
        if not mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier) and (
            event.key() in names and self.interaction.key(names[event.key()], self.adapter.frame_count,
                shift=bool(mods & Qt.KeyboardModifier.ShiftModifier))):
            self.auto_timer.stop()
            self._selection_held = False
            frame = self.selection.primary if mods & Qt.KeyboardModifier.ShiftModifier else self.selection.playhead
            if frame is not None:
                self.reveal_frame(frame)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            self._notify()
            event.accept()
            return
        super().keyPressEvent(event)

    def zoom_step(self, direction):
        g = self.geometry_state
        self.zoom_at(g.header_width + g.body_width / 2, 1.15 ** direction)

    def fit_frames(self):
        g = self.geometry_state
        self.zoom_at(g.header_width, max(8, min(160, g.body_width / g.frame_count)) / g.frame_width)
        self.set_scroll(0, g.scroll_y)

    def reset_zoom(self):
        self.zoom_at(self.geometry_state.header_width + self.geometry_state.body_width / 2,
                     32 / self.geometry_state.frame_width)

    def reveal_frame(self, frame):
        g = self.geometry_state
        left, right = g.frame_x(frame, False), g.frame_x(frame, False) + g.frame_width
        if left < g.header_width:
            self.horizontalScrollBar().setValue(round(frame * g.frame_width))
        elif right > g.width:
            self.horizontalScrollBar().setValue(round((frame + 1) * g.frame_width - g.body_width))
