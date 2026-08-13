from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import QSettings,Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget
import numpy as np

from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset

APP=QApplication.instance() or QApplication([])

def project_with_layers(count=5):
    project=Project.create_default(width=4,height=4,frame_count=2);composition=ResourceComposition("C",4,4,12,2)
    for index in range(count):
        pixels=np.zeros((2,2,4),dtype=np.uint8);pixels[:]=[index*30,20,255-index*30,255];asset=SourceAsset(chr(65+index),pixels);project.source_assets.append(asset);composition.layers.append(CompositionLayer(asset.name,"source_asset",asset.id,0,1))
    project.resource_compositions=[composition];return project,composition

def resource(tmp_path):
    project,composition=project_with_layers();editor=ResourceEditorWidget(QSettings(str(tmp_path/"r.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,composition.layers[-1].id);return editor,stack,project,composition

def effect(tmp_path):
    project,_=project_with_layers();project.resource_compositions=[]
    from app.models.resource_composition import CompositionLayer,ResourceComposition
    for asset in project.source_assets:project.resource_compositions.append(ResourceComposition(asset.name,4,4,12,2,layers=[CompositionLayer(asset.name,"source_asset",asset.id,0,1)]))
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"e.ini"),QSettings.Format.IniFormat)),initial_project=project);layers=[window.create_resource_layer_from_resource(item.id) for item in project.resource_compositions];window.application_undo_stack.clear();return window,layers

def close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()

def test_resource_batch_state_commands_are_one_undo_and_locked_mixed_policy(tmp_path):
    editor,stack,_,composition=resource(tmp_path);ui=[item.id for item in reversed(composition.layers)];editor.select_layer_with_modifiers(ui[1]);editor.select_layer_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier)
    assert editor.set_selected_layer_state("locked",True) and stack.count()==1 and all(item.locked for item in composition.layers if item.id in {ui[1],ui[3]});stack.undo();assert not any(item.locked for item in composition.layers if item.id in {ui[1],ui[3]});stack.redo()
    count=stack.count();before=[item.id for item in composition.layers];assert not editor.delete_selected_layers() and not editor.reorder_layers(editor.selected_layer_ids,0) and [item.id for item in composition.layers]==before and stack.count()==count
    assert editor.set_selected_layer_state("solo",True) and editor.set_selected_layer_state("visible",False);assert all(item.solo and not item.visible for item in composition.layers if item.id in editor.selected_layer_ids)
    editor.close()

def test_resource_batch_duplicate_drag_front_back_delete_restore_selection(tmp_path):
    editor,stack,_,composition=resource(tmp_path);ui=[item.id for item in reversed(composition.layers)];selected={ui[1],ui[3]};editor.select_layer_with_modifiers(ui[1]);editor.select_layer_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier);original=deepcopy(editor.layer_selection.snapshot());duplicates=editor.duplicate_selected_layers();duplicate_ids={item.id for item in duplicates}
    assert len(duplicates)==2 and stack.count()==1 and editor.selected_layer_ids==duplicate_ids and len({item.name for item in composition.layers})==len(composition.layers)
    stack.undo();assert editor.layer_selection.snapshot()==original;stack.redo();assert editor.selected_layer_ids==duplicate_ids
    stack.clear();assert editor.move_selected_to_edge(True) and stack.count()==1;assert editor._ui_layer_ids()[:2]==editor.layer_selection.ordered(editor._ui_layer_ids())
    stack.clear();assert editor.move_selected_to_edge(False) and stack.count()==1;assert editor._ui_layer_ids()[-2:]==editor.layer_selection.ordered(editor._ui_layer_ids())
    stack.clear();before_ids=[item.id for item in composition.layers];assert editor.delete_selected_layers() and stack.count()==1;stack.undo();assert [item.id for item in composition.layers]==before_ids and editor.selected_layer_ids==duplicate_ids
    editor.close()

def test_effect_batch_duplicate_state_reorder_and_delete_are_single_undo(tmp_path):
    window,layers=effect(tmp_path);ui=window._effect_ui_ids();window.select_effect_layers_with_modifiers(ui[1]);window.select_effect_layers_with_modifiers(ui[3],Qt.KeyboardModifier.ControlModifier);original=window.effect_layer_selection.snapshot();duplicates=window.duplicate_selected_effect_layers();duplicate_ids={item.id for item in duplicates}
    assert len(duplicates)==2 and window.application_undo_stack.count()==1 and all(item.generated_layer_id for item in duplicates) and len({item.generated_layer_id for item in window.project.effect_resource_layers})==len(window.project.effect_resource_layers)
    window.application_undo_stack.undo();assert window.effect_layer_selection.snapshot()==original;window.application_undo_stack.redo();assert window.selected_effect_layer_ids==duplicate_ids
    window.application_undo_stack.clear();assert window.set_selected_effect_state("solo",True) and window.application_undo_stack.count()==1
    window.application_undo_stack.clear();assert window.move_selected_effect_to_edge(True) and window.application_undo_stack.count()==1
    window.application_undo_stack.clear();before=[item.id for item in window.project.effect_resource_layers];assert window.delete_selected_effect_layers() and window.application_undo_stack.count()==1;window.application_undo_stack.undo();assert [item.id for item in window.project.effect_resource_layers]==before and window.selected_effect_layer_ids==duplicate_ids
    close(window)

def test_effect_locked_mixed_rejects_structural_batch_but_allows_duplicate_solo_visibility(tmp_path):
    window,layers=effect(tmp_path);ui=window._effect_ui_ids();window.select_effect_layers_with_modifiers(ui[0]);window.select_effect_layers_with_modifiers(ui[2],Qt.KeyboardModifier.ControlModifier);next(item for item in window.project.effect_resource_layers if item.id==ui[0]).locked=True;before=[item.id for item in window.project.effect_resource_layers]
    assert not window.delete_selected_effect_layers() and not window.reorder_selected_effect_layers(window.selected_effect_layer_ids,0) and window.application_undo_stack.count()==0 and [item.id for item in window.project.effect_resource_layers]==before
    assert len(window.duplicate_selected_effect_layers())==2;window.application_undo_stack.clear();assert window.set_selected_effect_state("solo",True);window.application_undo_stack.clear();assert window.set_selected_effect_state("visible",False)
    close(window)
