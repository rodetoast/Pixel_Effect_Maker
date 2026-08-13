from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP=QApplication.instance() or QApplication([])


def _panel(lo=1,max_value=1):
    panel=ParticlePropertiesPanel();panel.emitter_id="emitter";panel.clip.addItem("clip",("animation_clip","clip"));panel.clip.setCurrentIndex(0)
    panel._loading=True;panel.clip_speed_min.setValue(lo);panel.clip_speed_max.setValue(max_value);panel._loading=False
    return panel


def _wheel(widget,delta=120):
    local=QPointF(widget.rect().center())
    event=QWheelEvent(local,QPointF(widget.mapToGlobal(local.toPoint())),QPoint(),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.ControlModifier,Qt.ScrollPhase.ScrollUpdate,False)
    APP.notify(widget,event);APP.processEvents()


def _window(tmp_path):
    service=ShortcutSettingsService(QSettings(str(tmp_path/"playback-speed.ini"),QSettings.Format.IniFormat));window=MainWindow(service)
    pixels=np.zeros((4,4,4),dtype=np.uint8);pixels[1:3,1:3]=[255,100,20,255];asset=SourceAsset("Spark",pixels);composition=ResourceComposition("Spark",4,4,12,4,True);composition.layers.append(CompositionLayer("Spark","source_asset",asset.id,0,3));window.project.source_assets.append(asset);window.project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();return window,layer


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


@pytest.mark.parametrize(("lo","hi","field","value","expected"),[(1,1,"clip_speed_min",2,(2,2)),(2,4,"clip_speed_max",1.5,(1.5,1.5)),(1,4,"clip_speed_min",3,(3,4)),(1,4,"clip_speed_max",2,(1,2))])
def test_playback_speed_pair_policy_is_atomic_in_inspector(lo,hi,field,value,expected):
    panel=_panel(lo,hi);drafts=[];panel.draft_changed.connect(lambda _id,settings:drafts.append((settings.clip_speed_min,settings.clip_speed_max)))
    getattr(panel,field).setValue(value)
    assert (panel.clip_speed_min.value(),panel.clip_speed_max.value())==expected
    assert drafts==[expected]


@pytest.mark.parametrize("interaction",["typing","arrow","wheel"])
def test_min_crossing_paths_keep_pair_valid(interaction):
    panel=_panel();drafts=[];panel.draft_changed.connect(lambda _id,settings:drafts.append(settings))
    spin=panel.clip_speed_min;spin.setFocus()
    if interaction=="typing":spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"2");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Enter)
    elif interaction=="arrow":QTest.keyClick(spin,Qt.Key.Key_Up)
    else:_wheel(spin)
    APP.processEvents()
    assert panel.clip_speed_min.value()==panel.clip_speed_max.value()>1
    assert len(drafts)==1 and drafts[0].clip_speed_min<=drafts[0].clip_speed_max


def test_ctrl_wheel_boundary_stress_never_emits_invalid_pair():
    panel=_panel();pairs=[];panel.draft_changed.connect(lambda _id,s:pairs.append((s.clip_speed_min,s.clip_speed_max)))
    for _ in range(500):_wheel(panel.clip_speed_min)
    for _ in range(500):_wheel(panel.clip_speed_max,-120)
    assert pairs and all(lo<=hi for lo,hi in pairs)
    assert panel.clip_speed_min.minimum()<=panel.clip_speed_min.value()<=panel.clip_speed_min.maximum()
    assert panel.clip_speed_max.minimum()<=panel.clip_speed_max.value()<=panel.clip_speed_max.maximum()


@pytest.mark.parametrize(("field","before","value","after"),[("clip_speed_min",(1,1),2,(2,2)),("clip_speed_max",(2,4),1.5,(1.5,1.5))])
def test_crossing_pair_is_one_undo_and_redo(tmp_path,field,before,value,after):
    window,layer=_window(tmp_path);panel=window.particle_properties;layer.particle_settings.clip_speed_min=before[0];layer.particle_settings.clip_speed_max=before[1];window.particle_preview_manager.revert(layer.as_particle_emitter());window.select_resource_layer(layer.id);indexes=[];window.application_undo_stack.indexChanged.connect(indexes.append)
    getattr(panel,field).setValue(value)
    assert window.application_undo_stack.count()==1 and (layer.particle_settings.clip_speed_min,layer.particle_settings.clip_speed_max)==after
    window.application_undo_stack.undo();assert (layer.particle_settings.clip_speed_min,layer.particle_settings.clip_speed_max)==before
    window.application_undo_stack.redo();assert (layer.particle_settings.clip_speed_min,layer.particle_settings.clip_speed_max)==after
    assert indexes==[1,0,1]
    _close(window)


def test_boundary_noop_creates_no_undo(tmp_path):
    window,layer=_window(tmp_path);panel=window.particle_properties;panel.clip_speed_min.setValue(panel.clip_speed_min.value())
    assert window.application_undo_stack.count()==0 and not window.dirty
    _close(window)


def test_undo_index_callback_survives_normal_add_reorder_and_resource_commands(tmp_path,monkeypatch):
    errors=[];monkeypatch.setattr(sys,"excepthook",lambda kind,value,traceback:errors.append((kind,value)))
    window,first=_window(tmp_path);composition=window.project.resource_compositions[0];indexes=[];window.application_undo_stack.indexChanged.connect(indexes.append)
    second=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    assert window.reorder_resource_layer(first.id,1)
    assert window.rename_resource_layer(first.id,"Renamed")
    for _ in range(3):window.application_undo_stack.undo()
    for _ in range(3):window.application_undo_stack.redo()
    APP.processEvents()
    assert indexes==[1,2,3,2,1,0,1,2,3] and errors==[]
    assert not hasattr(window,"_undo_index_relay") and callable(window._undo_index_callback)
    _close(window)


def test_user_min_undo_redo_sequence_remains_valid_for_twenty_cycles(tmp_path):
    window,layer=_window(tmp_path);panel=window.particle_properties
    for _ in range(20):
        panel.clip_speed_min.setValue(2);window.application_undo_stack.undo();window.application_undo_stack.redo()
        panel.clip_speed_min.setValue(3);window.application_undo_stack.undo()
        assert layer.particle_settings.clip_speed_min<=layer.particle_settings.clip_speed_max
    assert window.application_undo_stack.count()>=1
    _close(window)
