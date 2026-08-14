from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from copy import deepcopy
import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget

APP = QApplication.instance() or QApplication([])


def _project():
    project = Project.create_default(width=32, height=32, frame_count=2)
    asset = SourceAsset("sprite", np.ones((2, 2, 4), dtype=np.uint8) * 255)
    composition = ResourceComposition("R", 32, 32, 12, 2)
    composition.layers = [CompositionLayer(name, "source_asset", asset.id, 0, 1) for name in ("A", "B", "C")]
    composition.repair_hierarchy();project.source_assets.append(asset);project.resource_compositions.append(composition)
    return project, composition


def _resource_editor(tmp_path):
    project, composition = _project();editor = ResourceEditorWidget(QSettings(str(tmp_path / "multi.ini"), QSettings.Format.IniFormat));stack = QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id, composition.layers[0].id)
    return editor, stack, composition


def _effect_window(tmp_path):
    project, composition = _project();settings = QSettings(str(tmp_path / "effect.ini"), QSettings.Format.IniFormat);settings.setValue("ui/language", "en");window = MainWindow(ShortcutSettingsService(settings), initial_project=project)
    layers = [window.create_resource_layer_from_resource(composition.id) for _ in range(3)];window.application_undo_stack.clear();return window, layers


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


def test_resource_batch_local_edit_is_one_exact_undo(tmp_path):
    editor, stack, composition = _resource_editor(tmp_path);a, b = composition.layers[:2]
    a.add_property("position").default_value = [10, 1];b.add_property("position").default_value = [20, 2]
    editor.select_layer_with_modifiers(a.id);editor.select_layer_with_modifiers(b.id, Qt.KeyboardModifier.ControlModifier);stack.clear()
    assert editor._batch_property_value("position", 0, 50) and stack.count() == 1
    assert a.value("position", 0) == [50, 1] and b.value("position", 0) == [50, 2]
    selected = editor.layer_selection.snapshot();stack.undo();assert a.value("position", 0) == [10, 1] and b.value("position", 0) == [20, 2]
    stack.redo();assert a.value("position", 0) == [50, 1] and b.value("position", 0) == [50, 2] and editor.layer_selection.snapshot() == selected
    editor.close()


def test_resource_multi_gizmo_gesture_is_one_undo_and_noop_is_zero(tmp_path):
    editor, stack, composition = _resource_editor(tmp_path);a, b = composition.layers[:2]
    editor.select_layer_with_modifiers(a.id);editor.select_layer_with_modifiers(b.id, Qt.KeyboardModifier.ControlModifier);APP.processEvents();stack.clear()
    revision=composition.revision;editor._multi_gizmo_change("position", (0, 0), False);editor._multi_gizmo_change("position", (0, 0), True);assert stack.count() == 0 and composition.revision==revision
    editor._multi_gizmo_change("position", (12, -4), False);editor._multi_gizmo_change("position", (12, -4), True)
    assert stack.count() == 1 and a.value("position", 0) == [12, -4] and b.value("position", 0) == [12, -4]
    stack.undo();assert a.value("position", 0) == [0, 0] and b.value("position", 0) == [0, 0]
    editor.close()


def test_effect_batch_local_edit_and_canvas_world_move_are_single_undo(tmp_path):
    window, layers = _effect_window(tmp_path);a, b = layers[:2]
    a.layer_transform.position_x = 10;b.layer_transform.position_x = 20
    window.select_effect_layers_with_modifiers(a.id);window.select_effect_layers_with_modifiers(b.id, Qt.KeyboardModifier.ControlModifier);window.application_undo_stack.clear()
    window.update_selected_resource_layer_transform_property("position_x", 50)
    assert a.layer_transform.position_x == 50 and b.layer_transform.position_x == 50 and window.application_undo_stack.count() == 1
    window.application_undo_stack.undo();assert a.layer_transform.position_x == 10 and b.layer_transform.position_x == 20
    window.application_undo_stack.clear();surface = deepcopy(a.surface_transform)
    window._effect_multi_gizmo_changed({"operation":"move","value":(7,-3)},False);window._effect_multi_gizmo_changed({"operation":"final","value":None},True)
    assert window.application_undo_stack.count() == 1 and a.layer_transform.position_x == 17 and b.layer_transform.position_x == 27 and a.surface_transform == surface
    window.application_undo_stack.undo();assert a.layer_transform.position_x == 10 and b.layer_transform.position_x == 20
    _close(window)
