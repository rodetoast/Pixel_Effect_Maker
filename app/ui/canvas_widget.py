"""Integer-scaled pixel canvas widget."""

from __future__ import annotations

import numpy as np
from copy import deepcopy
import math
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget

from app.models.project import Project
from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.particle_emitter import ParticleEmitterSettings
from app.services.particle_render_service import representative_particle_guide
from app.services.resource_composition_render_service import render_composition_frames


class CanvasWidget(QWidget):
    """Render the current frame over a checkerboard without pixel smoothing."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self._project_size: tuple[int, int] | None = None
        self.frame_index = 0
        self.layer_index = 0
        self.zoom = 8
        self.pan_offset = QPointF()
        self._panning = False
        self._pan_last = QPointF()
        self.preview_frames: list[np.ndarray] | None = None
        self.preview_layer_id: str | None = None
        self.preview_badge_text = "PREVIEW"
        self.gizmo_generator_id: str | None = None
        self.gizmo_settings = None
        self.gizmo_mode = "move"
        self.gizmo_edit_end = False
        self.gizmo_locked = False
        self._gizmo_drag = False
        self._gizmo_before = None
        self.effect_guide_id: str | None = None
        self.effect_guide_kind: str | None = None
        self.effect_guide_settings = None
        self.show_effect_guides = True
        self._guide_handle: str | None = None
        self._guide_hover: str | None = None
        self._guide_before = None
        self._guide_last_canvas_point: tuple[int, int] | None = None
        self._ghost_cache: dict[tuple, list[QPixmap]] = {}
        self.setMinimumSize(320, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def set_project(self, project: Project) -> None:
        size = (project.width, project.height)
        context_changed = self.project is not project or self._project_size != size
        self.project = project
        self._project_size = size
        self.frame_index = 0
        self.layer_index = 0
        if context_changed:
            self.pan_offset = QPointF()
            self._ghost_cache.clear()
            self._fit_initial_zoom()
        self.update()

    def set_preview(
        self, frames: list[np.ndarray], generated_layer_id: str | None
    ) -> None:
        """Display transient frames without writing them into the project."""
        self.preview_frames = frames or None
        self.preview_layer_id = generated_layer_id
        if self.preview_frames is not None:
            self.frame_index = min(self.frame_index, len(self.preview_frames) - 1)
        self.update()

    def clear_preview(self) -> None:
        self.preview_frames = None
        self.preview_layer_id = None
        if self.project is not None:
            self.frame_index = min(self.frame_index, len(self.project.frames) - 1)
        self.update()

    def set_gizmo(self, generator_id: str | None, settings=None, *, mode: str = "move", edit_end: bool = False, locked: bool = False) -> None:
        self.gizmo_generator_id = generator_id
        self.gizmo_settings = deepcopy(settings)
        self.gizmo_mode = mode
        self.gizmo_edit_end = edit_end
        self.gizmo_locked = locked
        self.update()

    def set_effect_guide(self, identifier: str | None, kind: str | None = None, settings=None) -> None:
        self.effect_guide_id = identifier
        self.effect_guide_kind = kind
        self.effect_guide_settings = deepcopy(settings)
        self._guide_handle = self._guide_hover = None
        self.update()

    def set_effect_guides_visible(self, visible: bool) -> None:
        self.show_effect_guides = bool(visible)
        self.update()

    def canvas_to_widget(self, x: float, y: float) -> QPointF:
        if self.project is None: return QPointF()
        origin = self._canvas_origin()
        return QPointF(origin.x() + x * self.zoom, origin.y() + y * self.zoom)

    def widget_to_canvas(self, point: QPointF) -> QPointF:
        origin = self._canvas_origin()
        return QPointF((point.x() - origin.x()) / self.zoom, (point.y() - origin.y()) / self.zoom)

    def _canvas_origin(self) -> QPoint:
        if self.project is None: return QPoint()
        return QPoint(round((self.width() - self.project.width * self.zoom) / 2 + self.pan_offset.x()),
                      round((self.height() - self.project.height * self.zoom) / 2 + self.pan_offset.y()))

    def set_frame(self, index: int) -> None:
        self.frame_index = index
        self.update()

    def set_layer(self, index: int) -> None:
        self.layer_index = index
        self.update()

    def _fit_initial_zoom(self) -> None:
        if self.project:
            self.zoom = max(1, min(16, 512 // max(self.project.width, self.project.height)))

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.zoom = max(1, min(32, self.zoom + delta))
        self.update()
        event.accept()

    def paintEvent(self, event: object) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#20242b"))
        if not self.project or not self.project.frames:
            painter.setPen(QColor("#adb5bd"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No project")
            return

        width = self.project.width * self.zoom
        height = self.project.height * self.zoom
        origin = self._canvas_origin()
        canvas_rect = QRect(origin.x(), origin.y(), width, height)
        painter.setClipRect(canvas_rect)

        checker = max(1, 8 * self.zoom)
        colors = (QColor("#b8bdc4"), QColor("#e1e4e8"))
        for y in range(origin.y(), origin.y() + height, checker):
            for x in range(origin.x(), origin.x() + width, checker):
                color = colors[((x - origin.x()) // checker + (y - origin.y()) // checker) % 2]
                painter.fillRect(x, y, checker, checker, color)

        pixels: np.ndarray = np.ascontiguousarray(self._compose_display_frame())
        image = QImage(
            pixels.data,
            self.project.width,
            self.project.height,
            pixels.strides[0],
            QImage.Format.Format_RGBA8888,
        ).copy()
        pixmap = QPixmap.fromImage(image)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(canvas_rect, pixmap)
        painter.setClipping(False)
        painter.setPen(QColor("#77808c"))
        painter.drawRect(canvas_rect.adjusted(0, 0, -1, -1))
        if self.preview_frames is not None:
            badge = QRect(origin.x() + 6, origin.y() + 6, 74, 24)
            painter.fillRect(badge, QColor(30, 30, 30, 210))
            painter.setPen(QColor("#ffd166"))
            painter.drawText(
                badge, Qt.AlignmentFlag.AlignCenter, self.preview_badge_text
            )
        if self.gizmo_generator_id and self.gizmo_settings is not None and not self.gizmo_locked:
            self._paint_gizmo(painter)
        if self.show_effect_guides and self.effect_guide_id and self.effect_guide_settings is not None:
            self._paint_effect_guide(painter)

    def _gizmo_center(self) -> tuple[float, float]:
        s = self.gizmo_settings
        x, y = float(s.origin_x), float(s.origin_y)
        if self.gizmo_mode != "distribution" and hasattr(s, "offset_x_start"):
            x += float(s.offset_x_end if self.gizmo_edit_end else s.offset_x_start)
            y += float(s.offset_y_end if self.gizmo_edit_end else s.offset_y_start)
        return x, y

    def _paint_gizmo(self, painter: QPainter) -> None:
        x, y = self._gizmo_center(); center = self.canvas_to_widget(x, y)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#51cf66"), 2)); painter.setBrush(QColor("#20242b"))
        painter.drawEllipse(center, 6, 6)
        s = self.gizmo_settings
        if self.gizmo_mode == "rotate":
            angle = float(s.rotation_end if self.gizmo_edit_end else s.rotation_start)
            end = center + QPointF(math.cos(math.radians(angle)) * 48, math.sin(math.radians(angle)) * 48)
            painter.drawLine(center, end); painter.drawEllipse(end, 5, 5)
        elif self.gizmo_mode == "scale":
            sx = abs(float(s.scale_x_end if self.gizmo_edit_end else s.scale_x_start)); sy = abs(float(s.scale_y_end if self.gizmo_edit_end else s.scale_y_start))
            rect = QRect(round(center.x() - 24*sx), round(center.y() - 24*sy), round(48*sx), round(48*sy))
            painter.drawRect(rect); painter.drawRect(rect.right()-4, rect.bottom()-4, 8, 8)
        elif self.gizmo_mode == "distribution":
            if getattr(s, "distribution", "Point") == "Line":
                end = self.canvas_to_widget(s.line_end_x, s.line_end_y); painter.drawLine(center, end); painter.drawEllipse(end, 5, 5)
            elif getattr(s, "distribution", "Point") == "Circle":
                radius = max(0.0, float(s.radius)) * self.zoom; painter.drawEllipse(center, radius, radius)

    def _guide_points(self) -> dict[str, QPointF]:
        settings = self.effect_guide_settings
        if isinstance(settings, EffectCompositionLayer):
            return {
                "start": self.canvas_to_widget(settings.start_x, settings.start_y),
                "end": self.canvas_to_widget(settings.end_x, settings.end_y),
            }
        if isinstance(settings, ParticleEmitterSettings):
            guide = representative_particle_guide(settings)
            origin = self.canvas_to_widget(guide["origin_x"], guide["origin_y"])
            endpoint = self.canvas_to_widget(guide["endpoint_x"], guide["endpoint_y"])
            angle = math.radians(settings.direction_degrees)
            direction = origin + QPointF(math.cos(angle) * 48, math.sin(angle) * 48)
            points = {"origin": origin, "direction": direction, "endpoint": endpoint}
            if settings.spawn_shape == "line":
                points["shape"] = self.canvas_to_widget(settings.line_end_x, settings.line_end_y)
            elif settings.spawn_shape == "circle":
                points["shape"] = self.canvas_to_widget(settings.origin_x + settings.radius, settings.origin_y)
            elif settings.spawn_shape == "box":
                points["shape"] = self.canvas_to_widget(
                    settings.origin_x + settings.box_width / 2,
                    settings.origin_y + settings.box_height / 2,
                )
            return points
        return {}

    def _paint_effect_guide(self, painter: QPainter) -> None:
        points = self._guide_points()
        if not points:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        guide_pen = QPen(QColor("#4dabf7"), 2, Qt.PenStyle.DashLine)
        painter.setPen(guide_pen)
        settings = self.effect_guide_settings
        if isinstance(settings, EffectCompositionLayer):
            painter.drawLine(points["start"], points["end"])
            self._paint_ghosts(painter, settings.resource_composition_id, points["start"], points["end"])
        else:
            origin, endpoint = points["origin"], points["endpoint"]
            painter.drawLine(origin, endpoint)
            painter.drawLine(origin, points["direction"])
            spread = math.radians(settings.direction_spread_degrees)
            direction = math.radians(settings.direction_degrees)
            length = min(80.0, max(36.0, math.hypot(endpoint.x()-origin.x(), endpoint.y()-origin.y())))
            for angle in (direction - spread, direction + spread):
                painter.drawLine(origin, origin + QPointF(math.cos(angle)*length, math.sin(angle)*length))
            if settings.spawn_shape == "line":
                painter.drawLine(origin, points["shape"])
            elif settings.spawn_shape == "circle":
                radius = max(0.0, settings.radius * self.zoom)
                painter.drawEllipse(origin, radius, radius)
            elif settings.spawn_shape == "box":
                painter.drawRect(QRectF(
                    origin.x()-settings.box_width*self.zoom/2,
                    origin.y()-settings.box_height*self.zoom/2,
                    settings.box_width*self.zoom, settings.box_height*self.zoom,
                ))
            if settings.resource_type == "resource_composition":
                self._paint_ghosts(painter, settings.resource_id, origin, endpoint)
        for name, point in points.items():
            painter.setPen(QPen(QColor("#ffd43b") if name == self._guide_hover else QColor("#51cf66"), 2))
            painter.setBrush(QColor("#20242b"))
            painter.drawEllipse(point, 6, 6)

    def _paint_ghosts(self, painter: QPainter, composition_id: str, start: QPointF, end: QPointF) -> None:
        if self.project is None:
            return
        composition = next((item for item in self.project.resource_compositions if item.id == composition_id), None)
        if composition is None:
            return
        key = (composition.id, composition.revision)
        pixmaps = self._ghost_cache.get(key)
        if pixmaps is None:
            frames = render_composition_frames(self.project, composition)
            indexes = sorted({0, len(frames)//2, len(frames)-1})
            pixmaps = []
            for index in indexes:
                pixels = np.ascontiguousarray(frames[index])
                image = QImage(pixels.data, composition.width, composition.height, pixels.strides[0], QImage.Format.Format_RGBA8888).copy()
                pixmaps.append(QPixmap.fromImage(image))
            self._ghost_cache[key] = pixmaps
        painter.save(); painter.setOpacity(0.28)
        for index, pixmap in enumerate(pixmaps):
            amount = index / max(1, len(pixmaps)-1)
            point = start + (end-start)*amount
            target = QRectF(
                point.x()-composition.pivot_x*self.zoom,
                point.y()-composition.pivot_y*self.zoom,
                composition.width*self.zoom,
                composition.height*self.zoom,
            )
            painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        painter.restore()

    def _hit_guide_handle(self, position: QPointF) -> str | None:
        candidates = self._guide_points()
        if not candidates:
            return None
        return next((name for name, point in candidates.items() if math.hypot(point.x()-position.x(), point.y()-position.y()) <= 10), None)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True; self._pan_last = event.position(); self.setCursor(Qt.CursorShape.ClosedHandCursor); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton and self.show_effect_guides and self.effect_guide_id:
            handle = self._hit_guide_handle(event.position())
            if handle:
                self._guide_handle = handle
                self._guide_before = deepcopy(self.effect_guide_settings)
                self._guide_last_canvas_point = None
                self.setFocus()
                event.accept()
                return
        if event.button() == Qt.MouseButton.LeftButton and self.gizmo_generator_id and self.gizmo_settings is not None and not self.gizmo_locked:
            self._gizmo_drag = True; self._gizmo_before = deepcopy(self.gizmo_settings); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton:
            layer_index = self._layer_at(event.position())
            if layer_index is not None:
                self.layer_selected.emit(layer_index); event.accept(); return
        super().mousePressEvent(event)

    def _layer_at(self, widget_point: QPointF) -> int | None:
        if self.project is None or not (0 <= self.frame_index < len(self.project.frames)):
            return None
        point = self.widget_to_canvas(widget_point); x, y = int(math.floor(point.x())), int(math.floor(point.y()))
        if not (0 <= x < self.project.width and 0 <= y < self.project.height):
            return None
        frame = self.project.frames[self.frame_index]
        for index in range(len(self.project.layers)-1, -1, -1):
            layer = self.project.layers[index]
            pixels = frame.layer_pixels.get(layer.id)
            if layer.visible and pixels is not None and pixels[y, x, 3] > 0:
                return index
        return None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            delta=event.position()-self._pan_last;self._pan_last=event.position();self.pan_offset+=delta;self.update();event.accept();return
        if self._guide_handle:
            point = self.widget_to_canvas(event.position())
            integer_point = (round(point.x()), round(point.y()))
            if integer_point == self._guide_last_canvas_point:
                event.accept(); return
            self._guide_last_canvas_point = integer_point
            self._move_effect_guide(point, event.modifiers())
            self.effect_guide_changed.emit(self.effect_guide_id, deepcopy(self.effect_guide_settings), False)
            self.update(); event.accept(); return
        if self.effect_guide_id:
            hover = self._hit_guide_handle(event.position())
            if hover != self._guide_hover:
                self._guide_hover = hover
                self.setCursor(Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor)
                self.update()
        if not self._gizmo_drag: super().mouseMoveEvent(event); return
        point = self.widget_to_canvas(event.position()); s = self.gizmo_settings
        if self.gizmo_mode == "move":
            name_x = "offset_x_end" if self.gizmo_edit_end else "offset_x_start"; name_y = "offset_y_end" if self.gizmo_edit_end else "offset_y_start"
            setattr(s, name_x, round(point.x() - s.origin_x)); setattr(s, name_y, round(point.y() - s.origin_y))
        elif self.gizmo_mode == "distribution":
            if getattr(s, "distribution", "Point") == "Line": s.line_end_x, s.line_end_y = round(point.x()), round(point.y())
            elif getattr(s, "distribution", "Point") == "Circle": s.radius = max(0, round(math.hypot(point.x()-s.origin_x, point.y()-s.origin_y)))
            else: s.origin_x, s.origin_y = round(point.x()), round(point.y())
        elif self.gizmo_mode == "rotate":
            x, y = self._gizmo_center(); angle = math.degrees(math.atan2(point.y()-y, point.x()-x))
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: angle = round(angle / 15) * 15
            setattr(s, "rotation_end" if self.gizmo_edit_end else "rotation_start", angle)
        elif self.gizmo_mode == "scale":
            x, y = self._gizmo_center(); value = max(0.01, math.hypot(point.x()-x, point.y()-y) / 34.0)
            setattr(s, "scale_x_end" if self.gizmo_edit_end else "scale_x_start", value); setattr(s, "scale_y_end" if self.gizmo_edit_end else "scale_y_start", value)
        self.gizmo_changed.emit(self.gizmo_generator_id, deepcopy(s)); self.update(); event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._panning and event.button()==Qt.MouseButton.MiddleButton:
            self._panning=False;self.setCursor(Qt.CursorShape.ArrowCursor);event.accept();return
        if self._guide_handle:
            self._guide_handle = None
            self._guide_last_canvas_point = None
            self.effect_guide_changed.emit(self.effect_guide_id, deepcopy(self.effect_guide_settings), True)
            event.accept(); return
        if self._gizmo_drag: self._gizmo_drag = False; event.accept(); return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self._guide_handle and self._guide_before is not None:
            before = deepcopy(self._guide_before)
            self.effect_guide_settings = before
            self._guide_handle = None
            self._guide_last_canvas_point = None
            self.effect_guide_cancelled.emit(self.effect_guide_id, before)
            self.update(); event.accept(); return
        if event.key() == Qt.Key.Key_Escape and self._gizmo_drag and self._gizmo_before is not None:
            self.gizmo_settings = self._gizmo_before; self._gizmo_drag = False
            self.gizmo_changed.emit(self.gizmo_generator_id, deepcopy(self.gizmo_settings)); self.update(); event.accept(); return
        super().keyPressEvent(event)

    def _move_effect_guide(self, point: QPointF, modifiers) -> None:
        settings = self.effect_guide_settings
        x, y = round(point.x()), round(point.y())
        if isinstance(settings, EffectCompositionLayer):
            if self._guide_handle == "start": settings.start_x, settings.start_y = x, y
            elif self._guide_handle == "end": settings.end_x, settings.end_y = x, y
            return
        if not isinstance(settings, ParticleEmitterSettings):
            return
        if self._guide_handle == "origin":
            dx, dy = x-settings.origin_x, y-settings.origin_y
            settings.origin_x, settings.origin_y = x, y
            if settings.spawn_shape == "line": settings.line_end_x += dx; settings.line_end_y += dy
        elif self._guide_handle == "direction":
            angle = math.degrees(math.atan2(y-settings.origin_y, x-settings.origin_x))
            if modifiers & Qt.KeyboardModifier.ShiftModifier: angle = round(angle/15)*15
            settings.direction_degrees = angle
        elif self._guide_handle == "endpoint":
            dx, dy = x-settings.origin_x, y-settings.origin_y
            angle = math.degrees(math.atan2(dy, dx))
            if modifiers & Qt.KeyboardModifier.ShiftModifier: angle = round(angle/15)*15
            settings.direction_degrees = angle
            lifetime = max(1.0, (settings.lifetime_min+settings.lifetime_max)/2.0-1.0)
            center = math.hypot(dx, dy)/lifetime
            half = max(0.0, (settings.speed_max-settings.speed_min)/2.0)
            settings.speed_min = max(0.0, center-half); settings.speed_max = center+half
        elif self._guide_handle == "shape":
            if settings.spawn_shape == "line": settings.line_end_x, settings.line_end_y = x, y
            elif settings.spawn_shape == "circle": settings.radius = max(0.0, math.hypot(x-settings.origin_x, y-settings.origin_y))
            elif settings.spawn_shape == "box":
                settings.box_width = abs(x-settings.origin_x)*2; settings.box_height = abs(y-settings.origin_y)*2

    def _compose_display_frame(self) -> np.ndarray:
        assert self.project is not None
        if self.preview_frames is None:
            return self.project.compose_frame(self.frame_index)
        if not (0 <= self.frame_index < len(self.preview_frames)):
            return self.project.compose_frame(
                min(self.frame_index, len(self.project.frames) - 1)
            )
        output = np.zeros((self.project.height, self.project.width, 4), dtype=np.float32)
        preview = self.preview_frames[self.frame_index]
        if preview.shape[:2] != output.shape[:2]:
            return self.project.compose_frame(
                min(self.frame_index, len(self.project.frames) - 1)
            )
        project_frame = (
            self.project.frames[self.frame_index]
            if self.frame_index < len(self.project.frames)
            else None
        )
        replacement_seen = False
        for layer in self.project.layers:
            if not layer.visible:
                continue
            if layer.id == self.preview_layer_id:
                source = preview
                replacement_seen = True
            elif project_frame is not None:
                source = project_frame.layer_pixels.get(layer.id)
            else:
                source = None
            if source is not None:
                self._composite(output, source, layer.opacity)
        if not replacement_seen:
            self._composite(output, preview, 1.0)
        return np.clip(output * 255.0, 0, 255).astype(np.uint8)

    @staticmethod
    def _composite(output: np.ndarray, source: np.ndarray, opacity: float) -> None:
        if source.shape[:2] != output.shape[:2]:
            return
        src = source.astype(np.float32) / 255.0
        src_alpha = src[..., 3:4] * max(0.0, min(1.0, opacity))
        dst_alpha = output[..., 3:4]
        combined_alpha = src_alpha + dst_alpha * (1.0 - src_alpha)
        safe_alpha = np.where(combined_alpha == 0, 1.0, combined_alpha)
        output[..., :3] = (
            src[..., :3] * src_alpha
            + output[..., :3] * dst_alpha * (1.0 - src_alpha)
        ) / safe_alpha
        output[..., 3:4] = combined_alpha
    gizmo_changed = Signal(str, object)
    effect_guide_changed = Signal(str, object, bool)
    effect_guide_cancelled = Signal(str, object)
    layer_selected = Signal(int)
