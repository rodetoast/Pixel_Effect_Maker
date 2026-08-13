from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication,QMessageBox

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.project_io import load_project,save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget


APP=QApplication.instance() or QApplication([])


def _project():
    project=Project.create_default(width=16,height=16,frame_count=4);pixels=np.zeros((8,8,4),dtype=np.uint8);pixels[1:7,1:7]=[255,80,20,220];asset=SourceAsset("Smoke",pixels);composition=ResourceComposition("Smoke",8,8,12,4,True);layer=CompositionLayer("Smoke","source_asset",asset.id,0,3,pivot_x=2,pivot_y=3);layer.visible=False;layer.add_property("rotation").set_keyframe(0,0);layer.tracks["rotation"].set_keyframe(3,720,"Ease In/Out");layer.add_property("position").default_value=[4,-2];composition.layers.append(layer);project.source_assets.append(asset);project.resource_compositions.append(composition);return project,composition,layer,asset


def _editor(tmp_path):
    project,composition,layer,asset=_project();editor=ResourceEditorWidget(QSettings(str(tmp_path/"duplicate.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,layer.id);return editor,stack,project,composition,layer,asset


def _window(tmp_path):
    project,composition,_,asset=_project();settings=QSettings(str(tmp_path/"effect-duplicate.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);window.application_undo_stack.clear();layer.layer_transform.position_x=-50;layer.layer_transform.rotation_z=450;layer.layer_transform.set_keyframe("rotation_z",3,720,"Ease Out");layer.surface_transform.opacity=.4;layer.advanced_transform_enabled=False;layer.particle_settings.seed=77;layer.particle_settings.clip_speed_min=2;layer.particle_settings.clip_speed_max=3;layer.particle_settings.motion.mode="orbit";layer.particle_settings.motion.radius_end=18;layer.particle_settings.motion.set_keyframe("radius_end",3,24);window.select_resource_layer(layer.id);return window,layer,composition,asset


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


def test_duplicate_resource_layer_copies_state_new_id_shared_source_and_is_independent(tmp_path):
    editor,stack,_,composition,original,asset=_editor(tmp_path);original.locked=True;original.solo=True;expected=deepcopy(original.to_dict());duplicate=editor.duplicate_layer(original.id)
    assert duplicate.id!=original.id and duplicate.source_id==asset.id==original.source_id and duplicate.name=="Smoke (2)"
    assert [item.id for item in composition.layers]==[original.id,duplicate.id] and editor.selected_layer.id==duplicate.id and stack.count()==1
    assert duplicate.visible==expected["visible"] and duplicate.locked and duplicate.solo and (duplicate.start_frame,duplicate.end_frame,duplicate.pivot_x,duplicate.pivot_y)==(0,3,2,3)
    assert duplicate.tracks["rotation"].to_dict()==original.tracks["rotation"].to_dict() and duplicate.tracks["rotation"] is not original.tracks["rotation"]
    duplicate.tracks["rotation"].keyframe_at(3).value=1080;duplicate.tracks["position"].default_value[0]=99
    assert original.tracks["rotation"].keyframe_at(3).value==720 and original.tracks["position"].default_value==[4,-2]
    editor.close()


def test_duplicate_resource_layer_undo_redo_restores_same_identity_and_round_trips(tmp_path):
    editor,stack,project,composition,original,_=_editor(tmp_path);duplicate=editor.duplicate_layer(original.id);identifier=duplicate.id;snapshot=deepcopy(duplicate.to_dict())
    stack.undo();assert [item.id for item in composition.layers]==[original.id] and editor.selected_layer.id==original.id
    stack.redo();restored=composition.layers[1];assert restored.id==identifier and restored.to_dict()==snapshot and editor.selected_layer.id==identifier
    loaded=load_project(save_project(project,tmp_path/"resource-duplicate.peffect.json"));layers=loaded.resource_compositions[0].layers
    assert [item.id for item in layers]==[original.id,identifier] and layers[0].source_id==layers[1].source_id
    editor.close()


def test_duplicate_effect_particle_layer_copies_every_layer_local_state_and_is_independent(tmp_path):
    window,original,composition,_=_window(tmp_path);duplicate=window.duplicate_resource_layer(original.id)
    assert duplicate.id!=original.id and duplicate.generated_layer_id!=original.generated_layer_id and duplicate.resource_composition_id==composition.id
    assert duplicate.name=="Smoke (2)" and duplicate.placement_mode==PLACEMENT_PARTICLE and not duplicate.advanced_transform_enabled
    assert duplicate.layer_transform.to_dict()==original.layer_transform.to_dict() and duplicate.surface_transform.to_dict()==original.surface_transform.to_dict()
    assert duplicate.particle_settings.to_dict()==original.particle_settings.to_dict() and duplicate.particle_settings is not original.particle_settings and duplicate.particle_settings.motion is not original.particle_settings.motion
    duplicate.layer_transform.position_x=50;duplicate.particle_settings.seed=99;duplicate.particle_settings.motion.radius_end=30;duplicate.particle_settings.motion.tracks["radius_end"].keyframe_at(3).value=40
    assert original.layer_transform.position_x==-50 and original.particle_settings.seed==77 and original.particle_settings.motion.radius_end==18 and original.particle_settings.motion.tracks["radius_end"].keyframe_at(3).value==24
    _close(window)


def test_duplicate_effect_layer_is_one_undo_redo_and_round_trips(tmp_path):
    window,original,_,_=_window(tmp_path);duplicate=window.duplicate_resource_layer(original.id);identifier=duplicate.id;snapshot=deepcopy(duplicate.to_dict())
    assert window.application_undo_stack.count()==1 and window.project.effect_resource_layers[1].id==identifier and window.effect_library.current_composition_id()==identifier
    window.application_undo_stack.undo();assert [item.id for item in window.project.effect_resource_layers]==[original.id]
    window.application_undo_stack.redo();restored=window.project.effect_resource_layers[1];assert restored.id==identifier and restored.to_dict()==snapshot
    loaded=load_project(save_project(window.project,tmp_path/"effect-duplicate.peffect.json"));layers=loaded.effect_resource_layers
    assert [item.id for item in layers]==[original.id,identifier] and layers[0].resource_composition_id==layers[1].resource_composition_id
    _close(window)


def test_duplicate_references_keep_asset_and_resource_delete_protection(tmp_path,monkeypatch):
    editor,_,project,_,original,asset=_editor(tmp_path);editor.duplicate_layer(original.id);settings=QSettings(str(tmp_path/"delete-safety.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);warnings=[];monkeypatch.setattr(QMessageBox,"warning",lambda *args,**kwargs:warnings.append(args))
    assert not window.delete_resource("source_asset",asset.id) and asset in window.project.source_assets and warnings
    effect=window.create_resource_layer_from_resource(window.project.resource_compositions[0].id);window.duplicate_resource_layer(effect.id);window.resource_editor.project=window.project;window.resource_editor.localization=window.localization;window.resource_editor._delete_composition(window.project.resource_compositions[0].id)
    assert window.project.resource_compositions and len(window.project.effect_resource_layers)==2 and len(warnings)>=2
    editor.close();_close(window)
