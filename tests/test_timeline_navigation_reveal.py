from __future__ import annotations
from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import QEvent,QPoint,QPointF,Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.layer_group import LayerGroup,group_node,layer_node
from app.ui.timeline_multi_key import TimelineKey
from app.ui.timeline_time_view import TimelineTimeView,navigation_frame
from tests.test_timeline_multi_key_editing import _close,_effect_window,_resource_editor

APP=QApplication.instance() or QApplication([])


def test_time_view_zoom_fit_and_navigation_are_bounded():
    view=TimelineTimeView();assert view.zoom_width(36,1)>36 and view.zoom_width(8,-20)==8 and view.zoom_width(160,20)==160;assert view.fit_width(800,0,99)==8 and view.fit_width(800,10,10)==64;assert navigation_frame([1,4,4,8],4,1)==8 and navigation_frame([1,4,8],4,-1)==1 and navigation_frame([1],1,1) is None


def test_resource_zoom_preserves_cursor_frame_playhead_selection_and_data(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(620,700);editor.show();timeline.set_frame_cell_width(80);APP.processEvents();timeline.table.horizontalScrollBar().setValue(120);APP.processEvents();layer=composition.layers[0];key=TimelineKey(layer.id,"resource","rotation",4);timeline.key_selection.selected={key};timeline.key_selection.primary=key;before=deepcopy(project.to_dict());frame=timeline._current_frame;item=timeline.table.item(next(i for i,(value,prop) in enumerate(timeline.rows) if value.id==layer.id and prop=="rotation"),4);x=timeline.table.visualItemRect(item).center().x();assert timeline.zoom_time(1,x);APP.processEvents();new_x=timeline.table.visualItemRect(item).center().x();assert abs(new_x-x)<=2 and timeline._current_frame==frame and timeline.key_selection.selected=={key} and project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_zoom_clamps_and_middle_pan_is_navigation_only(tmp_path):
    editor,stack,project,_composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(620,600);editor.show();APP.processEvents();timeline.set_frame_cell_width(160);assert not timeline.zoom_time(10,200) and timeline.frame_cell_width==160;timeline.set_frame_cell_width(80);APP.processEvents();timeline.table.horizontalScrollBar().setValue(100);before=deepcopy(project.to_dict());frame=timeline._current_frame;start=timeline.table.viewport().rect().center();end=start+QPoint(-80,0);QTest.mousePress(timeline.table.viewport(),Qt.MouseButton.MiddleButton,pos=start);move=QMouseEvent(QEvent.Type.MouseMove,QPointF(end),QPointF(end),Qt.MouseButton.NoButton,Qt.MouseButton.MiddleButton,Qt.KeyboardModifier.NoModifier);APP.sendEvent(timeline.table.viewport(),move);QTest.mouseRelease(timeline.table.viewport(),Qt.MouseButton.MiddleButton,pos=end);assert timeline.table.horizontalScrollBar().value()>100 and timeline._current_frame==frame and timeline._key_drag is None and timeline._marquee is None and project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_fit_and_key_navigation_use_visible_keys(tmp_path):
    editor,_stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;timeline.set_frame_cell_width(120);assert timeline.fit_timeline() and timeline.frame_cell_width<120;keys={TimelineKey(composition.layers[0].id,"resource","rotation",1),TimelineKey(composition.layers[1].id,"resource","opacity",10)};timeline.key_selection.selected=keys;assert timeline.fit_selected_keys();editor.set_frame(4);assert timeline.navigate_key(1) and editor.frame_index==7;assert timeline.navigate_key(-1) and editor.frame_index==4;editor.set_frame(10);assert not timeline.navigate_key(1);editor.close()


def test_resource_reveal_modes_filter_tracks_groups_and_repair_keys(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);a,b=composition.layers;a.add_property("scale_x");group=LayerGroup("G",children=[a.id]);composition.groups=[group];composition.root_order=[group_node(group.id),layer_node(b.id)];composition.sync_flat_order();editor.expanded_group_ids={group.id};editor._apply_state(editor.controller.state);timeline=editor.composition_timeline;layer_selection=set(editor.layer_selection.selected_ids);before=deepcopy(project.to_dict());static_key=TimelineKey(a.id,"resource","scale_x",0);hidden=TimelineKey(a.id,"resource","rotation",1);timeline.key_selection.selected={hidden};timeline.key_selection.primary=hidden;assert timeline.set_reveal_mode("animated");assert all(prop!="scale_x" for _layer,prop in timeline.rows) and any(isinstance(layer,LayerGroup) for layer,_prop in timeline.rows) and hidden in timeline.key_selection.selected
    timeline.key_selection.selected={static_key};timeline.key_selection.primary=static_key;timeline.set_reveal_mode("all");timeline.key_selection.selected={hidden};timeline.key_selection.primary=hidden;editor.select_layer_with_modifiers(b.id,Qt.KeyboardModifier.ControlModifier);assert timeline.set_reveal_mode("selected");visible_leaf_ids={layer.id for layer,prop in timeline.rows if prop is None and not isinstance(layer,LayerGroup)};assert visible_leaf_ids==set(editor.layer_selection.selected_ids)&{a.id,b.id};assert editor.layer_selection.selected_ids!=set() and project.to_dict()==before and stack.count()==0;editor.close()


def test_resource_filter_hidden_key_selection_is_removed(tmp_path):
    editor,_stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;key=TimelineKey(composition.layers[0].id,"resource","rotation",1);timeline.key_selection.selected={key};timeline.key_selection.primary=key;editor.select_layer_with_modifiers(composition.layers[1].id,Qt.KeyboardModifier.NoModifier);timeline.set_reveal_mode("selected");assert key not in timeline.key_selection.selected and timeline.key_selection.primary is None;timeline.set_reveal_mode("all");assert key not in timeline.key_selection.selected;editor.close()


def test_effect_zoom_fit_navigation_and_reveal_use_logical_ids(tmp_path):
    window,single,particle=_effect_window(tmp_path);timeline=window.timeline;window.resize(1200,800);window.show();APP.processEvents();before=deepcopy(window.project.to_dict());frame=window.frame_index;assert timeline.zoom_time(1,500) and window.frame_index==frame;timeline.key_selection.selected={TimelineKey(single.id,"effect_transform","rotation_z",1),TimelineKey(particle.id,"effect_motion","radius_end",16)};assert timeline.fit_selected_keys();window.select_frame(5);assert timeline.navigate_key(1) and window.frame_index==8;window.select_effect_layers_with_modifiers(single.id,Qt.KeyboardModifier.NoModifier);window.select_effect_layers_with_modifiers(particle.id,Qt.KeyboardModifier.ControlModifier);assert timeline.set_reveal_mode("selected");assert {row["logical"].id for row in timeline.rows if row.get("logical")}=={single.id,particle.id};assert all(row.get("kind")!="group" for row in timeline.rows);timeline.set_reveal_mode("animated");assert {row["logical"].id for row in timeline.rows if row.get("logical")}=={single.id,particle.id};assert window.project.to_dict()==before and window.application_undo_stack.count()==0;_close(window)


def test_reveal_filter_copy_paste_allows_hidden_model_track_without_hidden_selection(tmp_path):
    editor,stack,_project,composition=_resource_editor(tmp_path);a,b=composition.layers;timeline=editor.composition_timeline;source=TimelineKey(a.id,"resource","rotation",1);timeline.key_selection.selected={source};timeline.key_selection.primary=source;assert editor.copy_selected_keys();editor.select_layer_with_modifiers(b.id,Qt.KeyboardModifier.NoModifier);timeline.set_reveal_mode("selected");editor.set_frame(3);assert editor.paste_copied_keys() and a.tracks["rotation"].keyframe_at(3).value==0 and not timeline.key_selection.selected and stack.count()==1;APP.clipboard().clear();editor.close()


def test_zoomed_multi_key_drag_and_marquee_keep_cell_frame_semantics(tmp_path):
    editor,stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(750,650);editor.show();timeline.set_frame_cell_width(90);APP.processEvents();a=composition.layers[0];row=next(i for i,(layer,prop) in enumerate(timeline.rows) if layer.id==a.id and prop=="rotation");first=timeline.table.visualItemRect(timeline.table.item(row,0)).center();last=timeline.table.visualItemRect(timeline.table.item(row,5)).center();QTest.mousePress(timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=first);QTest.mouseMove(timeline.table.viewport(),last);QTest.mouseRelease(timeline.table.viewport(),Qt.MouseButton.LeftButton,pos=last);APP.processEvents();assert {key.frame for key in timeline.key_selection.selected}=={1,4} and stack.count()==0;editor.close()
