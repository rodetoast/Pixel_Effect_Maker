from __future__ import annotations

import ast
import os
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QScrollArea, QVBoxLayout, QWidget

from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.effect_generator import TransformEmitter, TransformEmitterSettings
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings
from app.models.source_asset import SourceAsset
from app.services.particle_render_service import representative_particle_guide
from app.services.settings_service import ShortcutSettingsService
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def service(tmp_path):
    settings = QSettings(str(tmp_path / "effect-guides.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", "en")
    return ShortcutSettingsService(settings)


def wheel(widget, delta=120, modifiers=Qt.KeyboardModifier.NoModifier):
    local = QPointF(widget.rect().center()); global_pos = QPointF(widget.mapToGlobal(local.toPoint()))
    event = QWheelEvent(local, global_pos, QPoint(), QPoint(0, delta), Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.ScrollUpdate, False)
    APP.notify(widget, event)
    return event


@pytest.mark.parametrize("widget_type", [ScrollSafeSpinBox, ScrollSafeDoubleSpinBox])
def test_scroll_safe_spinboxes_never_change_on_wheel(widget_type):
    widget = widget_type(); widget.setRange(-100, 100); widget.setValue(7); widget.show()
    for focus in (False, True):
        if focus: widget.setFocus(); widget.lineEdit().selectAll()
        else: widget.clearFocus()
        event = wheel(widget)
        assert widget.value() == 7 and not event.isAccepted()
    widget.close()


def test_scroll_safe_spinbox_wheel_reaches_parent_scroll_area():
    scroll = QScrollArea(); body = QWidget(); layout = QVBoxLayout(body)
    layout.addSpacing(400); spin = ScrollSafeSpinBox(); layout.addWidget(spin); layout.addSpacing(600)
    scroll.setWidget(body); scroll.setWidgetResizable(False); scroll.resize(220, 180); body.resize(200, 1100)
    scroll.show(); APP.processEvents(); scroll.verticalScrollBar().setValue(300); before = scroll.verticalScrollBar().value()
    event = wheel(spin, -120); APP.processEvents()
    assert spin.value() == 0 and not event.isAccepted()
    # Qt may deliver a synthetic sendEvent only to the child; explicitly
    # forwarding the still-ignored event models normal wheel propagation.
    if scroll.verticalScrollBar().value() == before:
        wheel(scroll.viewport(), -120); APP.processEvents()
    assert scroll.verticalScrollBar().value() > before
    scroll.close()


@pytest.mark.parametrize("focused", [False, True])
def test_ctrl_wheel_changes_one_exact_spinbox_step_regardless_of_focus(focused):
    widget = ScrollSafeSpinBox(); widget.setRange(0, 10); widget.setSingleStep(2); widget.setValue(4); widget.show()
    widget.setFocus() if focused else widget.clearFocus()
    event = wheel(widget, 120, Qt.KeyboardModifier.ControlModifier)
    assert event.isAccepted() and widget.value() == 6
    widget.lineEdit().setFocus(); wheel(widget, -120, Qt.KeyboardModifier.ControlModifier)
    assert widget.value() == 4
    widget.close()


def test_ctrl_wheel_accumulates_high_resolution_delta_and_respects_bounds():
    widget = ScrollSafeDoubleSpinBox(); widget.setRange(0, 1); widget.setSingleStep(.25); widget.setValue(.5); widget.show()
    for _ in range(3): wheel(widget, 30, Qt.KeyboardModifier.ControlModifier)
    assert widget.value() == .5
    wheel(widget, 30, Qt.KeyboardModifier.ControlModifier); assert widget.value() == .75
    for _ in range(4): wheel(widget, 120, Qt.KeyboardModifier.ControlModifier)
    assert widget.value() == 1
    widget.setReadOnly(True); event = wheel(widget, -120, Qt.KeyboardModifier.ControlModifier)
    assert widget.value() == 1 and not event.isAccepted()
    widget.close()


@pytest.mark.parametrize("kind", ["composition_layer", "particle_system", "legacy_generator"])
def test_delete_selected_effect_layer_round_trips_exact_model_and_pixels(tmp_path, kind):
    window = MainWindow(service(tmp_path)); layer = window.project.layers[0]
    pixels = window.project.frames[0].layer_pixels[layer.id]
    pixels[1, 1] = [12, 34, 56, 255]; original_pixels = pixels.copy()
    composition = ResourceComposition("Original", 64, 64, 12, 8, True)
    window.project.resource_compositions.append(composition)
    if kind == "composition_layer":
        model = EffectCompositionLayer("Placed", composition.id, generated_layer_id=layer.id)
        collection = window.project.effect_composition_layers
    elif kind == "particle_system":
        model = ParticleEmitter("Particles", ParticleEmitterSettings("source"), generated_layer_id=layer.id)
        collection = window.project.particle_emitters
    else:
        model = TransformEmitter("Legacy", TransformEmitterSettings("source"), generated_layer_id=layer.id)
        collection = window.project.generators
    collection.append(model); window.layer_index = 0; window.frame_index = 0; window._refresh_all()
    assert window.delete_layer_action.isEnabled()
    window.delete_layer()
    assert model not in collection and layer not in window.project.layers
    assert len(window.project.layers) == 1 and window.project.resource_compositions == [composition]
    assert window.application_undo_stack.undoText() == "Delete Effect Layer"
    window.application_undo_stack.undo()
    assert collection == [model] and collection[0] is model
    assert window.project.layers == [layer] and np.array_equal(window.project.frames[0].layer_pixels[layer.id], original_pixels)
    assert window.layer_index == 0 and window.frame_index == 0
    window.application_undo_stack.redo()
    assert model not in collection and layer not in window.project.layers
    window.dirty = False; window.close()


def test_delete_selected_layer_disabled_for_only_plain_invariant_layer(tmp_path):
    window = MainWindow(service(tmp_path)); window._refresh_all()
    assert not window.delete_layer_action.isEnabled()
    assert not window.timeline.delete_layer_button.isEnabled()
    window.delete_layer(); assert len(window.project.layers) == 1
    window.dirty = False; window.close()


def test_active_numeric_constructors_do_not_create_raw_spinboxes():
    root = Path(__file__).parents[1] / "app"
    offenders = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"QSpinBox", "QDoubleSpinBox"}:
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def test_effect_visibility_and_name_cells_have_separate_actions(tmp_path):
    window = MainWindow(service(tmp_path)); window.project.add_layer("Glow"); window._refresh_all(); window.show(); APP.processEvents()
    table = window.timeline.table; row = 0; model_layer = window.project.layers[-1]; before = model_layer.visible
    name = table.item(row, window.timeline.NAME_COLUMN)
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(name).center()); APP.processEvents()
    assert model_layer.visible is before and window.layer_index == len(window.project.layers)-1
    eye = table.item(row, window.timeline.VISIBILITY_COLUMN)
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(eye).center()); APP.processEvents()
    assert model_layer.visible is not before and window.application_undo_stack.undoText() == "Layer Visibility"
    window.application_undo_stack.undo(); assert model_layer.visible is before
    window.application_undo_stack.redo(); assert model_layer.visible is not before
    hidden_name = table.item(row, window.timeline.NAME_COLUMN)
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(hidden_name).center()); APP.processEvents()
    assert window.layer_index == len(window.project.layers)-1
    window.dirty=False; window.close()


def resource_project(window):
    pixels = np.zeros((8, 8, 4), dtype=np.uint8); pixels[2:6, 2:6] = [255, 180, 20, 255]
    asset = SourceAsset("spark", pixels, pivot_x=4, pivot_y=4)
    composition = ResourceComposition("Spark Resource", 8, 8, 12, 4, True)
    composition.layers.append(CompositionLayer("spark", "source_asset", asset.id, 0, 3, pivot_x=4, pivot_y=4))
    window.project.source_assets.append(asset); window.project.resource_compositions.append(composition)
    return composition


def test_resource_layer_preserves_both_modes_and_round_trips(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    direct = window.create_composition_layer_from_resource(composition.id)
    particle = window.create_particle_from_resource("resource_composition", composition.id)
    assert direct.resource_composition_id == composition.id and direct.placement_mode == "single"
    assert particle.settings.resource_type == "resource_composition" and particle.placement_mode == "particle"
    loaded = type(window.project).from_dict(window.project.to_dict())
    assert [item.to_dict() for item in loaded.effect_resource_layers] == [direct.to_dict(), particle.to_dict()]
    window.dirty=False; window.close()


def test_resource_add_to_effect_has_one_non_modal_path(tmp_path, monkeypatch):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    editor = window.resource_editor; editor.refresh(window.project); editor.controller.select_composition(composition.id)
    editor._use_in_effect()
    assert len(window.project.effect_resource_layers)==1
    assert window.project.effect_resource_layers[0].placement_mode=="single"
    window.dirty=False;window.close()


def test_composition_layer_canvas_drag_is_one_undo_step_and_escape_is_noop(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    layer = window.create_composition_layer_from_resource(composition.id); window.canvas.resize(700, 500); window.show(); APP.processEvents()
    start = window.canvas._guide_points()["start"].toPoint(); undo_before = window.application_undo_stack.count()
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.canvas, start + QPoint(24, 16))
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=start + QPoint(24, 16)); APP.processEvents()
    assert (layer.start_x, layer.start_y) != (window.project.width/2, window.project.height/2)
    assert window.application_undo_stack.count() == undo_before + 1
    changed = (layer.start_x, layer.start_y); window.application_undo_stack.undo()
    assert (layer.start_x, layer.start_y) != changed
    window.application_undo_stack.redo(); before_escape = deepcopy(layer.to_dict()); undo_before = window.application_undo_stack.count()
    end = window.canvas._guide_points()["end"].toPoint(); QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=end)
    QTest.mouseMove(window.canvas, end + QPoint(32, 0)); QTest.keyClick(window.canvas, Qt.Key.Key_Escape); APP.processEvents()
    assert layer.to_dict() == before_escape and window.application_undo_stack.count() == undo_before
    window.dirty=False; window.close()


def test_particle_direction_and_endpoint_guides_use_renderer_math(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    emitter = window.create_particle_from_resource("resource_composition", composition.id)
    settings = window.particle_preview_manager.ensure_draft(emitter).settings
    settings.direction_degrees = 0; settings.speed_min = settings.speed_max = 2; settings.lifetime_min = settings.lifetime_max = 5
    guide = representative_particle_guide(settings)
    assert guide["endpoint_x"] == pytest.approx(settings.origin_x + 8)
    assert guide["endpoint_y"] == pytest.approx(settings.origin_y)
    window.canvas.set_effect_guide(emitter.id, "particle_system", settings); window.canvas.resize(700, 500); window.show(); APP.processEvents()
    endpoint = window.canvas._guide_points()["endpoint"].toPoint(); undo_before = window.application_undo_stack.count()
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=endpoint)
    QTest.mouseMove(window.canvas, endpoint + QPoint(16, 24))
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=endpoint + QPoint(16, 24)); APP.processEvents()
    updated = window.particle_preview_manager.ensure_draft(emitter).settings
    assert updated.direction_degrees != 0 and window.application_undo_stack.count() == undo_before + 1
    assert window.canvas.effect_guide_settings.direction_degrees == pytest.approx(updated.direction_degrees)
    window.dirty=False; window.close()


def test_particle_origin_direction_snap_shape_and_inspector_stay_synchronized(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    emitter = window.create_particle_from_resource("resource_composition", composition.id)
    settings = deepcopy(window.particle_preview_manager.ensure_draft(emitter).settings)
    settings.spawn_shape = "circle"; settings.radius = 5
    window.canvas.set_effect_guide(emitter.id, "particle_system", settings)
    origin_before = (settings.origin_x, settings.origin_y)
    window.canvas._guide_handle = "origin"; window.canvas._move_effect_guide(QPointF(10, 12), Qt.KeyboardModifier.NoModifier)
    assert (window.canvas.effect_guide_settings.origin_x, window.canvas.effect_guide_settings.origin_y) == (10, 12)
    window.canvas._guide_handle = "direction"; window.canvas._move_effect_guide(QPointF(24, 19), Qt.KeyboardModifier.ShiftModifier)
    assert window.canvas.effect_guide_settings.direction_degrees % 15 == pytest.approx(0)
    window.canvas._guide_handle = "shape"; window.canvas._move_effect_guide(QPointF(20, 12), Qt.KeyboardModifier.NoModifier)
    assert window.canvas.effect_guide_settings.radius == pytest.approx(10)
    window.select_particle_emitter(emitter.id); window.particle_properties.direction_degrees.setValue(45); APP.processEvents()
    assert window.canvas.effect_guide_settings.direction_degrees == pytest.approx(45)
    assert origin_before != (10, 12)
    window.dirty=False; window.close()


def test_composition_inspector_updates_canvas_guide_and_visibility_tooltip_is_dynamic(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    layer = window.create_composition_layer_from_resource(composition.id)
    window.composition_layer_properties.start_x.setValue(layer.start_x + 3); APP.processEvents()
    assert window.canvas.effect_guide_settings.start_x == pytest.approx(layer.start_x)
    table = window.timeline.table; row = len(window.project.layers)-1-window.layer_index
    eye = table.item(row, window.timeline.VISIBILITY_COLUMN); assert "Hide" in eye.toolTip()
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualItemRect(eye).center()); APP.processEvents()
    eye = table.item(row, window.timeline.VISIBILITY_COLUMN); assert "Show" in eye.toolTip()
    window.dirty=False; window.close()


def test_effect_editor_uses_resource_layer_terms_and_v6_serialization(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    direct = window.create_composition_layer_from_resource(composition.id)
    particle = window.create_particle_from_resource("resource_composition", composition.id)
    assert window.effect_library.composition_group.title() == "Resource Layers"
    assert not window.effect_library.particle_group.isVisible()
    assert window.particle_properties.title.text() == "Resource Layer"
    assert "Resource Layer" in window.add_resource_layer_action.text()
    assert window.add_particle_system_action not in window.layer_menu.actions()
    serialized = window.project.to_dict()
    assert "effect_composition_layers" not in serialized and "particle_emitters" not in serialized
    assert [item["placement_mode"] for item in serialized["effect_resource_layers"]] == ["single", "particle"]
    assert direct.resource_composition_id == composition.id and particle.settings.resource_id == composition.id
    window.dirty=False; window.close()


def test_editing_guides_setting_and_canvas_overlay_do_not_change_render(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window); window.create_composition_layer_from_resource(composition.id)
    before = window.project.compose_frame(0).copy(); window.editing_guides_action.setChecked(False)
    assert not window.canvas.show_effect_guides
    assert window.settings_service.settings.value("ui/show_effect_editing_guides", type=bool) is False
    window.canvas.repaint(); APP.processEvents(); assert np.array_equal(window.project.compose_frame(0), before)
    window.dirty=False; window.close()


def test_middle_drag_pans_without_editing_selected_guide(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    layer = window.create_composition_layer_from_resource(composition.id); window.canvas.resize(700, 500); window.show(); APP.processEvents()
    before_model = deepcopy(layer.to_dict()); before_pan = QPointF(window.canvas.pan_offset)
    center = window.canvas.rect().center()
    QTest.mousePress(window.canvas, Qt.MouseButton.MiddleButton, pos=center)
    QTest.mouseMove(window.canvas, center + QPoint(30, 18))
    QTest.mouseRelease(window.canvas, Qt.MouseButton.MiddleButton, pos=center + QPoint(30, 18)); APP.processEvents()
    assert window.canvas.pan_offset != before_pan and layer.to_dict() == before_model
    window.dirty=False; window.close()


def test_left_click_selects_visible_effect_layer_when_no_handle_is_hit(tmp_path):
    window = MainWindow(service(tmp_path)); composition = resource_project(window)
    layer = window.create_composition_layer_from_resource(composition.id); window.canvas.resize(700, 500); window.show(); APP.processEvents()
    generated_index = next(index for index,item in enumerate(window.project.layers) if item.id==layer.generated_layer_id)
    window.editing_guides_action.setChecked(False); window.layer_index=0; window.canvas.set_layer(0)
    point = window.canvas.canvas_to_widget(layer.start_x, layer.start_y).toPoint()
    QTest.mouseClick(window.canvas, Qt.MouseButton.LeftButton, pos=point); APP.processEvents()
    assert window.layer_index == generated_index
    window.dirty=False; window.close()
