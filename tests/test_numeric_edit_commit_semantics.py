"""Numeric text entry commits once while explicit step controls stay immediate."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QUndoStack, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import ParticleMotionSettings
from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.ui.resource_editor_v2.asset_inspector_widget import AssetInspectorWidget
from app.ui.resource_editor_v2.composition_inspector import LayerInspector
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget
from app.ui.resource_layer_transform_panel import ResourceLayerTransformPanel


APP = QApplication.instance() or QApplication([])


class _Localization:
    language = "en"

    @staticmethod
    def text(key):
        return key


def _resource_editor(tmp_path):
    project = Project.create_default(width=16, height=16)
    pixels = np.zeros((3, 3, 4), dtype=np.uint8)
    asset = SourceAsset("sprite", pixels)
    project.source_assets.append(asset)
    composition = ResourceComposition("Resource", 16, 16, 12, 13, True)
    layer = CompositionLayer("sprite", "source_asset", asset.id, 0, 12)
    composition.layers.append(layer)
    project.resource_compositions.append(composition)
    editor = ResourceEditorWidget(QSettings(str(tmp_path / "numeric.ini"), QSettings.Format.IniFormat))
    editor.retranslate_ui(_Localization())
    stack = QUndoStack()
    editor.set_undo_stack(stack)
    editor.show()
    APP.processEvents()
    editor.refresh(project)
    editor.controller.select_composition(composition.id)
    editor.controller.select_layer(layer.id)
    APP.processEvents()
    return editor, stack, project, layer


def _replace_text(spin, text, after_character=None):
    spin.setFocus()
    APP.processEvents()
    spin.lineEdit().selectAll()
    APP.processEvents()
    for character in text:
        QTest.keyClicks(spin.lineEdit(), character)
        APP.processEvents()
        if after_character:
            after_character(character)


def _ctrl_wheel(spin, delta=120):
    local = QPointF(spin.rect().center())
    event = QWheelEvent(
        local,
        QPointF(spin.mapToGlobal(local.toPoint())),
        QPoint(),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    APP.notify(spin, event)
    APP.processEvents()


@pytest.mark.parametrize("widget_type", [ScrollSafeSpinBox, ScrollSafeDoubleSpinBox])
def test_shared_numeric_widgets_disable_keyboard_tracking(widget_type):
    spin = widget_type()
    assert not spin.keyboardTracking()


def test_spinbox_typing_does_not_commit_each_digit_and_enter_commits_once():
    spin = ScrollSafeDoubleSpinBox(); spin.setRange(-1000, 1000); spin.setDecimals(3); spin.setValue(0); spin.show()
    values = []; spin.valueChanged.connect(values.append)
    _replace_text(spin, "210", lambda _character: (values == [] and spin.value() == 0) or pytest.fail("typing committed early"))
    assert spin.lineEdit().text() == "210" and values == []
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents()
    assert spin.value() == 210 and values == [210]
    spin.close()


def test_spinbox_three_digit_entry_commits_on_focus_out_once():
    spin = ScrollSafeSpinBox(); spin.setRange(-1000, 1000); spin.show()
    values = []; spin.valueChanged.connect(values.append)
    _replace_text(spin, "360")
    assert spin.value() == 0 and values == []
    spin.clearFocus(); APP.processEvents()
    assert spin.value() == 360 and values == [360]
    spin.close()


@pytest.mark.parametrize("text, expected", [("1.25", 1.25), ("-0.75", -0.75), ("-120", -120.0)])
def test_decimal_and_negative_text_entry_commit_once(text, expected):
    spin = ScrollSafeDoubleSpinBox(); spin.setRange(-1000, 1000); spin.setDecimals(3); spin.show(); values = []; spin.valueChanged.connect(values.append)
    _replace_text(spin, text)
    assert spin.value() == 0 and values == []
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Enter); APP.processEvents()
    assert spin.value() == pytest.approx(expected) and values == [expected]
    spin.close()


def test_invalid_partial_text_never_reaches_model_and_recovers_safely():
    spin = ScrollSafeDoubleSpinBox(); spin.setRange(-1000, 1000); spin.setDecimals(3); spin.setValue(12); spin.show(); values = []; spin.valueChanged.connect(values.append)
    _replace_text(spin, "-")
    assert spin.value() == 12 and values == []
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents()
    assert spin.minimum() <= spin.value() <= spin.maximum() and len(values) <= 1
    spin.close()


def test_arrow_keyboard_and_ctrl_wheel_steps_still_commit_immediately():
    spin = ScrollSafeDoubleSpinBox(); spin.setRange(-100, 100); spin.setSingleStep(1); spin.show(); values = []; spin.valueChanged.connect(values.append)
    QTest.keyClick(spin, Qt.Key.Key_Up); APP.processEvents()
    assert spin.value() == 1 and values == [1]
    spin.stepDown(); APP.processEvents()
    assert spin.value() == 0 and values[-1] == 0
    _ctrl_wheel(spin)
    assert spin.value() == 1 and values[-1] == 1
    spin.close()


def test_static_typing_commits_one_undo_without_creating_key(tmp_path):
    editor, stack, _, layer = _resource_editor(tmp_path); track = layer.add_property("rotation"); editor.controller.changed(); editor.set_frame(12)
    spin = editor.layer_inspector.property_cards["rotation"]["editors"][0]
    _replace_text(spin, "210", lambda _character: (track.default_value == 0 and not track.keyframes and stack.count() == 0) or pytest.fail("static model changed while typing"))
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents()
    assert layer.tracks["rotation"].default_value == 210 and layer.tracks["rotation"].keyframes == [] and stack.count() == 1
    stack.undo(); assert layer.tracks["rotation"].default_value == 0 and not layer.tracks["rotation"].keyframes
    editor.close()


def test_animated_unkeyed_210_stays_hollow_until_enter_then_auto_keys_once(tmp_path):
    editor, stack, _, layer = _resource_editor(tmp_path); track = layer.add_property("rotation"); track.set_keyframe(0, 0); editor.controller.changed(); editor.set_frame(12)
    card = editor.layer_inspector.property_cards["rotation"]; spin = card["editors"][0]; commits = []; editor.layer_inspector.property_value_requested.connect(lambda *parts: commits.append(parts))
    def unchanged(_character):
        assert not track.has_keyframe(12) and track.evaluate(12) == 0 and stack.count() == 0
        assert card["keyframe"].text() == "◇"
    _replace_text(spin, "210", unchanged)
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents()
    assert layer.tracks["rotation"].keyframe_at(12).value == 210 and len(layer.tracks["rotation"].keyframes) == 2 and stack.count() == 1 and len(commits) == 1
    assert editor.layer_inspector.property_cards["rotation"]["keyframe"].text() == "◆"
    stack.undo(); assert not layer.tracks["rotation"].has_keyframe(12)
    stack.redo(); assert layer.tracks["rotation"].keyframe_at(12).value == 210
    editor.close()


def test_animated_unkeyed_typing_auto_keys_on_focus_out_once(tmp_path):
    editor, stack, _, layer = _resource_editor(tmp_path); track = layer.add_property("rotation"); track.set_keyframe(0, 0); editor.controller.changed(); editor.set_frame(12)
    spin = editor.layer_inspector.property_cards["rotation"]["editors"][0]; commits = []; editor.layer_inspector.property_value_requested.connect(lambda *parts: commits.append(parts))
    _replace_text(spin, "120")
    assert not track.has_keyframe(12) and commits == []
    editor.asset_fit.setFocus(); APP.processEvents()
    assert layer.tracks["rotation"].keyframe_at(12).value == 120 and stack.count() == 1 and len(commits) == 1
    editor.close()


def test_existing_key_typing_updates_once_without_duplicate(tmp_path):
    editor, stack, _, layer = _resource_editor(tmp_path); track = layer.add_property("rotation"); track.set_keyframe(12, 90); editor.controller.changed(); editor.set_frame(12)
    spin = editor.layer_inspector.property_cards["rotation"]["editors"][0]; commits = []; editor.layer_inspector.property_value_requested.connect(lambda *parts: commits.append(parts))
    _replace_text(spin, "210", lambda _character: track.keyframe_at(12).value == 90 or pytest.fail("existing key changed while typing"))
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents()
    assert len(layer.tracks["rotation"].keyframes) == 1 and layer.tracks["rotation"].keyframe_at(12).value == 210 and stack.count() == 1 and len(commits) == 1
    editor.close()


@pytest.mark.parametrize("property_id,text", [("rotation_x", "120"), ("rotation_y", "210"), ("rotation", "-120"), ("position", "999"), ("scale", "120")])
def test_resource_numeric_properties_share_delayed_typing(property_id, text):
    layer = CompositionLayer("sprite", "source_asset", "asset", 0, 12); layer.add_property(property_id)
    inspector = LayerInspector(); inspector.retranslate(_Localization()); inspector.set_layer(layer, None, 5); inspector.show(); values = []; inspector.property_value_requested.connect(lambda *parts: values.append(parts))
    spin = inspector.property_cards[property_id]["editors"][0]; original = spin.value(); _replace_text(spin, text)
    assert spin.value() == original and values == []
    QTest.keyClick(spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents()
    assert len(values) == 1
    inspector.close()


def test_effect_motion_and_asset_inspectors_share_delayed_typing():
    effect = EffectResourceLayer("Effect", "resource", end_frame=12)
    transform_panel = ResourceLayerTransformPanel(); transform_panel.setChecked(True); transform_panel.set_layer(effect, 5); transform_panel.show(); APP.processEvents(); transform_changes = []; transform_panel.interactive_transform_changed.connect(lambda *parts: transform_changes.append(parts))
    transform_spin = transform_panel.fields["rotation_z"]; _replace_text(transform_spin, "210"); assert transform_changes == []
    QTest.keyClick(transform_spin.lineEdit(), Qt.Key.Key_Return); APP.processEvents(); assert len(transform_changes) == 1

    project = Project.create_default(); project._current_effect_frame = 5; effect.placement_mode = "particle"; effect.particle_settings.motion = ParticleMotionSettings(mode="orbit", radius_end=20)
    motion_panel = ParticlePropertiesPanel(); motion_panel.set_resource_layer(effect, project); motion_panel.show(); APP.processEvents(); motion_changes = []; motion_panel.draft_changed.connect(lambda *parts: motion_changes.append(parts))
    _replace_text(motion_panel.motion_radius_end, "210"); assert motion_changes == []
    QTest.keyClick(motion_panel.motion_radius_end.lineEdit(), Qt.Key.Key_Return); APP.processEvents(); assert len(motion_changes) == 1

    asset = SourceAsset("asset", np.zeros((4, 4, 4), dtype=np.uint8)); asset_panel = AssetInspectorWidget(); asset_panel.set_asset(asset); asset_panel.show(); APP.processEvents(); pivots = []; asset_panel.pivot_changed.connect(lambda *parts: pivots.append(parts))
    _replace_text(asset_panel.pivot_x, "120"); assert pivots == []
    QTest.keyClick(asset_panel.pivot_x.lineEdit(), Qt.Key.Key_Return); APP.processEvents(); assert pivots == [(120.0, asset.pivot_y)]
    transform_panel.close(); motion_panel.close(); asset_panel.close()


def test_programmatic_refresh_and_frame_scrub_do_not_commit_or_create_key(tmp_path):
    editor, stack, _, layer = _resource_editor(tmp_path); track = layer.add_property("rotation"); track.set_keyframe(0, 0); editor.controller.changed()
    for frame in (12, 3, 9, 1, 12): editor.set_frame(frame)
    assert [key.frame for key in track.keyframes] == [0] and stack.count() == 0
    effect = EffectResourceLayer("Effect", "resource", end_frame=12); effect.layer_transform.set_keyframe("rotation_z", 0, 0); panel = ResourceLayerTransformPanel(); changes = []; panel.interactive_transform_changed.connect(lambda *parts: changes.append(parts))
    for frame in (0, 5, 12): panel.set_layer(effect, frame)
    assert changes == [] and [key.frame for key in effect.layer_transform.tracks["rotation_z"].keyframes] == [0]
    panel.close(); editor.close()
