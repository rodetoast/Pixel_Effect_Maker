from __future__ import annotations
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import json
import numpy as np
from PySide6.QtCore import QSettings,Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget

APP=QApplication.instance() or QApplication([])

def project_with_layers(count=5):
    project=Project.create_default(width=4,height=4,frame_count=2);composition=ResourceComposition("C",4,4,12,2)
    for index in range(count):
        pixels=np.zeros((2,2,4),dtype=np.uint8);pixels[:]=[index*30,20,255-index*30,255];asset=SourceAsset(chr(65+index),pixels);project.source_assets.append(asset);composition.layers.append(CompositionLayer(asset.name,"source_asset",asset.id,0,1))
    project.resource_compositions=[composition];return project,composition

def resource_editor(tmp_path):
    project,composition=project_with_layers();editor=ResourceEditorWidget(QSettings(str(tmp_path/"r.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,composition.layers[-1].id);return editor,stack,project,composition

def effect_window(tmp_path):
    project,_=project_with_layers();settings=QSettings(str(tmp_path/"e.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);layers=[window.create_resource_layer_from_resource(item.id) for item in project.resource_compositions];return window,layers

def close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()

def test_resource_click_ctrl_shift_reverse_and_ctrl_a_are_runtime_only(tmp_path):
    editor,stack,_,composition=resource_editor(tmp_path);ui=[item.id for item in reversed(composition.layers)];revision=composition.revision
    editor.select_layer_with_modifiers(ui[1]);editor.select_layer_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier);assert editor.selected_layer_ids=={ui[1],ui[3]} and editor.primary_layer_id==ui[3] and editor.selection_anchor_id==ui[3]
    editor.select_layer_with_modifiers(ui[1],Qt.KeyboardModifier.ControlModifier);assert editor.selected_layer_ids=={ui[3]} and editor.primary_layer_id==ui[3]
    editor.select_layer_with_modifiers(ui[1]);editor.select_layer_with_modifiers(ui[4],Qt.KeyboardModifier.ShiftModifier);assert editor.selected_layer_ids==set(ui[1:5]) and editor.primary_layer_id==ui[4] and editor.selection_anchor_id==ui[1]
    editor.select_layer_with_modifiers(ui[0],Qt.KeyboardModifier.ShiftModifier);assert editor.selected_layer_ids==set(ui[:2])
    editor.select_all_layers();assert editor.selected_layer_ids==set(ui) and editor.primary_layer_id==ui[0] and stack.count()==0 and composition.revision==revision and FORMAT_VERSION==11
    payload=json.dumps(editor.project.to_dict());assert "selected_layer_ids" not in payload and "primary_layer_id" not in payload and "selection_anchor_id" not in payload
    editor.close()

def test_effect_selection_uses_logical_ids_and_primary_only(tmp_path):
    project,composition=project_with_layers();project.resource_compositions=[]
    for asset in project.source_assets:
        project.resource_compositions.append(ResourceComposition(asset.name,4,4,12,2,layers=[CompositionLayer(asset.name,"source_asset",asset.id,0,1)]))
    settings=QSettings(str(tmp_path/"effect.ini"),QSettings.Format.IniFormat);window=MainWindow(ShortcutSettingsService(settings),initial_project=project);layers=[window.create_resource_layer_from_resource(item.id) for item in project.resource_compositions];window.application_undo_stack.clear();ui=window._effect_ui_ids()
    window.select_effect_layers_with_modifiers(ui[1]);window.select_effect_layers_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier);assert window.selected_effect_layer_ids=={ui[1],ui[3]} and window.primary_effect_layer_id==ui[3]
    window.select_effect_layers_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier);assert window.selected_effect_layer_ids=={ui[1]} and window.primary_effect_layer_id==ui[1]
    window.select_effect_layers_with_modifiers(ui[4],Qt.KeyboardModifier.ShiftModifier);assert window.selected_effect_layer_ids==set(ui[3:5]) and window.primary_effect_layer_id==ui[4] and window.effect_selection_anchor_id==ui[3]
    window.select_effect_layers_with_modifiers(ui[1]);window.select_effect_layers_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier)
    secondary=next(item for item in layers if item.id==ui[1]);before=secondary.layer_transform.position_x;primary=next(item for item in layers if item.id==ui[3]);changed=type(primary.layer_transform).from_dict(primary.layer_transform.to_dict());changed.position_x=42;window.update_resource_layer_transform(primary.id,changed)
    assert next(item for item in window.project.effect_resource_layers if item.id==primary.id).layer_transform.position_x==42 and secondary.layer_transform.position_x==before
    window.application_undo_stack.clear();window.select_all_effect_layers();assert window.selected_effect_layer_ids==set(ui) and window.primary_effect_layer_id==ui[3] and window.application_undo_stack.count()==0
    close(window)

def test_resource_multiselect_auto_key_and_locked_edit_target_primary_only(tmp_path):
    editor,stack,_,composition=resource_editor(tmp_path);ui=[item.id for item in reversed(composition.layers)];secondary=next(item for item in composition.layers if item.id==ui[1]);primary=next(item for item in composition.layers if item.id==ui[3])
    for layer in (secondary,primary):layer.add_property("rotation").set_keyframe(0,0)
    editor.select_layer_with_modifiers(secondary.id);editor.select_layer_with_modifiers(primary.id,Qt.KeyboardModifier.ControlModifier);editor.set_frame(1);stack.clear();editor._property_value("rotation",90)
    assert primary.tracks["rotation"].keyframe_at(1).value==90 and not secondary.tracks["rotation"].has_keyframe(1) and stack.count()==1
    primary.locked=True;stack.clear();editor._property_value("rotation",180);assert primary.tracks["rotation"].keyframe_at(1).value==90 and not secondary.tracks["rotation"].has_keyframe(1) and stack.count()==0
    editor.close()
