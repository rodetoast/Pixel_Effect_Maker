from time import perf_counter

from app.models.resource_composition import AnimationTrack
from app.ui.timeline_multi_key import TimelineKey,TimelineKeySelection,move_keys_atomic


def _keys(count):return [TimelineKey(f"layer-{index%10}","resource",f"property-{index%5}",index) for index in range(count)]


def test_selection_and_marquee_scale_to_one_thousand_visible_keys():
    visible=_keys(1000);selection=TimelineKeySelection();started=perf_counter();selection.marquee(visible[::2]);marquee_ms=(perf_counter()-started)*1000;started=perf_counter();selection.repair(visible);repair_ms=(perf_counter()-started)*1000
    assert len(selection.selected)==500 and marquee_ms<100 and repair_ms<100


def test_one_hundred_key_drop_uses_only_track_snapshots():
    track=AnimationTrack("rotation",0.0)
    for frame in range(100):track.set_keyframe(frame,float(frame))
    keys={TimelineKey("layer","resource","rotation",frame) for frame in range(100)};started=perf_counter();changed,delta=move_keys_atomic({("layer","resource","rotation"):track},keys,50,200);elapsed_ms=(perf_counter()-started)*1000
    assert changed and delta==50 and track.keyframes[0].frame==50 and track.keyframes[-1].frame==149 and elapsed_ms<100
