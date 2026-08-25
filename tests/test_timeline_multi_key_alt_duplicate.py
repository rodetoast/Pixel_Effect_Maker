from __future__ import annotations

from copy import deepcopy
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.ui.timeline_multi_key import (
    PASTE_COLLISION,
    PASTE_OUT_OF_RANGE,
    TimelineKey,
    duplicate_timeline_keys_atomic,
)
from tests.test_timeline_multi_key_editing import _close, _effect_window, _resource_editor


APP = QApplication.instance() or QApplication([])


def _mouse_event(kind,point,button,buttons,modifiers):
    position=QPointF(point);return QMouseEvent(kind,position,position,position,button,buttons,modifiers)


def test_common_duplicate_preserves_payload_and_rejects_collision_and_boundary():
    from app.models.resource_composition import AnimationTrack

    rotation=AnimationTrack("rotation",0.0);rotation.set_keyframe(2,720,"Ease In");rotation.set_keyframe(5,1080,"Ease Out")
    opacity=AnimationTrack("opacity",1.0);opacity.set_keyframe(3,.4,"Ease In/Out")
    tracks={("a","resource","rotation"):rotation,("b","resource","opacity"):opacity}
    keys={TimelineKey("a","resource","rotation",2),TimelineKey("a","resource","rotation",5),TimelineKey("b","resource","opacity",3)}
    issue,selected,primary=duplicate_timeline_keys_atomic(tracks,keys,4,16,TimelineKey("a","resource","rotation",5))
    assert issue is None and {key.frame for key in selected}=={6,7,9} and primary==TimelineKey("a","resource","rotation",9)
    assert [(key.frame,key.value,key.easing) for key in rotation.keyframes]==[(2,720,"Ease In"),(5,1080,"Ease Out"),(6,720,"Ease In"),(9,1080,"Ease Out")]
    before=deepcopy([(key.frame,key.value,key.easing) for key in rotation.keyframes]);assert duplicate_timeline_keys_atomic(tracks,{TimelineKey("a","resource","rotation",2)},3,16)[0]==PASTE_COLLISION;assert [(key.frame,key.value,key.easing) for key in rotation.keyframes]==before
    assert duplicate_timeline_keys_atomic(tracks,{TimelineKey("a","resource","rotation",9)},8,16)[0]==PASTE_OUT_OF_RANGE


def test_resource_duplicate_is_atomic_one_undo_selects_copies_and_preserves_clipboard(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);a,b=composition.layers;rotation=a.tracks["rotation"];rotation.keyframe_at(1).easing="Ease In";rotation.keyframe_at(4).easing="Ease Out"
    keys={TimelineKey(a.id,"resource","rotation",1),TimelineKey(a.id,"resource","rotation",4),TimelineKey(b.id,"resource","opacity",2)};primary=TimelineKey(a.id,"resource","rotation",4);selection=editor.composition_timeline.key_selection;selection.selected=set(keys);selection.primary=primary;APP.clipboard().setText("keep me")
    assert editor.duplicate_selected_keys(keys,2) and stack.count()==1 and APP.clipboard().text()=="keep me"
    expected={key.at_frame(key.frame+2) for key in keys};assert selection.selected==expected and selection.primary==primary.at_frame(6)
    rotation=a.tracks["rotation"];assert [(key.frame,key.value,key.easing) for key in rotation.keyframes]==[(1,0,"Ease In"),(3,0,"Ease In"),(4,720,"Ease Out"),(6,720,"Ease Out"),(8,1080,"Linear")]
    saved=[(key.frame,key.value,key.easing) for key in rotation.keyframes];stack.undo();assert not (selection.selected&expected);stack.redo();assert [(key.frame,key.value,key.easing) for key in a.tracks["rotation"].keyframes]==saved
    before=deepcopy(project.to_dict());count=stack.count();assert not editor.duplicate_selected_keys({TimelineKey(a.id,"resource","rotation",1),TimelineKey(a.id,"resource","rotation",4)},3);assert project.to_dict()==before and stack.count()==count
    assert not editor.duplicate_selected_keys({TimelineKey(a.id,"resource","rotation",8)},4) and project.to_dict()==before and stack.count()==count;editor.close()


def test_effect_duplicate_uses_logical_ids_and_keeps_layer_parenting(tmp_path):
    window,single,particle=_effect_window(tmp_path);single.parent_id=particle.id;single.parent_offset=(1,0,3,0,1,4,0,0,1);generated=[layer.generated_layer_id for layer in window.project.effect_resource_layers];keys={TimelineKey(single.id,"effect_transform","rotation_z",1),TimelineKey(single.id,"effect_transform","rotation_z",5),TimelineKey(particle.id,"effect_motion","radius_end",2)};primary=TimelineKey(single.id,"effect_transform","rotation_z",5);window.timeline.key_selection.selected=set(keys);window.timeline.key_selection.primary=primary
    assert window.duplicate_effect_selected_keys(keys,3) and window.application_undo_stack.count()==1
    assert window.timeline.key_selection.selected=={key.at_frame(key.frame+3) for key in keys} and window.timeline.key_selection.primary==primary.at_frame(8)
    assert [(key.frame,key.value) for key in single.layer_transform.tracks["rotation_z"].keyframes]==[(1,0.0),(4,0.0),(5,720.0),(8,720.0),(12,1080.0)]
    assert [layer.generated_layer_id for layer in window.project.effect_resource_layers]==generated and (single.parent_id,single.parent_offset)==(particle.id,(1,0,3,0,1,4,0,0,1));window.application_undo_stack.undo();assert not (window.timeline.key_selection.selected&{key.at_frame(key.frame+3) for key in keys});window.application_undo_stack.redo();_close(window)


def test_alt_mode_latches_at_drag_threshold_and_escape_is_non_mutating(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(1100,700);editor.show();APP.processEvents();layer=composition.layers[0];row=next(index for index,(current,prop) in enumerate(timeline.rows) if current.id==layer.id and prop=="rotation");source=timeline.table.visualItemRect(timeline.table.item(row,1)).center();target=timeline.table.visualItemRect(timeline.table.item(row,3)).center();before=deepcopy(project.to_dict())
    APP.sendEvent(timeline.table.viewport(),_mouse_event(QEvent.Type.MouseButtonPress,source,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier))
    APP.sendEvent(timeline.table.viewport(),_mouse_event(QEvent.Type.MouseMove,target,Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.AltModifier));assert timeline._drag_state()[4] is True and "+" in {timeline.table.item(row,column).text() for column in range(timeline.table.columnCount())}
    APP.sendEvent(timeline.table.viewport(),_mouse_event(QEvent.Type.MouseMove,target,Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier));assert timeline._drag_state()[4] is True
    timeline.table.setFocus();QTest=__import__("PySide6.QtTest",fromlist=["QTest"]).QTest;QTest.keyClick(timeline.table,Qt.Key.Key_Escape);assert timeline._key_drag is None and project.to_dict()==before and stack.count()==0;editor.close()


def test_alt_drag_selected_marker_duplicates_whole_selection(tmp_path):
    editor,stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(1100,700);editor.show();APP.processEvents();editor.controller.select_composition(composition.id,composition.layers[0].id);APP.processEvents();layer=composition.layers[0];keys={TimelineKey(layer.id,"resource","rotation",1),TimelineKey(layer.id,"resource","rotation",4)};timeline.key_selection.selected=set(keys);timeline.key_selection.primary=TimelineKey(layer.id,"resource","rotation",4);row=next(index for index,(current,prop) in enumerate(timeline.rows) if current.id==layer.id and prop=="rotation");source=timeline.table.visualItemRect(timeline.table.item(row,4)).center();target=timeline.table.visualItemRect(timeline.table.item(row,6)).center();captured=[];timeline.multi_key_duplicate_requested.connect(lambda selected,delta:captured.append((set(selected),delta)))
    APP.sendEvent(timeline.table.viewport(),_mouse_event(QEvent.Type.MouseButtonPress,source,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.AltModifier));APP.sendEvent(timeline.table.viewport(),_mouse_event(QEvent.Type.MouseMove,target,Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.AltModifier));assert timeline._drag_state()[3] and timeline._drag_state()[4] and set(timeline._drag_state()[5])==keys;APP.sendEvent(timeline.table.viewport(),_mouse_event(QEvent.Type.MouseButtonRelease,target,Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier));APP.processEvents()
    assert captured==[(keys,2)] and stack.count()==1 and [key.frame for key in layer.tracks["rotation"].keyframes]==[1,3,4,6,8] and timeline.key_selection.selected=={key.at_frame(key.frame+2) for key in keys};editor.close()


def test_duplicate_helper_scales_without_mouse_move_deepcopy():
    from app.models.resource_composition import AnimationTrack

    timings=[]
    for count in (10,100,500):
        track=AnimationTrack("position_x",0.0)
        for frame in range(count):track.set_keyframe(frame,float(frame),"Linear")
        keys={TimelineKey("a","resource","position_x",frame) for frame in range(count)};start=time.perf_counter();issue,selected,_=duplicate_timeline_keys_atomic({("a","resource","position_x"):track},keys,count,2*count+1);timings.append(time.perf_counter()-start);assert issue is None and len(selected)==count
    assert timings[-1]<1.0
