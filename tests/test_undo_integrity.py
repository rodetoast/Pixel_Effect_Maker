from __future__ import annotations

import os
from pathlib import Path

import pytest
import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.resource_composition import ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def _window(tmp_path: Path):
    settings = QSettings(str(tmp_path / "undo-integrity.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", "en")
    window = MainWindow(ShortcutSettingsService(settings))
    composition = ResourceComposition("Undo Source", 64, 64, 12, 8, True)
    window.project.resource_compositions.append(composition)
    first = window.create_composition_layer_from_resource(composition.id)
    second = window.create_composition_layer_from_resource(composition.id)
    first.name = second.name = "Spark"
    return window, first, second


@pytest.mark.parametrize(
    ("property_name", "new_value"),
    (("start_x", 151), ("start_y", 252), ("end_x", 353), ("end_y", 454)),
)
def test_effect_path_inspector_undo_uses_stable_id_and_exact_property_sentinels(tmp_path, property_name, new_value):
    window, layer, duplicate_name = _window(tmp_path)
    layer.start_x, layer.start_y, layer.end_x, layer.end_y = 101, 202, 303, 404
    duplicate_name.start_x, duplicate_name.start_y, duplicate_name.end_x, duplicate_name.end_y = 11, 22, 33, 44
    window.select_resource_layer(layer.id);APP.processEvents()
    before_count = window.application_undo_stack.count()

    getattr(window.composition_layer_properties, property_name).setValue(new_value);APP.processEvents()

    assert window.application_undo_stack.count() == before_count + 1
    assert (layer.start_x, layer.start_y, layer.end_x, layer.end_y) == tuple(
        new_value if name == property_name else value
        for name, value in (("start_x", 101), ("start_y", 202), ("end_x", 303), ("end_y", 404))
    )
    window.select_resource_layer(duplicate_name.id);window.application_undo_stack.undo();APP.processEvents()
    assert (layer.start_x, layer.start_y, layer.end_x, layer.end_y) == (101, 202, 303, 404)
    assert (duplicate_name.start_x, duplicate_name.start_y, duplicate_name.end_x, duplicate_name.end_y) == (11, 22, 33, 44)
    window.application_undo_stack.redo();APP.processEvents()
    assert getattr(layer, property_name) == new_value
    assert (duplicate_name.start_x, duplicate_name.start_y, duplicate_name.end_x, duplicate_name.end_y) == (11, 22, 33, 44)
    window.dirty = False;window.close()


@pytest.mark.parametrize("handle", ("start", "end"))
def test_effect_path_gizmo_is_one_stable_undo_transaction(tmp_path, handle):
    window, layer, other = _window(tmp_path)
    layer.start_x, layer.start_y, layer.end_x, layer.end_y = 11, 22, 43, 34
    other.start_x, other.start_y, other.end_x, other.end_y = 5, 6, 7, 8
    window.select_resource_layer(layer.id);window.canvas.resize(700, 500);window.show();APP.processEvents()
    original = (layer.start_x, layer.start_y, layer.end_x, layer.end_y)
    point = window.canvas._guide_points()[handle].toPoint();before_count = window.application_undo_stack.count()

    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=point)
    QTest.mouseMove(window.canvas, point + QPoint(24, 16))
    # A refresh must not replace the press-time identity or settings.
    window.canvas.set_effect_guide(other.id, "composition_layer", other.single_settings)
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=point + QPoint(24, 16));APP.processEvents()

    changed = (layer.start_x, layer.start_y, layer.end_x, layer.end_y)
    assert changed != original and window.application_undo_stack.count() == before_count + 1
    if handle == "start":assert changed[2:] == original[2:]
    else:assert changed[:2] == original[:2]
    assert (other.start_x, other.start_y, other.end_x, other.end_y) == (5, 6, 7, 8)
    window.select_resource_layer(other.id);window.application_undo_stack.undo();APP.processEvents()
    assert (layer.start_x, layer.start_y, layer.end_x, layer.end_y) == original
    assert (other.start_x, other.start_y, other.end_x, other.end_y) == (5, 6, 7, 8)
    window.application_undo_stack.redo();APP.processEvents()
    assert (layer.start_x, layer.start_y, layer.end_x, layer.end_y) == changed
    window.dirty = False;window.close()


def test_effect_path_gizmo_noop_creates_no_undo_command(tmp_path):
    window, layer, _ = _window(tmp_path);window.select_resource_layer(layer.id);window.canvas.resize(700,500);window.show();APP.processEvents()
    point=window.canvas._guide_points()["start"].toPoint();before_count=window.application_undo_stack.count()
    QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=point);QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=point);APP.processEvents()
    assert window.application_undo_stack.count()==before_count
    window.dirty=False;window.close()


def test_new_effect_guide_gesture_replaces_an_interrupted_stale_snapshot(tmp_path):
    window, first, second = _window(tmp_path)
    first.start_x, first.start_y, first.end_x, first.end_y = 10, 20, 30, 40
    second.start_x, second.start_y, second.end_x, second.end_y = 101, 202, 303, 404
    interrupted = first.as_composition_layer();interrupted.start_x = 77
    window._effect_guide_changed(first.id, interrupted, False)

    window._effect_guide_started(second.id)
    changed = second.as_composition_layer();changed.start_x = 151
    window._effect_guide_changed(second.id, changed, True);APP.processEvents()
    window.application_undo_stack.undo();APP.processEvents()

    # The interrupted live preview may finish independently; it must never be
    # reused as the second layer's Undo snapshot.
    assert first.id != second.id
    assert (second.start_x, second.start_y, second.end_x, second.end_y) == (101, 202, 303, 404)
    window.dirty = False;window.close()


def test_resource_gizmo_finalizes_against_press_time_layer_after_selection_change(tmp_path):
    window, _, _ = _window(tmp_path);editor=window.resource_editor
    pixels=np.full((2,2,4),255,dtype=np.uint8);asset=SourceAsset("Pixel",pixels);window.project.source_assets.append(asset);editor.refresh(window.project)
    editor._last_asset=("source_asset",asset.id);editor.create_composition("Gizmo Stable ID",16,16,12,8,True)
    first=editor.add_selected_asset();first_id=first.id;second=editor.add_selected_asset();first=next(item for item in editor.composition.layers if item.id==first_id);editor.controller.select_layer(first.id)
    before_count=window.application_undo_stack.count()

    editor._gizmo_change("position",[11.0,22.0],False)
    editor.controller.select_layer(second.id)
    editor._gizmo_change("position",[33.0,44.0],True)

    assert window.application_undo_stack.count()==before_count+1
    assert first.tracks["position"].evaluate(0)==[33.0,44.0]
    assert "position" not in second.tracks
    window.application_undo_stack.undo()
    assert "position" not in first.tracks and "position" not in second.tracks
    window.application_undo_stack.redo()
    assert first.tracks["position"].evaluate(0)==[33.0,44.0] and "position" not in second.tracks
    window.dirty=False;window.close()
