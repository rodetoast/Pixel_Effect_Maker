import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget

APP=QApplication.instance() or QApplication([])

def _project():
    project=Project.create_default(width=4,height=4,frame_count=2);pixels=np.zeros((2,2,4),dtype=np.uint8);pixels[:]=[255,255,255,255];asset=SourceAsset("A",pixels);composition=ResourceComposition("C",4,4,12,2,layers=[CompositionLayer("A","source_asset",asset.id,0,1)]);project.source_assets=[asset];project.resource_compositions=[composition];return project,composition

def test_resource_lock_undo_noop_and_mutation_guards(tmp_path):
    project,composition=_project();layer=composition.layers[0];editor=ResourceEditorWidget(QSettings(str(tmp_path/"r.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,layer.id)
    assert editor.set_layer_locked(layer.id,True) and layer.locked and stack.count()==1;stack.undo();assert not layer.locked;stack.redo();assert layer.locked
    revision=composition.revision;count=stack.count();assert not editor.set_layer_locked(layer.id,True);editor.set_keyframe("rotation",90);assert not editor.remove_layer(layer.id) and not editor.move_layer(layer.id,1) and not editor.reorder_layer(layer.id,0)
    assert composition.revision==revision and stack.count()==count and editor.set_layer_solo(layer.id,True) and layer.solo
    duplicate=editor.duplicate_layer(layer.id);assert duplicate.locked and duplicate.solo and duplicate.id!=layer.id
    editor.close()

def test_effect_lock_blocks_settings_delete_reorder_but_allows_solo_duplicate_and_undo(tmp_path):
    project,composition=_project();settings=QSettings(str(tmp_path/"e.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);layer=window.create_resource_layer_from_resource(composition.id);window.application_undo_stack.clear();window.application_undo_stack.setClean()
    assert window.set_resource_layer_locked(layer.id,True) and layer.locked;count=window.application_undo_stack.count();before=layer.layer_transform.to_dict();changed=type(layer.layer_transform).from_dict(before);changed.position_x=99
    window.update_resource_layer_transform(layer.id,changed);window.set_resource_layer_mode(layer.id,"particle");assert not window.remove_resource_layer(layer.id) and not window.reorder_resource_layer_to_ui_index(layer.id,0)
    assert layer.layer_transform.to_dict()==before and layer.placement_mode=="single" and window.application_undo_stack.count()==count
    assert window.set_resource_layer_solo(layer.id,True);duplicate=window.duplicate_resource_layer(layer.id);assert duplicate.locked and duplicate.solo and duplicate.generated_layer_id!=layer.generated_layer_id
    window.application_undo_stack.undo();assert duplicate not in window.project.effect_resource_layers
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()
