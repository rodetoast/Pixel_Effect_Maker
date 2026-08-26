"""Pure runtime helpers for screen-space Timeline key snapping."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Callable, Iterable

from app.ui.timeline_multi_key import TimelineKey


SNAP_THRESHOLD_PX = 8.0
SNAP_PLAYHEAD = "playhead"
SNAP_KEYFRAME = "keyframe"
SNAP_START = "start"
SNAP_END = "end"
_PRIORITY = {SNAP_PLAYHEAD: 0, SNAP_KEYFRAME: 1, SNAP_START: 2, SNAP_END: 2}


@dataclass(frozen=True)
class TimelineSnapTarget:
    frame: int
    kind: str


@dataclass(frozen=True)
class TimelineSnapSnapshot:
    targets: tuple[TimelineSnapTarget, ...]
    frame_count: int

    @property
    def frames(self):return tuple(target.frame for target in self.targets)


@dataclass(frozen=True)
class TimelineSnapResult:
    delta: int
    guide_frame: int
    target_kind: str
    distance_px: float


def collect_snap_targets(
    visible_keys: Iterable[TimelineKey],
    selected_keys: Iterable[TimelineKey],
    playhead_frame: int,
    frame_count: int,
) -> TimelineSnapSnapshot:
    """Capture visible target frames, deduped with deterministic kind priority."""

    selected=set(selected_keys);by_frame={}
    for key in visible_keys:
        if key not in selected:by_frame.setdefault(key.frame,SNAP_KEYFRAME)
    count=max(1,int(frame_count));playhead=max(0,min(int(playhead_frame),count-1));by_frame[playhead]=SNAP_PLAYHEAD
    by_frame.setdefault(0,SNAP_START);by_frame.setdefault(count-1,SNAP_END)
    targets=tuple(TimelineSnapTarget(frame,by_frame[frame]) for frame in sorted(by_frame))
    return TimelineSnapSnapshot(targets,count)


def batch_delta_issue(
    keys: Iterable[TimelineKey],
    delta: int,
    frame_count: int,
    occupied_keys: Iterable[TimelineKey],
    duplicate: bool,
) -> str | None:
    """Return boundary/collision for a shared delta without touching model data."""

    selected=set(keys);offset=int(delta);count=max(1,int(frame_count))
    if any(not 0<=key.frame+offset<count for key in selected):return "boundary"
    occupied=set(occupied_keys) if duplicate else set(occupied_keys)-selected
    if any(key.at_frame(key.frame+offset) in occupied for key in selected):return "collision"
    return None


def compute_batch_snap(
    snapshot: TimelineSnapSnapshot,
    keys: Iterable[TimelineKey],
    raw_delta_frames: float,
    proposed_delta: int,
    frame_width: float,
    is_valid: Callable[[int], bool],
    threshold_px: float = SNAP_THRESHOLD_PX,
) -> TimelineSnapResult | None:
    """Find the nearest valid shared delta in screen space using bisect lookup."""

    selected=tuple(sorted(set(keys)));targets=snapshot.targets
    if not selected or not targets:return None
    frames=snapshot.frames;width=max(1.0,float(frame_width));threshold=max(0.0,float(threshold_px));candidates={}
    for key in selected:
        wanted=key.frame+float(raw_delta_frames);index=bisect_left(frames,wanted)
        for candidate_index in (index-1,index,index+1):
            if not 0<=candidate_index<len(targets):continue
            target=targets[candidate_index];delta=target.frame-key.frame;distance=abs(delta-float(raw_delta_frames))*width
            if target.kind in {SNAP_START,SNAP_END}:continue
            if distance>threshold+1e-9:continue
            rank=(distance,_PRIORITY[target.kind],abs(delta-int(proposed_delta)),target.frame,target.kind)
            current=candidates.get(delta)
            if current is None or rank<current[0]:candidates[delta]=(rank,target)
    earliest=min(selected,key=lambda key:key.frame);latest=max(selected,key=lambda key:key.frame)
    for target,key in ((TimelineSnapTarget(0,SNAP_START),earliest),(TimelineSnapTarget(snapshot.frame_count-1,SNAP_END),latest)):
        delta=target.frame-key.frame;distance=abs(delta-float(raw_delta_frames))*width
        if distance<=threshold+1e-9:
            rank=(distance,_PRIORITY[target.kind],abs(delta-int(proposed_delta)),target.frame,target.kind);current=candidates.get(delta)
            if current is None or rank<current[0]:candidates[delta]=(rank,target)
    for delta,(rank,target) in sorted(candidates.items(),key=lambda item:item[1][0]):
        if is_valid(delta):return TimelineSnapResult(delta,target.frame,target.kind,rank[0])
    return None
