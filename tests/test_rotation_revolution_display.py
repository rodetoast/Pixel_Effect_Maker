from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import AnimationTrack, CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.ui.focus_wheel_widgets import RotationSpinBox
from app.ui.resource_editor_v2.composition_inspector import LayerInspector
from app.ui.resource_layer_transform_panel import ResourceLayerTransformPanel


APP=QApplication.instance() or QApplication([])


class _Localization:
    language="en"
    @staticmethod
    def text(key):return key


def _wheel(spin,delta=120):
    local=QPointF(spin.rect().center());event=QWheelEvent(local,QPointF(spin.mapToGlobal(local.toPoint())),QPoint(),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.ControlModifier,Qt.ScrollPhase.ScrollUpdate,False);APP.notify(spin,event);APP.processEvents()


@pytest.mark.parametrize("value,text",[(0,"0x + 0.000°"),(210,"0x + 210.000°"),(450,"1x + 90.000°"),(720,"2x + 0.000°"),(-90,"0x - 90.000°"),(-450,"-1x - 90.000°")])
def test_rotation_display_and_round_trip(value,text):
    spin=RotationSpinBox();spin.setDecimals(3);spin.setRange(-36000,36000)
    assert spin.textFromValue(value)==text and spin.valueFromText(text)==value


@pytest.mark.parametrize("text,value",[("720",720),("720°",720),("2x",720),("2x+0",720),("2x + 30°",750),("-1x - 90°",-450)])
def test_rotation_accepts_plain_and_revolution_input(text,value):
    spin=RotationSpinBox();spin.setRange(-36000,36000)
    assert spin.valueFromText(text)==value


def test_rotation_typing_commits_once_on_enter_and_focus_out():
    spin=RotationSpinBox();other=QWidget();spin.setRange(-36000,36000);spin.setDecimals(3);other.show();spin.show();values=[];spin.valueChanged.connect(values.append)
    spin.setFocus();spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"2x + 90");APP.processEvents();assert spin.value()==0 and values==[]
    QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Return);APP.processEvents();assert spin.value()==810 and values==[810]
    spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"-1x - 90");APP.processEvents();assert spin.value()==810
    spin.clearFocus();APP.processEvents();assert spin.value()==-450 and values[-1]==-450
    spin.close();other.close()


def test_rotation_arrow_and_ctrl_wheel_cross_turn_boundary():
    spin=RotationSpinBox();spin.setRange(-36000,36000);spin.setDecimals(3);spin.setSingleStep(1);spin.setValue(719);spin.show();spin.setFocus();QTest.keyClick(spin,Qt.Key.Key_Up);assert spin.value()==720 and spin.text().startswith("2x + 0.000")
    spin.setValue(359);_wheel(spin);assert spin.value()==360 and spin.text().startswith("1x + 0.000");spin.close()


def test_rotation_tracks_preserve_total_degrees_interpolation_and_round_trip():
    track=AnimationTrack("rotation",0);track.set_keyframe(0,0);track.set_keyframe(10,720)
    assert track.keyframe_at(10).value==720 and track.evaluate(5)==360
    project=Project.create_default(frame_count=11);asset=SourceAsset("sprite",__import__("numpy").zeros((2,2,4),dtype="uint8"));project.source_assets.append(asset);composition=ResourceComposition("sprite",2,2,12,11,True);layer=CompositionLayer("sprite","source_asset",asset.id,0,10);layer.tracks["rotation"]=track;composition.layers.append(layer);project.resource_compositions.append(composition)
    loaded=Project.from_dict(project.to_dict());loaded_track=loaded.resource_compositions[0].layers[0].tracks["rotation"]
    assert loaded_track.keyframe_at(10).value==720 and loaded_track.evaluate(5)==360 and FORMAT_VERSION==10


def test_resource_and_effect_rotation_fields_use_total_degree_widget():
    layer=EffectResourceLayer("effect","resource");panel=ResourceLayerTransformPanel();panel.set_layer(layer,0)
    assert all(isinstance(panel.fields[name],RotationSpinBox) and isinstance(panel.surface_fields[name],RotationSpinBox) for name in ("rotation_x","rotation_y","rotation_z"))
    composition_layer=CompositionLayer("sprite","source_asset","asset",0,0);[composition_layer.add_property(name) for name in ("rotation_x","rotation_y","rotation")];inspector=LayerInspector();inspector.retranslate(_Localization());inspector.set_layer(composition_layer,None,0)
    assert all(isinstance(inspector.property_cards[name]["editors"][0],RotationSpinBox) for name in ("rotation_x","rotation_y","rotation"));panel.close();inspector.close()


def test_effect_conditional_auto_key_keeps_total_degrees():
    layer=EffectResourceLayer("effect","resource",end_frame=10);layer.layer_transform.set_keyframe("rotation_z",0,0);panel=ResourceLayerTransformPanel();panel.set_layer(layer,10);changes=[];panel.interactive_transform_changed.connect(lambda _,value,name:changes.append((value,name)))
    panel.fields["rotation_z"].setValue(810)
    assert changes[-1][0].tracks["rotation_z"].keyframe_at(10).value==810 and changes[-1][1]=="rotation_z";panel.close()
