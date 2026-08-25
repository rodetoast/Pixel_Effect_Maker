from time import perf_counter
import pytest

from app.models.resource_composition import AnimationTrack
from app.ui.timeline_multi_key import TimelineKey,TimelineKeySelection,build_timeline_clipboard_payload,decode_timeline_clipboard_payload,move_keys_atomic,paste_timeline_keys_atomic


def _keys(count):return [TimelineKey(f"layer-{index%10}","resource",f"property-{index%5}",index) for index in range(count)]


def test_selection_and_marquee_scale_to_one_thousand_visible_keys():
    visible=_keys(1000);selection=TimelineKeySelection();started=perf_counter();selection.marquee(visible[::2]);marquee_ms=(perf_counter()-started)*1000;started=perf_counter();selection.repair(visible);repair_ms=(perf_counter()-started)*1000
    assert len(selection.selected)==500 and marquee_ms<100 and repair_ms<100


def test_one_hundred_key_drop_uses_only_track_snapshots():
    track=AnimationTrack("rotation",0.0)
    for frame in range(100):track.set_keyframe(frame,float(frame))
    keys={TimelineKey("layer","resource","rotation",frame) for frame in range(100)};started=perf_counter();changed,delta=move_keys_atomic({("layer","resource","rotation"):track},keys,50,200);elapsed_ms=(perf_counter()-started)*1000
    assert changed and delta==50 and track.keyframes[0].frame==50 and track.keyframes[-1].frame==149 and elapsed_ms<100


@pytest.mark.parametrize("count",[10,100,500])
def test_clipboard_copy_and_paste_scale_without_project_round_trip(count):
    source=AnimationTrack("rotation",0.0)
    for frame in range(count):source.set_keyframe(frame,float(frame),"Ease In/Out" if frame%2 else "Linear")
    keys={TimelineKey("layer","resource","rotation",frame) for frame in range(count)};started=perf_counter();data=build_timeline_clipboard_payload("resource","ctx",keys,{("layer","resource","rotation"):source});copy_ms=(perf_counter()-started)*1000;payload=decode_timeline_clipboard_payload(data);destination=AnimationTrack("rotation",0.0);started=perf_counter();issue,pasted,_primary=paste_timeline_keys_atomic({("layer","resource","rotation"):destination},payload,"resource","ctx",0,count+1);paste_ms=(perf_counter()-started)*1000
    assert issue is None and len(pasted)==count and destination.keyframes[-1].value==float(count-1) and copy_ms<150 and paste_ms<150
