"""Deterministic keyframe editing, UI state, undo, and v9 round-trip coverage."""

from __future__ import annotations

from copy import deepcopy
import random

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QUndoStack, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import ParticleMotionSettings
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import AnimationTrack, CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.ui.resource_editor_v2.composition_inspector import LayerInspector
from app.ui.resource_editor_v2.composition_timeline import CompositionTimeline
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget
from app.ui.resource_layer_transform_panel import ResourceLayerTransformPanel
from app.ui.timeline_widget import TimelineWidget
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.services.settings_service import ShortcutSettingsService


APP = QApplication.instance() or QApplication([])


class _Localization:
    language = "en"

    @staticmethod
    def text(key):
        return key


def _composition_project():
    project=Project.create_default(width=16,height=16);pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[1,1]=[255,255,255,255];asset=SourceAsset("sprite",pixels);project.source_assets.append(asset)
    composition=ResourceComposition("Resource",16,16,12,11,True);layer=CompositionLayer("sprite","source_asset",asset.id,0,10,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y);composition.layers.append(layer);project.resource_compositions.append(composition);return project,composition,layer


def _resource_editor(tmp_path):
    project,composition,layer=_composition_project();editor=ResourceEditorWidget(QSettings(str(tmp_path/"ui.ini"),QSettings.Format.IniFormat));editor.retranslate_ui(_Localization());stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id);editor.controller.select_layer(layer.id);return editor,stack,project,composition,layer


def test_track_add_update_delete_sort_and_reference_evaluation():
    track=AnimationTrack("rotation",5);track.set_keyframe(10,100);track.set_keyframe(0,0);track.set_keyframe(10,120)
    assert [key.frame for key in track.keyframes]==[0,10]
    assert track.evaluate(-10)==0 and track.evaluate(5)==60 and track.evaluate(99)==120
    assert track.has_keyframe(0) and track.keyframe_at(10).value==120
    assert track.delete_keyframe(0) and not track.delete_keyframe(0)
    assert track.delete_keyframe(10) and track.keyframes==[] and track.default_value==120 and track.evaluate(5)==120


def test_key_move_clamps_rejects_collision_and_preserves_value():
    track=AnimationTrack("opacity",1);track.set_keyframe(2,.2);track.set_keyframe(7,.7)
    assert not track.move_keyframe(2,7,11)
    assert track.move_keyframe(2,-20,11) and track.keyframe_at(0).value==.2
    assert track.move_keyframe(7,99,11) and track.keyframe_at(10).value==.7


def test_randomized_tracks_are_unique_sorted_and_round_trip():
    rng=random.Random(9401)
    for _ in range(200):
        track=AnimationTrack("position_x",0)
        for _ in range(40):track.set_keyframe(rng.randrange(0,31),rng.uniform(-100,100))
        frames=[key.frame for key in track.keyframes]
        assert frames==sorted(set(frames))
        loaded=AnimationTrack.from_dict(track.to_dict())
        assert loaded.to_dict()==track.to_dict()
        assert [loaded.evaluate(frame) for frame in range(31)]==[track.evaluate(frame) for frame in range(31)]


def test_inspector_distinguishes_static_unkeyed_animated_and_current_key():
    _,_,layer=_composition_project();track=layer.add_property("rotation");inspector=LayerInspector();inspector.retranslate(_Localization())
    inspector.set_layer(layer,None,0);card=inspector.property_cards["rotation"];assert card["key_state"]=="static" and card["editors"][0].isEnabled() and card["keyframe"].text()=="◇"
    track.set_keyframe(0,0);track.set_keyframe(10,100);inspector.set_layer(layer,None,5);card=inspector.property_cards["rotation"];assert card["key_state"]=="animated_no_key" and card["editors"][0].isEnabled() and "adds a keyframe" in card["keyframe"].toolTip()
    inspector.set_layer(layer,None,10);card=inspector.property_cards["rotation"];assert card["key_state"]=="current_key" and card["editors"][0].isEnabled() and card["keyframe"].text()=="◆";inspector.close();inspector.deleteLater();APP.processEvents()


def test_timeline_first_last_markers_and_key_selection_are_exact():
    _,composition,layer=_composition_project();track=layer.add_property("rotation");track.set_keyframe(0,0);track.set_keyframe(10,90);timeline=CompositionTimeline();timeline.retranslate(_Localization());timeline.refresh(composition,layer,0)
    row=timeline.rows.index((layer,"rotation"));assert timeline.table.item(row,0).text()=="◆" and timeline.table.item(row,10).text()=="◆"
    selected=[];timeline.frame_selected.connect(selected.append);timeline._clicked(row,10);timeline.table.setCurrentCell(row,10)
    assert selected==[10] and timeline.table.currentRow()==row and timeline.table.currentColumn()==10;timeline.close();timeline.deleteLater();APP.processEvents()


def test_timeline_key_drag_emits_one_exact_move():
    _,composition,layer=_composition_project();layer.add_property("rotation").set_keyframe(2,20);timeline=CompositionTimeline();timeline.resize(700,260);timeline.refresh(composition,layer,2);timeline.show();APP.processEvents();row=timeline.rows.index((layer,"rotation"));source=timeline.table.visualItemRect(timeline.table.item(row,2)).center();target=timeline.table.visualItemRect(timeline.table.item(row,7)).center();moves=[];timeline.move_keyframe_requested.connect(lambda *parts:moves.append(parts))
    QTest.mousePress(timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=source);QTest.mouseMove(timeline.table.viewport(),target,20);QTest.mouseRelease(timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=target);APP.processEvents()
    assert moves==[("rotation",2,7)];timeline.close();timeline.deleteLater();APP.processEvents()


def test_resource_editor_add_edit_delete_move_undo_redo(tmp_path):
    editor,stack,project,composition,layer=_resource_editor(tmp_path)
    layer.add_property("rotation");editor.set_frame(0);editor.set_keyframe("rotation",0,"Linear");editor.set_frame(10);editor.set_keyframe("rotation",100,"Linear");assert stack.count()==2
    editor.set_frame(5);editor._property_value("rotation",999);assert layer.tracks["rotation"].keyframe_at(5).value==999
    stack.undo();assert not layer.tracks["rotation"].has_keyframe(5) and layer.tracks["rotation"].evaluate(5)==50;stack.redo();assert layer.tracks["rotation"].keyframe_at(5).value==999
    editor._move_keyframe("rotation",10,9);assert layer.tracks["rotation"].keyframe_at(9).value==100;stack.undo();assert layer.tracks["rotation"].keyframe_at(10).value==100;stack.redo();assert layer.tracks["rotation"].keyframe_at(9).value==100
    editor.set_frame(9);editor._delete_keyframe("rotation");assert not layer.tracks["rotation"].has_keyframe(9);stack.undo();assert layer.tracks["rotation"].has_keyframe(9);stack.redo();assert not layer.tracks["rotation"].has_keyframe(9);editor.close();editor.deleteLater();APP.processEvents()


def test_v9_resource_effect_and_motion_tracks_round_trip_deterministically():
    project,composition,resource_layer=_composition_project();resource_layer.add_property("rotation").set_keyframe(10,90,"Ease In");resource_layer.tracks["rotation"].set_keyframe(0,0)
    effect=EffectResourceLayer("Effect Resource",composition.id,end_frame=10);effect.layer_transform.set_keyframe("rotation_z",10,180);effect.layer_transform.set_keyframe("rotation_z",0,0);effect.particle_settings.motion.set_keyframe("radius_end",0,2);effect.particle_settings.motion.set_keyframe("radius_end",10,8);project.effect_resource_layers.append(effect)
    data=project.to_dict();loaded=Project.from_dict(deepcopy(data));assert FORMAT_VERSION==17 and loaded.to_dict()==data
    loaded_resource=loaded.resource_compositions[0].layers[0];loaded_effect=loaded.effect_resource_layers[0]
    assert loaded_resource.value("rotation",5)==45 and loaded_effect.layer_transform.value("rotation_z",5)==90 and loaded_effect.particle_settings.motion.value("radius_end",5)==5


def test_effect_transform_panel_uses_same_three_states_and_explicit_delete():
    layer=EffectResourceLayer("Effect","resource",end_frame=10);layer.layer_transform.set_keyframe("rotation_z",0,0);layer.layer_transform.set_keyframe("rotation_z",10,90);panel=ResourceLayerTransformPanel();panel.setChecked(True);panel.retranslate_ui(_Localization());panel.set_layer(layer,5)
    assert panel.key_buttons["rotation_z"].property("keyState")=="animated_no_key" and panel.fields["rotation_z"].isEnabled()
    deleted=[];panel.keyframe_delete_requested.connect(lambda *parts:deleted.append(parts));panel.set_layer(layer,10);assert panel.key_buttons["rotation_z"].text()=="◆" and panel.fields["rotation_z"].isEnabled();panel._add_key("rotation_z")
    assert deleted==[(layer.id,"rotation_z",10)];panel.close();panel.deleteLater();APP.processEvents()


def test_effect_timeline_marks_system_and_motion_keys_on_exact_frame():
    project,composition,_=_composition_project();generated=project.layers[0];effect=EffectResourceLayer("Effect",composition.id,placement_mode="particle",end_frame=10,generated_layer_id=generated.id);effect.layer_transform.set_keyframe("opacity",0,1);effect.particle_settings.motion.set_keyframe("radius_end",10,8);project.effect_resource_layers.append(effect);timeline=TimelineWidget();timeline.refresh(project,0,0,display_frame_count=11);row=0
    assert timeline.table.item(row,timeline.FRAME_COLUMN_OFFSET).text()=="◆" and timeline.table.item(row,timeline.FRAME_COLUMN_OFFSET+10).text()=="◆";timeline.close();timeline.deleteLater();APP.processEvents()


def test_static_property_edit_does_not_auto_key_and_first_key_is_explicit(tmp_path):
    editor,stack,_,_,layer=_resource_editor(tmp_path);layer.add_property("rotation");editor._property_value("rotation",25)
    assert layer.tracks["rotation"].keyframes==[] and layer.tracks["rotation"].default_value==25 and stack.count()==1
    editor.set_keyframe("rotation",25,"Linear");assert layer.tracks["rotation"].has_keyframe(0) and len(layer.tracks["rotation"].keyframes)==1
    editor.close()


def test_animated_unkeyed_inspector_auto_key_marker_diamond_undo_redo(tmp_path):
    editor,stack,_,composition,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(0,0);track.set_keyframe(10,100);editor.controller.changed();editor.set_frame(5);before=stack.count()
    editor._property_value("rotation",65);assert layer.tracks["rotation"].keyframe_at(5).value==65 and stack.count()==before+1
    row=editor.composition_timeline.rows.index((layer,"rotation"));assert editor.composition_timeline.table.item(row,5).text()=="◆" and editor.layer_inspector.property_cards["rotation"]["keyframe"].text()=="◆"
    stack.undo();assert not layer.tracks["rotation"].has_keyframe(5) and layer.tracks["rotation"].evaluate(5)==50;stack.redo();assert layer.tracks["rotation"].keyframe_at(5).value==65
    editor.close()


def test_programmatic_frame_sync_scrub_and_selection_do_not_auto_key(tmp_path):
    editor,stack,_,_,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(0,0);track.set_keyframe(10,100);editor.controller.changed();before=stack.count()
    for frame in (0,5,10,2,8):editor.set_frame(frame)
    editor.controller.select_layer(layer.id);editor.layer_inspector.retranslate(_Localization())
    assert [key.frame for key in track.keyframes]==[0,10] and stack.count()==before
    editor.close()


def test_deleted_key_reauto_keys_while_animated_but_last_delete_returns_static(tmp_path):
    editor,_,_,_,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(0,0);track.set_keyframe(10,100);editor.controller.changed();editor.set_frame(10);editor._delete_keyframe("rotation");assert not layer.tracks["rotation"].has_keyframe(10) and layer.tracks["rotation"].keyframes
    editor._property_value("rotation",80);assert layer.tracks["rotation"].keyframe_at(10).value==80
    editor._delete_keyframe("rotation");editor.set_frame(0);editor._delete_keyframe("rotation");assert not layer.tracks["rotation"].keyframes and layer.tracks["rotation"].default_value==0
    editor.set_frame(5);editor._property_value("rotation",33);assert not layer.tracks["rotation"].keyframes and layer.tracks["rotation"].default_value==33
    editor.close()


def test_resource_rotation_z_conditional_auto_key_uses_canonical_track(tmp_path):
    editor,_,_,_,layer=_resource_editor(tmp_path);layer.add_property("rotation").set_keyframe(0,0);editor.controller.changed();editor.set_frame(10);editor._property_value("rotation",90)
    assert "rotation" in layer.tracks and "rotation_z" not in layer.tracks and layer.tracks["rotation"].keyframe_at(10).value==90
    editor.close()


def test_resource_gizmo_delta_auto_keys_and_escape_removes_transient_key(tmp_path):
    editor,stack,_,_,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(0,0);editor.controller.changed();editor.set_frame(5);before=stack.count()
    editor._gizmo_change("rotation",30,False);assert layer.tracks["rotation"].keyframe_at(5).value==30
    editor._gizmo_cancel("rotation",0);assert not layer.tracks["rotation"].has_keyframe(5) and stack.count()==before
    editor._gizmo_change("rotation",45,False);editor._gizmo_change("rotation",60,True);assert layer.tracks["rotation"].keyframe_at(5).value==60 and stack.count()==before+1
    stack.undo();assert not layer.tracks["rotation"].has_keyframe(5);stack.redo();assert layer.tracks["rotation"].keyframe_at(5).value==60
    editor.close()


def test_resource_gizmo_no_delta_does_not_create_key_or_undo(tmp_path):
    editor,stack,_,_,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(0,0);editor.controller.changed();editor.set_frame(5);before=stack.count()
    editor._gizmo_change("rotation",track.evaluate(5),True)
    assert not track.has_keyframe(5) and stack.count()==before and "rotation" not in editor._gizmo_before
    editor.close()


def test_effect_transform_inspector_auto_keys_only_after_actual_delta():
    layer=EffectResourceLayer("Effect","resource",end_frame=10);transform=layer.layer_transform;transform.set_keyframe("position_x",0,0);panel=ResourceLayerTransformPanel();panel.setChecked(True);panel.set_layer(layer,5);changes=[];panel.interactive_transform_changed.connect(lambda *parts:changes.append(parts))
    panel.fields["position_x"].setValue(0);assert not changes and not transform.tracks["position_x"].has_keyframe(5)
    panel.fields["position_x"].setValue(12);assert changes and changes[-1][1].tracks["position_x"].keyframe_at(5).value==12
    panel.close()


def test_effect_timeline_accepts_transient_auto_key_marker():
    project,composition,_=_composition_project();generated=project.layers[0];effect=EffectResourceLayer("Effect",composition.id,end_frame=10,generated_layer_id=generated.id);timeline=TimelineWidget();timeline.refresh(project,0,5,display_frame_count=11);transient=deepcopy(effect);transient.layer_transform.set_keyframe("position_x",5,12);timeline.set_resource_layer_key_marker(project,transient,5)
    assert timeline.table.item(0,timeline.FRAME_COLUMN_OFFSET+5).text()=="◆"
    timeline.set_resource_layer_key_marker(project,effect,5);assert timeline.table.item(0,timeline.FRAME_COLUMN_OFFSET+5).text()!="◆";timeline.close()


def test_existing_current_key_edit_updates_without_duplicate(tmp_path):
    editor,_,_,_,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(5,20);editor.controller.changed();editor.set_frame(5);editor._property_value("rotation",70)
    assert len(layer.tracks["rotation"].keyframes)==1 and layer.tracks["rotation"].keyframe_at(5).value==70
    editor.close()


def test_auto_created_key_v9_round_trip_and_random_access(tmp_path):
    editor,_,project,_,layer=_resource_editor(tmp_path);track=layer.add_property("rotation");track.set_keyframe(0,0);editor.controller.changed();editor.set_frame(10);editor._property_value("rotation",100);expected={frame:layer.tracks["rotation"].evaluate(frame) for frame in (10,0,7,3,5)}
    loaded=Project.from_dict(project.to_dict());loaded_track=loaded.resource_compositions[0].layers[0].tracks["rotation"]
    assert loaded_track.keyframe_at(10).value==100 and {frame:loaded_track.evaluate(frame) for frame in (10,0,7,3,5)}==expected
    editor.close()


def test_particle_motion_inspector_conditional_auto_key_and_programmatic_guard():
    project=Project.create_default();[project.add_frame() for _ in range(10)];project._current_effect_frame=5;composition=ResourceComposition("Motion");project.resource_compositions.append(composition);layer=EffectResourceLayer("Particle",composition.id,placement_mode="particle",end_frame=10);layer.particle_settings.motion=ParticleMotionSettings(mode="orbit",radius_end=20);layer.particle_settings.motion.set_keyframe("radius_end",0,20);panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda _,settings:changes.append(settings));panel.set_resource_layer(layer,project)
    assert not changes and not layer.particle_settings.motion.tracks["radius_end"].has_keyframe(5)
    panel.motion_radius_end.setValue(35);assert changes and changes[-1].motion.tracks["radius_end"].keyframe_at(5).value==35
    panel.close()


def _apply_spin_interaction(spin,interaction):
    spin.setFocus();APP.processEvents()
    if interaction=="arrow":QTest.keyClick(spin,Qt.Key.Key_Up)
    elif interaction=="typing":
        spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"42");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Enter)
    else:
        local=QPointF(spin.rect().center());event=QWheelEvent(local,QPointF(spin.mapToGlobal(local.toPoint())),QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.ControlModifier,Qt.ScrollPhase.ScrollUpdate,False);APP.notify(spin,event)
    APP.processEvents()


@pytest.mark.parametrize("interaction",["typing","arrow","wheel"])
def test_animated_unkeyed_spin_inputs_share_conditional_auto_key(tmp_path,interaction):
    _,_,layer=_composition_project();layer.add_property("rotation").set_keyframe(0,0);inspector=LayerInspector();inspector.retranslate(_Localization());inspector.set_layer(layer,None,5);values=[];inspector.property_value_requested.connect(lambda property_id,value:values.append((property_id,value)));inspector.show();APP.processEvents();spin=inspector.property_cards["rotation"]["editors"][0]
    _apply_spin_interaction(spin,interaction)
    assert values and values[-1][0]=="rotation" and values[-1][1]!=0
    inspector.close()


def _effect_window(tmp_path,mode="single"):
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/f"{mode}.ini"),QSettings.Format.IniFormat)));[window.project.add_frame() for _ in range(11)];composition=ResourceComposition("Effect Resource",width=16,height=16,frame_count=12);window.project.resource_compositions.append(composition);layer=window.create_resource_layer_from_resource(composition.id,mode);window.select_resource_layer(layer.id);window.canvas.resize(700,500);window.show();APP.processEvents();return window,layer


def test_effect_system_gizmo_press_delta_release_undo_redo_and_escape(tmp_path):
    window,layer=_effect_window(tmp_path);layer.layer_transform.set_keyframe("position_x",0,0);layer.layer_transform.set_keyframe("position_y",0,0);window.select_frame(5);window._set_resource_transform_gizmo(layer.id,"move");APP.processEvents();canvas=window.canvas;before=window.application_undo_stack.count();handle=canvas.resource_transform_handle_positions()["x"].toPoint()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=handle);assert not layer.layer_transform.tracks["position_x"].has_keyframe(5) and window.application_undo_stack.count()==before
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(canvas,handle+QPoint(24,0));assert canvas.resource_transform.tracks["position_x"].has_keyframe(5) and window.timeline.table.currentItem().text()=="◆";QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(24,0));APP.processEvents()
    assert layer.layer_transform.tracks["position_x"].has_keyframe(5) and window.application_undo_stack.count()==before+1
    window.application_undo_stack.undo();assert not layer.layer_transform.tracks["position_x"].has_keyframe(5);window.application_undo_stack.redo();assert layer.layer_transform.tracks["position_x"].has_keyframe(5)
    window.application_undo_stack.undo();handle=canvas.resource_transform_handle_positions()["y"].toPoint();before=window.application_undo_stack.count();QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(canvas,handle+QPoint(0,20));QTest.keyClick(canvas,Qt.Key.Key_Escape);APP.processEvents()
    assert not layer.layer_transform.tracks["position_y"].has_keyframe(5) and window.application_undo_stack.count()==before
    window.dirty=False;window.close()


@pytest.mark.parametrize("mode",["orbit","helix"])
def test_motion_handle_conditional_auto_key_and_escape(tmp_path,mode):
    window,layer=_effect_window(tmp_path,"particle");layer.particle_settings.motion=ParticleMotionSettings(mode=mode,radius_start=12,radius_end=24,turns=1);layer.particle_settings.motion.set_keyframe("radius_start",0,12);layer.particle_settings.motion.set_keyframe("radius_end",0,24);window.particle_preview_manager.revert(layer.as_particle_emitter());window.select_resource_layer(layer.id);window.select_frame(5);APP.processEvents();canvas=window.canvas;before=window.application_undo_stack.count();start=canvas._guide_points()["radius_start"].toPoint()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(canvas,start+QPoint(18,0));assert canvas.effect_guide_settings.motion.tracks["radius_start"].has_keyframe(5);QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=start+QPoint(18,0));APP.processEvents()
    assert layer.particle_settings.motion.tracks["radius_start"].has_keyframe(5) and window.application_undo_stack.count()==before+1
    window.application_undo_stack.undo();assert not layer.particle_settings.motion.tracks["radius_start"].has_keyframe(5);window.application_undo_stack.redo();assert layer.particle_settings.motion.tracks["radius_start"].has_keyframe(5)
    window.application_undo_stack.undo();window.select_resource_layer(layer.id);window.select_frame(5);end=canvas._guide_points()["radius_end"].toPoint();before=window.application_undo_stack.count();QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=end);QTest.mouseMove(canvas,end+QPoint(20,0));QTest.keyClick(canvas,Qt.Key.Key_Escape);APP.processEvents()
    assert not layer.particle_settings.motion.tracks["radius_end"].has_keyframe(5) and window.application_undo_stack.count()==before
    window.dirty=False;window.close()
