from __future__ import annotations

from copy import deepcopy
import os
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.timeline_multi_key import TimelineKey
from app.ui.timeline_snapping import (
    SNAP_KEYFRAME,SNAP_PLAYHEAD,SNAP_START,SNAP_END,
    batch_delta_issue,collect_snap_targets,compute_batch_snap,
)
from app.ui.timeline_time_view import TimelineTimeView
from tests.test_timeline_multi_key_editing import _close,_effect_window,_resource_editor


APP=QApplication.instance() or QApplication([])


def test_snap_helper_threshold_ranking_dedupe_and_source_exclusion():
    source=TimelineKey("a","resource","position_x",2);other=TimelineKey("b","resource","opacity",10);same_frame=TimelineKey("c","resource","scale_x",10)
    snapshot=collect_snap_targets({source,other,same_frame},{source},9,24);assert [(target.frame,target.kind) for target in snapshot.targets].count((10,SNAP_KEYFRAME))==1 and all(not (target.frame==2 and target.kind==SNAP_KEYFRAME) for target in snapshot.targets)
    result=compute_batch_snap(snapshot,{source},7.5,8,8,lambda _delta:True);assert result and result.delta==7 and result.guide_frame==9 and result.target_kind==SNAP_PLAYHEAD
    assert compute_batch_snap(snapshot,{source},7.9,8,160,lambda _delta:True) is None
    tied=collect_snap_targets({TimelineKey("b","resource","opacity",8)},{source},6,24);result=compute_batch_snap(tied,{source},5.0,5,8,lambda _delta:True);assert result and result.target_kind==SNAP_PLAYHEAD
    view=TimelineTimeView();assert view.frame_to_x(3,-16,8)==12 and view.frame_to_x(3,-16,160)==544


def test_batch_snap_preserves_shared_delta_boundaries_and_skips_invalid_candidates():
    keys={TimelineKey("a","resource","position_x",2),TimelineKey("b","resource","opacity",5)};visible=keys|{TimelineKey("c","resource","scale_x",10),TimelineKey("d","resource","scale_y",11)};snapshot=collect_snap_targets(visible,keys,15,20)
    result=compute_batch_snap(snapshot,keys,5.1,5,8,lambda delta:delta!=5);assert result and result.delta==6 and {key.frame+result.delta for key in keys}=={8,11}
    assert compute_batch_snap(snapshot,keys,5.1,5,8,lambda _delta:False) is None
    start=compute_batch_snap(snapshot,keys,-2.0,-2,8,lambda _delta:True);assert start and start.target_kind==SNAP_START and start.delta==-2
    end=compute_batch_snap(snapshot,keys,14.0,14,8,lambda _delta:True);assert end and end.target_kind==SNAP_END and end.delta==14


def test_collision_validation_differs_for_move_and_duplicate_sources():
    keys={TimelineKey("a","resource","position_x",2),TimelineKey("a","resource","position_x",4)};occupied=keys|{TimelineKey("a","resource","position_x",8)}
    assert batch_delta_issue(keys,2,12,occupied,False) is None
    assert batch_delta_issue(keys,4,12,occupied,False)=="collision"
    assert batch_delta_issue(keys,2,12,occupied,True)=="collision"
    assert batch_delta_issue(keys,8,12,occupied,False)=="boundary"


def test_resource_snap_toggle_runtime_and_drag_resolution(tmp_path):
    editor,stack,project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;editor.resize(1100,700);editor.show();APP.processEvents();editor.controller.select_composition(composition.id,composition.layers[0].id);timeline.set_frame_cell_width(8);APP.processEvents();layer=composition.layers[0];key=TimelineKey(layer.id,"resource","rotation",1);selected={key};snapshot=collect_snap_targets(timeline._visible_keys,selected,0,composition.frame_count);row=next(index for index,(current,prop) in enumerate(timeline.rows) if current.id==layer.id and prop=="rotation");start=timeline.table.visualItemRect(timeline.table.item(row,1)).center().x();x=start+5.2*8;before=deepcopy(project.to_dict())
    delta,result,issue=timeline._resolve_drag_delta(1,start,x,False,selected,snapshot);assert (delta,result.guide_frame,issue)==(6,7,None)
    timeline._preview_key_drag(1,x,keys=selected,start_x=start,snap_snapshot=snapshot);assert timeline._snap_guide.isVisible() and "Frame 8" in timeline.key_selection_status.text()
    assert timeline.set_snap_enabled(False);delta,result,issue=timeline._resolve_drag_delta(1,start,x,False,selected,snapshot);assert delta==5 and result is None and issue is None and not timeline._snap_guide.isVisible();assert project.to_dict()==before and stack.count()==0
    assert editor.move_selected_keys(selected,6) and layer.tracks["rotation"].keyframe_at(7).value==0 and stack.count()==1;editor.close()


def test_resource_alt_duplicate_uses_snapped_delta_and_keeps_sources(tmp_path):
    editor,stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;layer=composition.layers[0];selected={TimelineKey(layer.id,"resource","rotation",1)};timeline.set_frame_cell_width(8);snapshot=collect_snap_targets(timeline._visible_keys,selected,0,composition.frame_count);snap=compute_batch_snap(snapshot,selected,5.2,5,8,lambda value:batch_delta_issue(selected,value,composition.frame_count,timeline._occupied_keys,True) is None)
    assert snap and snap.delta==6 and editor.duplicate_selected_keys(selected,snap.delta);track=layer.tracks["rotation"];assert [(key.frame,key.value) for key in track.keyframes]==[(1,0),(4,720),(7,0),(8,1080)] and timeline.key_selection.selected=={TimelineKey(layer.id,"resource","rotation",7)} and stack.count()==1;editor.close()


def test_reveal_targets_and_effect_logical_identity(tmp_path):
    editor,_stack,_project,composition=_resource_editor(tmp_path);timeline=editor.composition_timeline;layer=composition.layers[0];timeline._selected_ids={layer.id};timeline.set_reveal_mode("selected");assert {key.layer_id for key in timeline._visible_keys}=={layer.id};snapshot=collect_snap_targets(timeline._visible_keys,set(),0,composition.frame_count);assert all(target.frame in {0,1,4,8,composition.frame_count-1} for target in snapshot.targets);editor.close()
    window,single,_particle=_effect_window(tmp_path);timeline=window.timeline;logical={key.layer_id for key in timeline._visible_keys};generated={layer.generated_layer_id for layer in window.project.effect_resource_layers};assert single.id in logical and not (logical&generated);timeline.set_frame_cell_width(8);selected={TimelineKey(single.id,"effect_transform","rotation_z",1)};snapshot=collect_snap_targets(timeline._visible_keys,selected,0,timeline._display_frame_count);row=next(index for index,value in enumerate(timeline.rows) if value.get("kind")=="property" and value.get("logical").id==single.id and value.get("property_id")=="rotation_z");start=timeline.table.visualItemRect(timeline.table.item(row,timeline.FRAME_COLUMN_OFFSET+1)).center().x();delta,result,issue=timeline._resolve_drag_delta(timeline.FRAME_COLUMN_OFFSET+1,start,start+6.2*8,False,selected,snapshot);assert delta==7 and result and result.guide_frame==8 and issue is None;assert window.move_effect_selected_keys(selected,delta) and single.layer_transform.tracks["rotation_z"].keyframe_at(8).value==0;_close(window)


def test_snap_helper_performance_fixtures():
    timings={}
    for count in (100,1000,5000):
        visible={TimelineKey(f"layer-{index}","resource","position_x",index%240) for index in range(count)};start=perf_counter();snapshot=collect_snap_targets(visible,set(),120,240);timings[("snapshot",count)]=perf_counter()-start;assert len(snapshot.targets)<=240
    snapshot=collect_snap_targets({TimelineKey(f"t-{index}","resource","position_x",index) for index in range(5000)},set(),2500,6000)
    for count in (100,500):
        keys={TimelineKey(f"s-{index}","resource","position_x",index*2) for index in range(count)};start=perf_counter();compute_batch_snap(snapshot,keys,3.2,3,8,lambda _delta:True);timings[("batch",count)]=perf_counter()-start
    assert max(timings.values())<1.0
