from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QImage, QWheelEvent
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.source_asset import SourceAsset
from app.ui.resource_editor_v2.asset_inspector_widget import AssetPreviewCanvas
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget


APP = QApplication.instance() or QApplication([])


def _asset(size: int = 28) -> SourceAsset:
    pixels = np.zeros((size, size, 4), dtype=np.uint8)
    pixels[2:-1, 2:-1] = [220, 70, 30, 255]
    return SourceAsset("preview", pixels)


def _canvas(size: int = 28) -> tuple[SourceAsset, AssetPreviewCanvas]:
    asset = _asset(size)
    canvas = AssetPreviewCanvas()
    canvas.resize(520, 420)
    canvas.set_asset(asset)
    canvas.show()
    APP.processEvents()
    return asset, canvas


@pytest.mark.parametrize("size,expected", [(28, 14.0), (29, 14.5)])
def test_asset_preview_default_pivot_marker_is_geometric_center(size, expected):
    asset, canvas = _canvas(size)
    assert (asset.pivot_x, asset.pivot_y) == (expected, expected)
    assert canvas.pivot_marker_position() == canvas.image_rect().center()
    canvas.close()


def test_asset_preview_pivot_change_moves_overlay_without_changing_pixels():
    asset, canvas = _canvas()
    original_pixels = asset.pixels.copy()
    before = canvas.pivot_marker_position()
    asset.pivot_x, asset.pivot_y = 5.0, 9.0
    canvas.set_asset(asset)
    APP.processEvents()
    assert canvas.pivot_marker_position() != before
    assert canvas.pivot_marker_position() == canvas.source_to_widget(QPointF(5, 9))
    assert np.array_equal(asset.pixels, original_pixels)
    canvas.close()


@pytest.mark.parametrize("size,expected", [(28, 14.0), (29, 14.5)])
def test_center_asset_pivot_button_updates_preview_immediately(size, expected):
    project = Project.create_default(width=size, height=size, frame_count=1)
    asset = _asset(size)
    asset.pivot_x, asset.pivot_y = 2.0, 3.0
    project.source_assets.append(asset)
    editor = ResourceEditorWidget(QSettings())
    editor.resize(1000, 700)
    editor.refresh(project, ("source_asset", asset.id))
    editor.show()
    APP.processEvents()
    editor.asset_inspector.center_button.click()
    APP.processEvents()
    assert (asset.pivot_x, asset.pivot_y) == (expected, expected)
    assert editor.asset_canvas.pivot_marker_position() == editor.asset_canvas.image_rect().center()
    editor.close()


def test_fit_keeps_full_asset_inside_safe_preview_margin():
    _, canvas = _canvas(28)
    rect = canvas.image_rect()
    assert rect.left() >= canvas.FIT_MARGIN and rect.top() >= canvas.FIT_MARGIN
    assert rect.right() <= canvas.width() - canvas.FIT_MARGIN
    assert rect.bottom() <= canvas.height() - canvas.FIT_MARGIN
    canvas.close()


def test_wheel_zoom_is_cursor_anchored_clamped_and_reversible():
    _, canvas = _canvas()
    cursor = QPointF(173, 129)
    source_before = (cursor - canvas.image_rect().topLeft()) / canvas.zoom

    def wheel(delta):
        event = QWheelEvent(cursor, canvas.mapToGlobal(cursor.toPoint()), QPoint(), QPoint(0, delta),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.ScrollUpdate, False)
        APP.notify(canvas, event)

    original_zoom = canvas.zoom
    wheel(120)
    source_after = (cursor - canvas.image_rect().topLeft()) / canvas.zoom
    assert canvas.zoom == min(canvas.MAX_ZOOM, original_zoom * 2)
    assert source_after == source_before
    for _ in range(20): wheel(-120)
    assert canvas.zoom == canvas.MIN_ZOOM
    canvas.close()


def test_middle_pan_moves_image_and_pivot_together_without_model_mutation():
    asset, canvas = _canvas()
    before_rect = canvas.image_rect()
    before_marker = canvas.pivot_marker_position()
    before_pivot = (asset.pivot_x, asset.pivot_y)
    start = QPointF(200, 170)

    class Event:
        def __init__(self, position, button): self._position, self._button = position, button
        def position(self): return self._position
        def button(self): return self._button
        def accept(self): pass

    canvas.mousePressEvent(Event(start, Qt.MouseButton.MiddleButton))
    canvas.mouseMoveEvent(Event(start + QPointF(31, -18), Qt.MouseButton.NoButton))
    canvas.mouseReleaseEvent(Event(start + QPointF(31, -18), Qt.MouseButton.MiddleButton))
    delta = QPointF(31, -18)
    assert canvas.image_rect().topLeft() == before_rect.topLeft() + delta
    assert canvas.pivot_marker_position() == before_marker + delta
    assert (asset.pivot_x, asset.pivot_y) == before_pivot
    canvas.close()


def test_fit_and_actual_buttons_reset_navigation_only():
    project = Project.create_default(width=28, height=28, frame_count=1)
    asset = _asset(); project.source_assets.append(asset)
    editor = ResourceEditorWidget(QSettings()); editor.resize(1000, 700)
    editor.refresh(project, ("source_asset", asset.id)); editor.show(); APP.processEvents()
    editor.asset_canvas.zoom = 7; editor.asset_canvas.pan = QPointF(50, -20)
    editor.asset_actual.click()
    assert editor.asset_canvas.zoom == 1 and editor.asset_canvas.pan == QPointF()
    editor.asset_fit.click()
    assert editor.asset_canvas.fit_mode and editor.asset_canvas.pan == QPointF()
    assert editor.asset_canvas.zoom == editor.asset_canvas._fit_zoom()
    editor.close()


def test_asset_preview_pivot_tracks_zoom_and_pan():
    asset, canvas = _canvas()
    asset.pivot_x, asset.pivot_y = 7, 11
    canvas.zoom = 8; canvas.pan = QPointF(23, -17)
    assert canvas.pivot_marker_position() == canvas.source_to_widget(QPointF(7, 11))
    canvas.close()


def test_asset_preview_uses_nearest_neighbor():
    pixels = np.array([[[255, 0, 0, 255], [0, 0, 255, 255]]], dtype=np.uint8)
    canvas = AssetPreviewCanvas(); canvas.resize(320, 260); canvas.set_asset(SourceAsset("two", pixels)); canvas.show(); APP.processEvents()
    target = QImage(canvas.size(), QImage.Format.Format_RGBA8888)
    canvas.render(target)
    rect = canvas.image_rect(); y = round(rect.center().y())
    left = target.pixelColor(round(rect.left() + rect.width() * .25), y)
    right = target.pixelColor(round(rect.left() + rect.width() * .75), y)
    assert (left.red(), left.green(), left.blue()) == (255, 0, 0)
    assert (right.red(), right.green(), right.blue()) == (0, 0, 255)
    canvas.close()
