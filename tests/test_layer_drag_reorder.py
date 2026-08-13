from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QMimeData,QPointF,QSettings,Qt
from PySide6.QtGui import QDropEvent,QUndoStack
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE,PLACEMENT_SINGLE
from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.project_io import load_project,save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget


APP=QApplication.instance() or QApplication([])


def _resources():
    project=Project.create_default(width=12,height=12,frame_count=3);assets=[]
    for index,name in enumerate("ABCDE"):
        pixels=np.zeros((6,6,4),dtype=np.uint8);pixels[1:5,1:5]=([255,30,30,255],[30,255,30,192],[30,30,255,255],[255,255,30,180],[255,30,255,255])[index];asset=SourceAsset(name,pixels);project.source_assets.append(asset);assets.append(asset)
    composition=ResourceComposition("Five",6,6,12,3,True);composition.layers=[CompositionLayer(item.name,"source_asset",item.id,0,2) for item in assets];project.resource_compositions.append(composition);return project,composition,assets


def _editor(tmp_path):
    project,composition,assets=_resources();editor=ResourceEditorWidget(QSettings(str(tmp_path/"drag.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,composition.layers[-1].id);return editor,stack,project,composition,assets


def _window(tmp_path):
    project,_,assets=_resources();project.resource_compositions=[];resources=[]
    for asset in assets:
        composition=ResourceComposition(asset.name,6,6,12,3,True);composition.layers.append(CompositionLayer(asset.name,"source_asset",asset.id,0,2));project.resource_compositions.append(composition);resources.append(composition)
    settings=QSettings(str(tmp_path/"effect-drag.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);layers=[]
    for index,resource in enumerate(resources):
        mode=PLACEMENT_SINGLE if index%2==0 else PLACEMENT_PARTICLE;layer=window.create_resource_layer_from_resource(resource.id,mode);layer.particle_settings.motion.mode=("linear","orbit","helix")[index%3];layers.append(layer)
    window.application_undo_stack.clear();window.application_undo_stack.setClean();return window,layers


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


def test_resource_drag_bottom_to_top_is_one_undo_selection_safe_and_round_trips(tmp_path):
    editor,stack,project,composition,_=_editor(tmp_path);original=[item.id for item in composition.layers];snapshots={item.id:deepcopy(item.to_dict()) for item in composition.layers};back=composition.layers[0]
    assert editor.reorder_layer(back.id,0) and [item.id for item in composition.layers]==original[1:]+original[:1] and editor.selected_layer.id==back.id and stack.count()==1
    assert [item.id for item,prop in editor.composition_timeline.rows if prop is None][0]==back.id
    assert all(item.to_dict()==snapshots[item.id] for item in composition.layers)
    stack.undo();assert [item.id for item in composition.layers]==original
    stack.redo();assert [item.id for item in composition.layers]==original[1:]+original[:1]
    loaded=load_project(save_project(project,tmp_path/"resource-order.peffect.json"));assert [item.id for item in loaded.resource_compositions[0].layers]==original[1:]+original[:1]
    editor.close()


def test_resource_noop_drop_has_no_revision_undo_or_mutation(tmp_path):
    editor,stack,_,composition,_=_editor(tmp_path);front=composition.layers[-1];before=deepcopy(composition.to_dict());revision=composition.revision
    assert not editor.reorder_layer(front.id,0) and composition.to_dict()==before and composition.revision==revision and stack.count()==0
    editor.close()

def test_locked_resource_and_effect_sources_cannot_reorder(tmp_path):
    editor,stack,_,composition,_=_editor(tmp_path);source=composition.layers[0];source.locked=True;before=[item.id for item in composition.layers];revision=composition.revision
    assert not editor.reorder_layer(source.id,0) and [item.id for item in composition.layers]==before and composition.revision==revision and stack.count()==0
    window,layers=_window(tmp_path);source=layers[0];source.locked=True;before=[item.id for item in window.project.effect_resource_layers]
    assert not window.reorder_resource_layer_to_ui_index(source.id,0) and [item.id for item in window.project.effect_resource_layers]==before and window.application_undo_stack.count()==0
    editor.close();_close(window)


def test_effect_drag_bottom_to_top_updates_composite_once_and_undoes_once(tmp_path,monkeypatch):
    window,layers=_window(tmp_path);original=[item.id for item in window.project.effect_resource_layers];back=layers[0];before,_=render_exact_playback_frame(window.project,0);refreshes=[];real=window._refresh_all;monkeypatch.setattr(window,"_refresh_all",lambda:refreshes.append(1) or real())
    assert window.reorder_resource_layer_to_ui_index(back.id,0);after,_=render_exact_playback_frame(window.project,0)
    assert [item.id for item in window.project.effect_resource_layers]==original[1:]+original[:1] and window.effect_library.current_composition_id()==back.id
    assert window.application_undo_stack.count()==1 and refreshes==[1] and not np.array_equal(before,after)
    window.application_undo_stack.undo();assert [item.id for item in window.project.effect_resource_layers]==original
    window.application_undo_stack.redo();assert [item.id for item in window.project.effect_resource_layers]==original[1:]+original[:1]
    _close(window)


def test_effect_noop_drop_has_no_dirty_undo_render_or_revision(tmp_path,monkeypatch):
    window,layers=_window(tmp_path);front=layers[-1];before=[item.to_dict() for item in window.project.effect_resource_layers];revision=window._project_edit_revision;refreshes=[];monkeypatch.setattr(window,"_refresh_all",lambda:refreshes.append(1))
    assert not window.reorder_resource_layer_to_ui_index(front.id,0)
    assert [item.to_dict() for item in window.project.effect_resource_layers]==before and window.application_undo_stack.count()==0 and window._project_edit_revision==revision and not window.dirty and refreshes==[]
    _close(window)


def test_effect_drag_mixed_modes_order_selection_and_save_reload(tmp_path):
    window,layers=_window(tmp_path);original=[item.id for item in layers];target=layers[1]
    assert window.reorder_resource_layer_to_ui_index(target.id,0);expected=[original[0],original[2],original[3],original[4],original[1]]
    assert [item.id for item in window.project.effect_resource_layers]==expected and {item.placement_mode for item in window.project.effect_resource_layers}=={PLACEMENT_SINGLE,PLACEMENT_PARTICLE}
    window.effect_library.refresh(window.project);assert str(window.effect_library.composition_list.item(0).data(256))==target.id
    loaded=load_project(save_project(window.project,tmp_path/"effect-order.peffect.json"));assert [item.id for item in loaded.effect_resource_layers]==expected
    _close(window)


def test_duplicate_buttons_and_list_focused_ctrl_d_emit_selected_identity(tmp_path):
    editor,stack,_,composition,_=_editor(tmp_path);resource_events=[];selected=editor.selected_layer.id;editor.composition_timeline.duplicate_layer_requested.connect(resource_events.append);editor.composition_timeline.duplicate_layer.click();first_copy=editor.selected_layer.id;QTest.keyClick(editor.composition_timeline.table,Qt.Key.Key_D,Qt.KeyboardModifier.ControlModifier)
    assert resource_events==[selected,first_copy] and [item.name for item in composition.layers[-3:]]==["E","E (2)","E (3)"] and stack.count()==2
    window,layers=_window(tmp_path);effect_events=[];window.select_resource_layer(layers[-1].id);selected=layers[-1].id;window.effect_library.duplicate_resource_layer_requested.connect(effect_events.append);window.effect_library.duplicate_composition_button.click();first_copy=window._selected_resource_layer().id;QTest.keyClick(window.effect_library.composition_list,Qt.Key.Key_D,Qt.KeyboardModifier.ControlModifier)
    assert effect_events==[selected,first_copy] and [item.name for item in window.project.effect_resource_layers[-3:]]==["E","E (2)","E (3)"] and window.application_undo_stack.count()==2
    editor.close();_close(window)


def test_real_drop_commit_signals_reorder_each_list_once(tmp_path):
    editor,stack,_,composition,_=_editor(tmp_path);back=composition.layers[0];mime=QMimeData();mime.setData(editor.composition_timeline.table.MIME,back.id.encode());event=QDropEvent(QPointF(2,0),Qt.DropAction.MoveAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier);editor.composition_timeline.table.dropEvent(event)
    assert composition.layers[-1].id==back.id and stack.count()==1 and event.isAccepted()
    window,layers=_window(tmp_path);back=layers[0];window.effect_library.refresh(window.project);mime=QMimeData();mime.setData(window.effect_library.composition_list.MIME,back.id.encode());event=QDropEvent(QPointF(2,0),Qt.DropAction.MoveAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier);window.effect_library.composition_list.dropEvent(event)
    assert window.project.effect_resource_layers[-1].id==back.id and window.application_undo_stack.count()==1 and event.isAccepted()
    editor.close();_close(window)
