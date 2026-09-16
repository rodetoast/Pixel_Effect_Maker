from __future__ import annotations

from copy import deepcopy
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import QMimeData,QSettings,Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QComboBox,QLineEdit,QSpinBox
import pytest

from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import AnimationTrack
from app.models.layer_group import LayerGroup,group_node,layer_node
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget
from app.ui.timeline_multi_key import (
    PASTE_COLLISION,PASTE_INCOMPATIBLE,PASTE_INVALID,PASTE_MISSING_TRACK,PASTE_OUT_OF_RANGE,
    TIMELINE_KEY_MIME,TimelineKey,build_timeline_clipboard_payload,
    decode_timeline_clipboard_payload,paste_timeline_keys_atomic,
)

from tests.test_timeline_multi_key_editing import _close,_effect_window,_resource_project


APP=QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _release_clipboard_after_test():
    yield
    APP.clipboard().clear()


def _resource_editor(tmp_path,frame_count=24):
    project,composition=_resource_project(frame_count);editor=ResourceEditorWidget(QSettings(str(tmp_path/"clipboard.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,composition.layers[0].id);return editor,stack,project,composition


def _selected_resource_keys(composition):
    a,b=composition.layers
    return {TimelineKey(a.id,"resource","rotation",1),TimelineKey(a.id,"resource","rotation",4),TimelineKey(b.id,"resource","opacity",2)}


def test_payload_preserves_relative_frames_values_easing_and_primary():
    rotation=AnimationTrack("rotation",0.0);rotation.set_keyframe(5,720,"Ease In");rotation.set_keyframe(8,1080,"Ease Out");opacity=AnimationTrack("opacity",1.0);opacity.set_keyframe(6,.5,"Ease In/Out");tracks={("a","resource","rotation"):rotation,("b","resource","opacity"):opacity};keys={TimelineKey("a","resource","rotation",5),TimelineKey("a","resource","rotation",8),TimelineKey("b","resource","opacity",6)};primary=TimelineKey("a","resource","rotation",8)
    data=build_timeline_clipboard_payload("resource","ctx",keys,tracks,primary);payload=decode_timeline_clipboard_payload(data);assert payload and [entry["relative_frame"] for entry in payload["entries"]]==[0,1,3]
    destination={("a","resource","rotation"):AnimationTrack("rotation",0.0),("b","resource","opacity"):AnimationTrack("opacity",1.0)};issue,pasted,pasted_primary=paste_timeline_keys_atomic(destination,payload,"resource","ctx",12,24);assert issue is None and {key.frame for key in pasted}=={12,13,15} and pasted_primary==TimelineKey("a","resource","rotation",15);assert [(key.frame,key.value,key.easing) for key in destination[("a","resource","rotation")].keyframes]==[(12,720,"Ease In"),(15,1080,"Ease Out")]


def test_payload_validation_rejects_corrupt_unknown_duplicate_and_non_finite_data():
    valid={"version":1,"timeline_kind":"resource","context_id":"ctx","anchor_frame":1,"primary_index":None,"entries":[{"layer_id":"a","scope":"resource","property_id":"rotation","relative_frame":0,"value":1.0,"easing":"Linear"}]}
    assert decode_timeline_clipboard_payload(b"not-json") is None
    changed=deepcopy(valid);changed["version"]=99;assert decode_timeline_clipboard_payload(json.dumps(changed).encode()) is None
    changed=deepcopy(valid);changed["entries"][0]["value"]=float("nan");assert decode_timeline_clipboard_payload(json.dumps(changed).encode()) is None
    changed=deepcopy(valid);changed["entries"][0]["relative_frame"]=-1;assert decode_timeline_clipboard_payload(json.dumps(changed).encode()) is None
    changed=deepcopy(valid);changed["entries"]*=2;assert decode_timeline_clipboard_payload(json.dumps(changed).encode()) is None
    assert paste_timeline_keys_atomic({},changed,"resource","ctx",0,12)[0]==PASTE_INVALID


def test_atomic_paste_rejects_context_missing_track_collision_and_boundary():
    source=AnimationTrack("rotation",0.0);source.set_keyframe(1,720);source.set_keyframe(4,1080);keyset={TimelineKey("a","resource","rotation",1),TimelineKey("a","resource","rotation",4)};payload=decode_timeline_clipboard_payload(build_timeline_clipboard_payload("resource","ctx",keyset,{("a","resource","rotation"):source}))
    empty=AnimationTrack("rotation",0.0);assert paste_timeline_keys_atomic({("a","resource","rotation"):empty},payload,"effect","ctx",5,20)[0]==PASTE_INCOMPATIBLE;assert not empty.keyframes
    assert paste_timeline_keys_atomic({},payload,"resource","ctx",5,20)[0]==PASTE_MISSING_TRACK
    occupied=AnimationTrack("rotation",0.0);occupied.set_keyframe(8,1);before=deepcopy(occupied);assert paste_timeline_keys_atomic({("a","resource","rotation"):occupied},payload,"resource","ctx",5,20)[0]==PASTE_COLLISION and occupied==before
    empty=AnimationTrack("rotation",0.0);assert paste_timeline_keys_atomic({("a","resource","rotation"):empty},payload,"resource","ctx",18,20)[0]==PASTE_OUT_OF_RANGE and not empty.keyframes


def test_resource_copy_paste_uses_playhead_selects_keys_and_is_one_stable_undo(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);keys=_selected_resource_keys(composition);timeline=editor.composition_timeline;timeline.key_selection.selected=set(keys);timeline.key_selection.primary=TimelineKey(composition.layers[0].id,"resource","rotation",4);before=deepcopy(project.to_dict());revision=composition.revision
    assert editor.copy_selected_keys() and project.to_dict()==before and composition.revision==revision and stack.count()==0 and timeline.key_selection.selected==keys
    editor.set_frame(12);assert editor.paste_copied_keys() and stack.count()==1;expected={TimelineKey(composition.layers[0].id,"resource","rotation",12),TimelineKey(composition.layers[0].id,"resource","rotation",15),TimelineKey(composition.layers[1].id,"resource","opacity",13)};assert timeline.key_selection.selected==expected and timeline.key_selection.primary==TimelineKey(composition.layers[0].id,"resource","rotation",15)
    pasted={layer.id:deepcopy(layer.tracks) for layer in composition.layers};stack.undo();assert not (timeline.key_selection.selected&expected);APP.clipboard().setText("clipboard changed after paste");stack.redo();assert {layer.id:layer.tracks for layer in composition.layers}==pasted and stack.count()==1;editor.close()


def test_resource_paste_collision_and_overflow_are_atomic_noops(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);editor.composition_timeline.key_selection.selected=_selected_resource_keys(composition);assert editor.copy_selected_keys();before=deepcopy(project.to_dict());editor.set_frame(4);assert not editor.paste_copied_keys() and project.to_dict()==before and stack.count()==0;editor.set_frame(22);assert not editor.paste_copied_keys() and project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_timeline_ctrl_c_ctrl_v_uses_active_table_context(tmp_path):
    editor,stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;timeline.key_selection.selected=_selected_resource_keys(composition);timeline.key_selection.primary=TimelineKey(composition.layers[0].id,"resource","rotation",4);timeline.table.setFocus();QTest.keyClick(timeline.table,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier);editor.set_frame(12);timeline.table.setFocus();QTest.keyClick(timeline.table,Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier);APP.processEvents();assert stack.count()==1 and composition.layers[0].tracks["rotation"].keyframe_at(15).value==720;editor.close()


def test_resource_clipboard_rejects_other_composition_and_project_switch(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);editor.composition_timeline.key_selection.selected=_selected_resource_keys(composition);assert editor.copy_selected_keys();other_project,other_composition=_resource_project(24);editor.refresh(other_project);editor.controller.select_composition(other_composition.id,other_composition.layers[0].id);before=deepcopy(other_project.to_dict());assert not editor.paste_copied_keys() and other_project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_group_collapse_after_copy_pastes_model_keys_without_hidden_selection(tmp_path):
    editor,stack,_project,composition=_resource_editor(tmp_path);layer=composition.layers[0];group=LayerGroup("G",children=[layer.id]);composition.groups=[group];composition.root_order=[group_node(group.id),layer_node(composition.layers[1].id)];composition.sync_flat_order();editor.expanded_group_ids={group.id};editor._apply_state(editor.controller.state);key=TimelineKey(layer.id,"resource","rotation",1);editor.composition_timeline.key_selection.selected={key};editor.composition_timeline.key_selection.primary=key;assert editor.copy_selected_keys();editor.set_all_groups_expanded(False);editor.set_frame(12);assert editor.paste_copied_keys() and layer.tracks["rotation"].keyframe_at(12).value==0 and not editor.composition_timeline.key_selection.selected and stack.count()==1;editor.close()


def test_paste_rejects_layer_removed_after_copy(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);editor.composition_timeline.key_selection.selected={TimelineKey(composition.layers[0].id,"resource","rotation",1)};assert editor.copy_selected_keys();composition.layers.pop(0);before=deepcopy(project.to_dict());assert not editor.paste_copied_keys() and project.to_dict()==before and stack.count()==0;editor.close()


def test_effect_copy_paste_preserves_logical_tracks_values_and_redo(tmp_path):
    window,single,particle=_effect_window(tmp_path);keys={TimelineKey(single.id,"effect_transform","rotation_z",1),TimelineKey(single.id,"effect_transform","rotation_z",5),TimelineKey(particle.id,"effect_motion","radius_end",2)};window.timeline.key_selection.selected=set(keys);window.timeline.key_selection.primary=TimelineKey(single.id,"effect_transform","rotation_z",5);generated=[layer.generated_layer_id for layer in window.project.effect_resource_layers];window.dirty=False;before=deepcopy(window.project.to_dict())
    assert window.copy_effect_selected_keys() and window.project.to_dict()==before and window.application_undo_stack.count()==0 and not window.dirty;window.frame_index=13;assert window.paste_effect_copied_keys() and window.application_undo_stack.count()==1;expected={TimelineKey(single.id,"effect_transform","rotation_z",13),TimelineKey(single.id,"effect_transform","rotation_z",17),TimelineKey(particle.id,"effect_motion","radius_end",14)};assert window.timeline.key_selection.selected==expected and window.timeline.key_selection.primary==TimelineKey(single.id,"effect_transform","rotation_z",17);assert single.layer_transform.tracks["rotation_z"].keyframe_at(17).value==720 and particle.particle_settings.motion.tracks["radius_end"].keyframe_at(14).value==4 and [layer.generated_layer_id for layer in window.project.effect_resource_layers]==generated
    pasted=deepcopy(window.project.to_dict());window.application_undo_stack.undo();assert not (window.timeline.key_selection.selected&expected);APP.clipboard().setText("changed");window.application_undo_stack.redo();assert window.project.to_dict()==pasted;_close(window)


def test_resource_and_effect_clipboards_are_not_cross_paste_compatible(tmp_path):
    editor,_stack,project,composition=_resource_editor(tmp_path);editor.composition_timeline.key_selection.selected=_selected_resource_keys(composition);assert editor.copy_selected_keys();settings=QSettings(str(tmp_path/"cross.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings),initial_project=project);before=deepcopy(project.to_dict());assert not window.paste_effect_copied_keys() and project.to_dict()==before;_close(window);editor.close()


def test_effect_clipboard_is_rejected_by_resource_timeline(tmp_path):
    window,single,_particle=_effect_window(tmp_path);window.timeline.key_selection.selected={TimelineKey(single.id,"effect_transform","rotation_z",1)};assert window.copy_effect_selected_keys();editor=window.resource_editor;composition=window.project.resource_compositions[0];editor.controller.select_composition(composition.id,composition.layers[0].id);before=deepcopy(window.project.to_dict());assert not editor.paste_copied_keys() and window.project.to_dict()==before;_close(window)


def test_line_edit_and_spinbox_keep_native_copy_paste_focus_behavior(tmp_path):
    editor,_stack,_project,composition=_resource_editor(tmp_path);editor.composition_timeline.key_selection.selected=_selected_resource_keys(composition);assert editor.copy_selected_keys();line=QLineEdit("ordinary text");line.show();line.setFocus();line.selectAll();QTest.keyClick(line,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier);assert APP.clipboard().text()=="ordinary text"
    APP.clipboard().setText("replacement");line.selectAll();QTest.keyClick(line,Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier);assert line.text()=="replacement"
    spin=QSpinBox();spin.setRange(0,999);spin.setValue(123);spin.show();spin.lineEdit().setFocus();spin.lineEdit().selectAll();APP.clipboard().setText("456");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier);assert spin.lineEdit().text()=="456";line.close();spin.close();editor.close()
    combo=QComboBox();combo.setEditable(True);combo.lineEdit().setText("combo");combo.show();combo.lineEdit().setFocus();combo.lineEdit().selectAll();APP.clipboard().setText("edited");QTest.keyClick(combo.lineEdit(),Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier);assert combo.currentText()=="edited";combo.close()


def test_invalid_and_plain_clipboards_are_safe_noops(tmp_path):
    editor,stack,project,_composition=_resource_editor(tmp_path);before=deepcopy(project.to_dict());APP.clipboard().setText("plain text");assert not editor.paste_copied_keys();mime=QMimeData();mime.setData(TIMELINE_KEY_MIME,b'{"version":999}');APP.clipboard().setMimeData(mime);assert not editor.paste_copied_keys() and project.to_dict()==before and stack.count()==0 and FORMAT_VERSION==15;editor.close()


def test_pasted_keys_round_trip_frames_values_easing_and_revolutions(tmp_path):
    editor,_stack,project,composition=_resource_editor(tmp_path);track=composition.layers[0].tracks["rotation"];track.keyframe_at(1).easing="Ease In";track.keyframe_at(4).easing="Ease Out";editor.composition_timeline.key_selection.selected={TimelineKey(composition.layers[0].id,"resource","rotation",1),TimelineKey(composition.layers[0].id,"resource","rotation",4)};assert editor.copy_selected_keys();editor.set_frame(12);assert editor.paste_copied_keys();loaded=Project.from_dict(project.to_dict());copied=loaded.resource_compositions[0].layers[0].tracks["rotation"];assert [(key.frame,key.value,key.easing) for key in copied.keyframes if key.frame>=12]==[(12,0,"Ease In"),(15,720,"Ease Out")];editor.close()
