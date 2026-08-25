from copy import deepcopy

from app.models.resource_composition import AnimationTrack
from app.ui.timeline_multi_key import (
    TimelineKey, TimelineKeySelection, delete_keys, move_keys_atomic, set_keys_easing,
)


def _track(property_id,frames):
    track=AnimationTrack(property_id,0.0)
    for frame in frames:track.set_keyframe(frame,float(frame),"Linear")
    return track


def test_click_ctrl_shift_and_primary_selection_are_runtime_only():
    keys=[TimelineKey("a","resource","rotation",frame) for frame in (1,4,8,11)];selection=TimelineKeySelection();selection.click(keys[0],track_keys=keys);assert selection.selected=={keys[0]} and selection.primary==keys[0]
    selection.click(keys[2],ctrl=True,track_keys=keys);assert selection.selected=={keys[0],keys[2]} and selection.primary==keys[2]
    selection.click(keys[0],ctrl=True,track_keys=keys);assert selection.selected=={keys[2]}
    selection.click(keys[0],track_keys=keys);selection.click(keys[2],shift=True,track_keys=keys);assert selection.selected==set(keys[:3]) and selection.primary==keys[2]


def test_cross_track_shift_is_additive():
    a=TimelineKey("a","resource","rotation",1);b=TimelineKey("a","resource","opacity",4);selection=TimelineKeySelection();selection.click(a);selection.click(b,shift=True);assert selection.selected=={a,b} and selection.primary==b


def test_atomic_move_preserves_distance_clamps_and_rejects_collision():
    a=_track("rotation",(1,4,8));b=_track("opacity",(2,7,10));tracks={("a","resource","rotation"):a,("b","resource","opacity"):b};keys={TimelineKey("a","resource","rotation",1),TimelineKey("a","resource","rotation",4),TimelineKey("b","resource","opacity",2)}
    changed,delta=move_keys_atomic(tracks,keys,3,12);assert changed and delta==3 and [key.frame for key in a.keyframes]==[4,7,8] and [key.frame for key in b.keyframes]==[5,7,10]
    snapshot=deepcopy(tracks);blocked,delta=move_keys_atomic(tracks,{TimelineKey("a","resource","rotation",4),TimelineKey("a","resource","rotation",7)},1,12);assert not blocked and tracks==snapshot
    edge=_track("rotation",(1,5,9));changed,delta=move_keys_atomic({("a","resource","rotation"):edge},{TimelineKey("a","resource","rotation",1),TimelineKey("a","resource","rotation",9)},-20,12);assert changed and delta==-1 and [key.frame for key in edge.keyframes]==[0,5,8]


def test_delete_preserves_latest_value_when_track_becomes_static():
    track=_track("rotation",(1,4,8));keys={TimelineKey("a","resource","rotation",frame) for frame in (1,4,8)};assert delete_keys({("a","resource","rotation"):track},keys)==3;assert not track.keyframes and track.default_value==8.0


def test_batch_easing_is_heterogeneous_and_noop_safe():
    a=_track("rotation",(1,4));b=_track("opacity",(2,));tracks={("a","resource","rotation"):a,("b","resource","opacity"):b};keys={TimelineKey("a","resource","rotation",1),TimelineKey("b","resource","opacity",2)}
    assert set_keys_easing(tracks,keys,"Ease In/Out")==2;assert a.keyframe_at(1).easing==b.keyframe_at(2).easing=="Ease In/Out";assert set_keys_easing(tracks,keys,"Ease In/Out")==0
