from __future__ import annotations

from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings,Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.layer_group import LayerGroup,group_node,layer_node
from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget
from app.ui.timeline_multi_key import TimelineKey


APP=QApplication.instance() or QApplication([])


def _resource_project(frame_count=12):
    project=Project.create_default(width=8,height=8,frame_count=frame_count);composition=ResourceComposition("Keys",8,8,12,frame_count)
    for name in ("A","B"):
        asset=SourceAsset(name,np.full((3,3,4),255,dtype=np.uint8));layer=CompositionLayer(name,"source_asset",asset.id,0,frame_count-1);project.source_assets.append(asset);composition.layers.append(layer)
    composition.layers[0].add_property("rotation");composition.layers[1].add_property("opacity")
    for frame,value in ((1,0),(4,720),(8,1080)):composition.layers[0].tracks["rotation"].set_keyframe(frame,value,"Linear")
    for frame,value in ((2,.2),(7,.7),(10,1)):composition.layers[1].tracks["opacity"].set_keyframe(frame,value,"Ease In")
    project.resource_compositions=[composition];return project,composition


def _resource_editor(tmp_path):
    project,composition=_resource_project();editor=ResourceEditorWidget(QSettings(str(tmp_path/"resource.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,composition.layers[0].id);return editor,stack,project,composition


def test_resource_multi_key_move_collision_delete_easing_and_undo(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);a,b=composition.layers;keys={TimelineKey(a.id,"resource","rotation",1),TimelineKey(a.id,"resource","rotation",4),TimelineKey(b.id,"resource","opacity",2)};before_parent=(a.parent_id,a.parent_offset);before_value=a.tracks["rotation"].keyframe_at(4).value
    editor.composition_timeline.key_selection.selected=set(keys);editor.composition_timeline.key_selection.primary=next(iter(keys));assert editor.move_selected_keys(keys,2);assert stack.count()==1 and [key.frame for key in a.tracks["rotation"].keyframes]==[3,6,8] and [key.frame for key in b.tracks["opacity"].keyframes]==[4,7,10]
    assert a.tracks["rotation"].keyframe_at(6).value==before_value and (a.parent_id,a.parent_offset)==before_parent and FORMAT_VERSION==19
    stack.undo();assert [key.frame for key in a.tracks["rotation"].keyframes]==[1,4,8];stack.redo();assert [key.frame for key in a.tracks["rotation"].keyframes]==[3,6,8]
    snapshot=deepcopy(composition.to_dict());count=stack.count();blocked={TimelineKey(a.id,"resource","rotation",3),TimelineKey(a.id,"resource","rotation",6)};assert not editor.move_selected_keys(blocked,2) and composition.to_dict()==snapshot and stack.count()==count
    easing={TimelineKey(a.id,"resource","rotation",3),TimelineKey(b.id,"resource","opacity",4)};assert editor.set_selected_keys_easing(easing,"Ease In/Out") and stack.count()==count+1;assert a.tracks["rotation"].keyframe_at(3).easing==b.tracks["opacity"].keyframe_at(4).easing=="Ease In/Out"
    assert not editor.set_selected_keys_easing(easing,"Ease In/Out")
    assert editor.delete_selected_keys(easing);assert a.tracks["rotation"].keyframe_at(3) is None and b.tracks["opacity"].keyframe_at(4) is None;stack.undo();assert a.tracks["rotation"].keyframe_at(3) and b.tracks["opacity"].keyframe_at(4);editor.close()


def test_resource_last_key_delete_preserves_static_value_in_one_undo(tmp_path):
    editor,stack,_,composition=_resource_editor(tmp_path);layer=composition.layers[0];track=layer.tracks["rotation"];keys={TimelineKey(layer.id,"resource","rotation",key.frame) for key in track.keyframes};assert editor.delete_selected_keys(keys);track=layer.tracks["rotation"];assert not track.keyframes and track.default_value==1080 and stack.count()==1;stack.undo();track=layer.tracks["rotation"];assert [(key.frame,key.value) for key in track.keyframes]==[(1,0),(4,720),(8,1080)];editor.close()


def test_resource_key_click_ctrl_shift_and_marquee_do_not_mutate_project(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(1100,700);editor.show();APP.processEvents();before=deepcopy(project.to_dict());rows={(layer.id,prop):index for index,(layer,prop) in enumerate(timeline.rows) if prop};a,b=composition.layers;row_a=rows[(a.id,"rotation")];row_b=rows[(b.id,"opacity")]
    def point(row,frame):return timeline.table.visualItemRect(timeline.table.item(row,frame)).center()
    QTest.mouseClick(timeline.table.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point(row_a,1));QTest.mouseClick(timeline.table.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier,point(row_b,2));assert len(timeline.key_selection.selected)==2 and timeline.key_selection.primary==TimelineKey(b.id,"resource","opacity",2)
    QTest.mouseClick(timeline.table.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point(row_a,1));QTest.mouseClick(timeline.table.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ShiftModifier,point(row_a,8));assert {key.frame for key in timeline.key_selection.selected}=={1,4,8}
    start=point(row_a,0);end=point(row_b,7);QTest.mousePress(timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(timeline.table.viewport(),end,20);QTest.mouseRelease(timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=end);APP.processEvents();assert {key.frame for key in timeline.key_selection.selected}=={1,2,4,7};assert project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_collapse_repairs_hidden_key_selection_without_data_change(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);layer=composition.layers[0];group=LayerGroup("G",children=[layer.id]);composition.groups=[group];composition.root_order=[group_node(group.id),layer_node(composition.layers[1].id)];composition.sync_flat_order();editor.expanded_group_ids={group.id};editor._apply_state(editor.controller.state);key=TimelineKey(layer.id,"resource","rotation",1);editor.composition_timeline.key_selection.selected={key};editor.composition_timeline.key_selection.primary=key;before=deepcopy(project.to_dict());editor.set_all_groups_expanded(False);assert not editor.composition_timeline.key_selection.selected and project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_alt_arrow_nudge_and_escape_are_safe(tmp_path):
    editor,stack,_,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;layer=composition.layers[0];key=TimelineKey(layer.id,"resource","rotation",1);timeline.key_selection.selected={key};timeline.key_selection.primary=key;timeline.table.setFocus();QTest.keyClick(timeline.table,Qt.Key.Key_Right,Qt.KeyboardModifier.AltModifier);APP.processEvents();assert layer.tracks["rotation"].keyframe_at(2) and stack.count()==1
    moved=TimelineKey(layer.id,"resource","rotation",2);timeline.key_selection.selected={moved};timeline.key_selection.primary=moved;timeline._key_drag=(moved,2,timeline.table.viewport().rect().center(),True);QTest.keyClick(timeline.table,Qt.Key.Key_Escape);assert timeline._key_drag is None and stack.count()==1;editor.close()


def test_resource_drag_preview_marks_collision_without_mutating(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(1000,700);editor.show();APP.processEvents();layer=composition.layers[0];keys={TimelineKey(layer.id,"resource","rotation",1),TimelineKey(layer.id,"resource","rotation",4)};timeline.key_selection.selected=keys;timeline.key_selection.primary=next(iter(keys));row=next(index for index,(current,prop) in enumerate(timeline.rows) if current.id==layer.id and prop=="rotation");target_x=timeline.table.visualItemRect(timeline.table.item(row,5)).center().x();before=deepcopy(project.to_dict());timeline._preview_key_drag(1,target_x);assert timeline.table.viewport().cursor().shape()==Qt.CursorShape.ForbiddenCursor and "Collision" in timeline.key_selection_status.text() and project.to_dict()==before and stack.count()==0;timeline._cancel_key_gesture();assert timeline.table.item(row,1).text() in {"◆","⬥"};editor.close()


def _effect_window(tmp_path):
    project,composition=_resource_project(24);settings=QSettings(str(tmp_path/"effect.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);single=window.create_resource_layer_from_resource(composition.id);particle=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);single.layer_transform.set_keyframe("rotation_z",1,0);single.layer_transform.set_keyframe("rotation_z",5,720);single.layer_transform.set_keyframe("rotation_z",12,1080);particle.particle_settings.motion.set_keyframe("radius_end",2,4);particle.particle_settings.motion.set_keyframe("radius_end",8,12);particle.particle_settings.motion.set_keyframe("radius_end",16,20);window.application_undo_stack.clear();window._refresh_all();return window,single,particle


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


def test_effect_multi_key_uses_logical_identity_and_preserves_generated_mapping(tmp_path):
    window,single,particle=_effect_window(tmp_path);single.parent_id=particle.id;single.parent_offset=(1,0,3,0,1,4,0,0,1);generated=[layer.generated_layer_id for layer in window.project.effect_resource_layers];parent=(single.parent_id,single.parent_offset);keys={TimelineKey(single.id,"effect_transform","rotation_z",1),TimelineKey(single.id,"effect_transform","rotation_z",5),TimelineKey(particle.id,"effect_motion","radius_end",2)};before=window.application_undo_stack.count();assert window.move_effect_selected_keys(keys,3);assert window.application_undo_stack.count()==before+1;assert [key.frame for key in single.layer_transform.tracks["rotation_z"].keyframes]==[4,8,12];assert [key.frame for key in particle.particle_settings.motion.tracks["radius_end"].keyframes]==[5,8,16];assert single.layer_transform.tracks["rotation_z"].keyframe_at(8).value==720;assert [layer.generated_layer_id for layer in window.project.effect_resource_layers]==generated and (single.parent_id,single.parent_offset)==parent
    window.application_undo_stack.undo();single=next(layer for layer in window.project.effect_resource_layers if layer.id==single.id);assert [key.frame for key in single.layer_transform.tracks["rotation_z"].keyframes]==[1,5,12];window.application_undo_stack.redo();single=next(layer for layer in window.project.effect_resource_layers if layer.id==single.id);assert [key.frame for key in single.layer_transform.tracks["rotation_z"].keyframes]==[4,8,12];assert not any(row.get("kind")=="group" for row in window.timeline.rows);_close(window)


def test_effect_delete_and_easing_are_atomic_one_command(tmp_path):
    window,single,particle=_effect_window(tmp_path);keys={TimelineKey(single.id,"effect_transform","rotation_z",1),TimelineKey(particle.id,"effect_motion","radius_end",2)};assert window.set_effect_selected_keys_easing(keys,"Ease Out");assert window.application_undo_stack.count()==1;assert single.layer_transform.tracks["rotation_z"].keyframe_at(1).easing==particle.particle_settings.motion.tracks["radius_end"].keyframe_at(2).easing=="Ease Out";assert not window.set_effect_selected_keys_easing(keys,"Ease Out");assert window.delete_effect_selected_keys(keys);assert window.application_undo_stack.count()==2;window.application_undo_stack.undo();single=next(layer for layer in window.project.effect_resource_layers if layer.id==single.id);particle=next(layer for layer in window.project.effect_resource_layers if layer.id==particle.id);assert single.layer_transform.tracks["rotation_z"].keyframe_at(1) and particle.particle_settings.motion.tracks["radius_end"].keyframe_at(2);_close(window)


def test_effect_collision_rejects_whole_move_without_undo(tmp_path):
    window,single,_particle=_effect_window(tmp_path);keys={TimelineKey(single.id,"effect_transform","rotation_z",1),TimelineKey(single.id,"effect_transform","rotation_z",5)};before=deepcopy(window.project.to_dict());count=window.application_undo_stack.count();assert not window.move_effect_selected_keys(keys,7);assert window.project.to_dict()==before and window.application_undo_stack.count()==count;_close(window)


def test_effect_key_selection_is_runtime_and_keeps_layer_multiselection(tmp_path):
    window,single,particle=_effect_window(tmp_path);window.select_effect_layers_with_modifiers(single.id,Qt.KeyboardModifier.NoModifier);window.select_effect_layers_with_modifiers(particle.id,Qt.KeyboardModifier.ControlModifier);layer_selection=set(window.effect_layer_selection.selected_ids);window.dirty=False;before=deepcopy(window.project.to_dict());before_undo=window.application_undo_stack.count();window.show();APP.processEvents();row=next(index for index,value in enumerate(window.timeline.rows) if value.get("kind")=="property" and value.get("logical").id==single.id and value.get("property_id")=="rotation_z");item=window.timeline.table.item(row,window.timeline.FRAME_COLUMN_OFFSET+1);QTest.mouseClick(window.timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=window.timeline.table.visualItemRect(item).center());APP.processEvents();assert window.timeline.key_selection.primary==TimelineKey(single.id,"effect_transform","rotation_z",1);assert window.effect_layer_selection.selected_ids==layer_selection and window.project.to_dict()==before and window.application_undo_stack.count()==before_undo and not window.dirty;_close(window)


def test_multi_key_save_reload_preserves_frames_values_easing_not_selection(tmp_path):
    editor,_,project,composition=_resource_editor(tmp_path);layer=composition.layers[0];keys={TimelineKey(layer.id,"resource","rotation",1),TimelineKey(layer.id,"resource","rotation",4)};assert editor.move_selected_keys(keys,2);moved={key.at_frame(key.frame+2) for key in keys};assert editor.set_selected_keys_easing(moved,"Ease In/Out");payload=project.to_dict();loaded=Project.from_dict(payload);track=loaded.resource_compositions[0].layers[0].tracks["rotation"];assert [(key.frame,key.value,key.easing) for key in track.keyframes]==[(3,0,"Ease In/Out"),(6,720,"Ease In/Out"),(8,1080,"Linear")];assert "key_selection" not in str(payload) and FORMAT_VERSION==19;editor.close()
