from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def _wheel(spin,delta):
    local=QPointF(spin.rect().center());event=QWheelEvent(local,QPointF(spin.mapToGlobal(local.toPoint())),QPoint(),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.ControlModifier,Qt.ScrollPhase.ScrollUpdate,False);APP.notify(spin,event);APP.processEvents()


def _window(tmp_path):
    project=Project.create_default(width=24,height=24,frame_count=3);pixels=np.zeros((5,5,4),dtype=np.uint8);pixels[1:4,1:4]=[255,80,20,255];asset=SourceAsset("sprite",pixels);composition=ResourceComposition("sprite",5,5,12,3,True);composition.layers.append(CompositionLayer("sprite","source_asset",asset.id,0,2));project.source_assets.append(asset);project.resource_compositions.append(composition);window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"wheel.ini"),QSettings.Format.IniFormat)),initial_project=project);return window,composition


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close();APP.processEvents()


def test_real_undo_stack_index_changed_invokes_main_window_handler(tmp_path):
    window,composition=_window(tmp_path);seen=[];window.application_undo_stack.indexChanged.connect(seen.append);before=window._project_edit_revision;window.create_resource_layer_from_resource(composition.id)
    assert seen and seen[-1]==window.application_undo_stack.index() and window._project_edit_revision==before+1;_close(window)


def test_ctrl_wheel_500_steps_is_safe_and_stops_at_minimum_without_noop_undo(tmp_path):
    window,composition=_window(tmp_path);layer=window.create_resource_layer_from_resource(composition.id);spin=window.composition_layer_properties.transform_panel.fields["position_x"];spin.setFocus();window.application_undo_stack.clear();window.application_undo_stack.setClean()
    spin.setValue(spin.minimum()+2);APP.processEvents();window.application_undo_stack.clear();window.application_undo_stack.setClean()
    for _ in range(500):_wheel(spin,-120)
    assert spin.value()==spin.minimum() and layer.layer_transform.position_x==spin.minimum()
    count=window.application_undo_stack.count();revision=window._project_edit_revision
    for _ in range(20):_wheel(spin,-120)
    assert window.application_undo_stack.count()==count and window._project_edit_revision==revision;_close(window)


def test_ctrl_wheel_maximum_boundary_and_static_property_are_safe(tmp_path):
    window,composition=_window(tmp_path);layer=window.create_resource_layer_from_resource(composition.id);spin=window.composition_layer_properties.transform_panel.fields["perspective_strength"];layer.layer_transform.perspective_strength=spin.maximum();window.select_resource_layer(layer.id);window.application_undo_stack.clear();before=window.application_undo_stack.count()
    for _ in range(100):_wheel(spin,120)
    assert spin.value()==spin.maximum() and window.application_undo_stack.count()==before and not layer.layer_transform.tracks.get("perspective_strength");_close(window)


def test_ctrl_wheel_at_animated_minimum_does_not_auto_key(tmp_path):
    window,composition=_window(tmp_path);layer=window.create_resource_layer_from_resource(composition.id);layer.layer_transform.set_keyframe("opacity",0,0);window.frame_index=1;window.select_resource_layer(layer.id);spin=window.composition_layer_properties.transform_panel.fields["opacity"];assert spin.value()==spin.minimum();window.application_undo_stack.clear()
    for _ in range(20):_wheel(spin,-120)
    assert not layer.layer_transform.tracks["opacity"].has_keyframe(1) and window.application_undo_stack.count()==0;_close(window)


def test_effect_add_remove_reorder_and_resource_commands_emit_index_changed_safely(tmp_path):
    window,composition=_window(tmp_path);seen=[];window.application_undo_stack.indexChanged.connect(seen.append);a=window.create_resource_layer_from_resource(composition.id);b=window.create_resource_layer_from_resource(composition.id);window.rename_resource_layer(a.id,"A");window.reorder_resource_layer(a.id,1);window.remove_resource_layer(b.id);window.application_undo_stack.undo();window.application_undo_stack.redo()
    assert len(seen)>=7 and seen[-1]==window.application_undo_stack.index();_close(window)


def test_twenty_real_command_wheel_undo_redo_sequences_do_not_raise(tmp_path):
    window,composition=_window(tmp_path)
    for index in range(20):
        layer=window.create_resource_layer_from_resource(composition.id);spin=window.composition_layer_properties.transform_panel.fields["position_x"]
        _wheel(spin,-120)
        if len(window.project.effect_resource_layers)>1:window.reorder_resource_layer(layer.id,-1)
        window.application_undo_stack.undo();window.application_undo_stack.redo()
    assert window.application_undo_stack.index()>0 and len(window.project.effect_resource_layers)==20;_close(window)
