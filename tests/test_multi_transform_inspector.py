from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.resource_composition import CompositionLayer
from app.services.multi_transform_service import (
    mixed_numeric_value,
    set_effect_local_property,
    set_resource_local_component,
    validate_multi_transform_selection,
)
from app.ui.resource_editor_v2.composition_inspector import LayerInspector
from app.ui.resource_layer_transform_panel import ResourceLayerTransformPanel

APP=QApplication.instance() or QApplication([])


def _layer(name):
    return CompositionLayer(name, "source_asset", name, 0, 12)


def test_mixed_value_uses_float_tolerance():
    assert mixed_numeric_value([1.0, 1.0 + 0.5e-6]) == pytest.approx(1.0)
    assert mixed_numeric_value([1.0, 1.0 + 2e-6]) is None


def test_resource_batch_numeric_edit_is_absolute_local_and_conditional_autokey():
    a, b = _layer("a"), _layer("b")
    a.add_property("position").default_value = [10, 1]
    track = b.add_property("position")
    track.default_value = [20, 2]
    track.set_keyframe(0, [20, 2])
    assert set_resource_local_component(a, "position", 0, 5, 50)
    assert set_resource_local_component(b, "position", 0, 5, 50)
    assert a.value("position", 5) == [50, 1]
    assert b.value("position", 5) == [50, 2]
    assert not a.tracks["position"].keyframes
    assert b.tracks["position"].keyframe_at(5).value == [50, 2]


def test_effect_batch_numeric_edit_keeps_total_rotation_degrees():
    layer = EffectResourceLayer("effect", "resource", end_frame=12)
    layer.layer_transform.set_keyframe("rotation_z", 0, 720)
    assert set_effect_local_property(layer, "rotation_z", 5, 1080)
    assert layer.layer_transform.tracks["rotation_z"].keyframe_at(5).value == 1080


def test_group_and_locked_selections_are_rejected_atomically():
    a, b = _layer("a"), _layer("b")
    leaves, reason = validate_multi_transform_selection([a, b], {a.id, "group"}, group_ids={"group"})
    assert leaves == [] and reason == "group"
    b.locked = True
    leaves, reason = validate_multi_transform_selection([a, b], {a.id, b.id})
    assert leaves == [] and reason == "locked"


def test_resource_mixed_field_commits_only_explicit_component():
    a,b=_layer("a"),_layer("b");a.add_property("position").default_value=[10,3];b.add_property("position").default_value=[20,4]
    inspector=LayerInspector();inspector.set_layer(a,None,0);inspector.set_multi_layers([a,b],0);spin=inspector.property_cards["position"]["editors"][0]
    assert spin.lineEdit().text()=="—";commits=[];inspector.batch_property_value_requested.connect(lambda *value:commits.append(value));spin.show();spin.setFocus();spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"50");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Return);APP.processEvents()
    assert commits==[("position",0,50.0)];inspector.close()


def test_effect_mixed_field_emits_batch_property_and_primary_only_fields_stay_primary():
    a=EffectResourceLayer("a","resource",end_frame=12);b=EffectResourceLayer("b","resource",end_frame=12);a.layer_transform.position_x=10;b.layer_transform.position_x=20
    panel=ResourceLayerTransformPanel();panel.set_layer(a,0);panel.set_multi_layers([a,b],0);spin=panel.fields["position_x"]
    assert spin.lineEdit().text()=="—" and panel.fields["position_z"].isEnabled();commits=[];panel.batch_transform_changed.connect(lambda *value:commits.append(value));spin.show();spin.setFocus();spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"50");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Return);APP.processEvents()
    assert commits==[("position_x",50.0)];panel.close()
