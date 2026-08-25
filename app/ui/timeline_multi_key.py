"""Runtime-only selection and atomic mutation helpers for Timeline keys."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Mapping

from app.models.resource_composition import AnimationTrack, EASINGS


@dataclass(frozen=True, order=True)
class TimelineKey:
    layer_id: str
    scope: str
    property_id: str
    frame: int

    def __post_init__(self):
        object.__setattr__(self, "layer_id", str(self.layer_id))
        object.__setattr__(self, "scope", str(self.scope))
        object.__setattr__(self, "property_id", str(self.property_id))
        object.__setattr__(self, "frame", int(self.frame))

    @property
    def track_id(self) -> tuple[str, str, str]:
        return self.layer_id, self.scope, self.property_id

    def at_frame(self, frame: int) -> "TimelineKey":
        return TimelineKey(self.layer_id, self.scope, self.property_id, int(frame))


class TimelineKeySelection:
    """Small selection model; it never owns or mutates project data."""

    def __init__(self):
        self.selected: set[TimelineKey] = set()
        self.primary: TimelineKey | None = None
        self.anchor: TimelineKey | None = None

    def clear(self) -> bool:
        changed=bool(self.selected);self.selected.clear();self.primary=None;self.anchor=None;return changed

    def click(self,key: TimelineKey,*,ctrl=False,shift=False,track_keys: Iterable[TimelineKey]=()) -> None:
        if shift and self.anchor is not None:
            if self.anchor.track_id==key.track_id:
                low,high=sorted((self.anchor.frame,key.frame));self.selected={value for value in track_keys if value.track_id==key.track_id and low<=value.frame<=high}
            else:self.selected.add(key)
            self.primary=key;return
        if ctrl:
            if key in self.selected:
                self.selected.remove(key)
                if self.primary==key:self.primary=max(self.selected,key=lambda value:(value.frame,value.track_id),default=None)
            else:self.selected.add(key);self.primary=key;self.anchor=key
            if not self.selected:self.primary=None
            return
        self.selected={key};self.primary=key;self.anchor=key

    def marquee(self,keys: Iterable[TimelineKey],*,ctrl=False) -> None:
        values=set(keys)
        self.selected=self.selected.symmetric_difference(values) if ctrl else values
        self.primary=max(values,key=lambda value:(value.frame,value.track_id),default=self.primary if self.primary in self.selected else None)
        if self.primary is not None:self.anchor=self.primary

    def repair(self,visible_keys: Iterable[TimelineKey]) -> None:
        visible=set(visible_keys);self.selected&=visible
        if self.primary not in self.selected:self.primary=max(self.selected,key=lambda value:(value.frame,value.track_id),default=None)
        if self.anchor not in visible:self.anchor=self.primary

    def remap_frames(self,delta: int) -> None:
        mapping={key:key.at_frame(key.frame+int(delta)) for key in self.selected};self.selected=set(mapping.values());self.primary=mapping.get(self.primary);self.anchor=mapping.get(self.anchor,self.primary)


def selected_track_ids(keys: Iterable[TimelineKey]) -> set[tuple[str,str,str]]:
    return {key.track_id for key in keys}


def clamp_group_delta(keys: Iterable[TimelineKey],delta: int,frame_count: int) -> int:
    values=list(keys)
    if not values:return 0
    requested=int(delta);last=max(0,int(frame_count)-1)
    return max(-min(key.frame for key in values),min(requested,last-max(key.frame for key in values)))


def move_keys_atomic(tracks: Mapping[tuple[str,str,str],AnimationTrack],keys: Iterable[TimelineKey],delta: int,frame_count: int) -> tuple[bool,int]:
    """Move every selected key by one clamped delta or reject the whole edit."""

    values=set(keys);actual=clamp_group_delta(values,delta,frame_count)
    if not values or actual==0:return False,actual
    by_track: dict[tuple[str,str,str],set[int]]={}
    for key in values:by_track.setdefault(key.track_id,set()).add(key.frame)
    for track_id,frames in by_track.items():
        track=tracks.get(track_id)
        if track is None or any(track.keyframe_at(frame) is None for frame in frames):return False,actual
        occupied={item.frame for item in track.keyframes if item.frame not in frames}
        if any(frame+actual in occupied for frame in frames):return False,actual
    for track_id,frames in by_track.items():
        track=tracks[track_id]
        for keyframe in track.keyframes:
            if keyframe.frame in frames:keyframe.frame+=actual
        track._normalize()
    return True,actual


def delete_keys(tracks: Mapping[tuple[str,str,str],AnimationTrack],keys: Iterable[TimelineKey]) -> int:
    """Delete selected keys, preserving the latest deleted value for static tracks."""

    by_track: dict[tuple[str,str,str],set[int]]={}
    for key in set(keys):by_track.setdefault(key.track_id,set()).add(key.frame)
    deleted=0
    for track_id,frames in by_track.items():
        track=tracks.get(track_id)
        if track is None:continue
        existing=[item for item in track.keyframes if item.frame in frames]
        if not existing:continue
        remaining=[item for item in track.keyframes if item.frame not in frames]
        if not remaining:track.default_value=deepcopy(max(existing,key=lambda item:item.frame).value)
        track.keyframes=remaining;deleted+=len(existing)
    return deleted


def set_keys_easing(tracks: Mapping[tuple[str,str,str],AnimationTrack],keys: Iterable[TimelineKey],easing: str) -> int:
    if easing not in EASINGS:raise ValueError("unsupported keyframe easing")
    changed=0
    for key in set(keys):
        track=tracks.get(key.track_id);item=track.keyframe_at(key.frame) if track else None
        if item is not None and item.easing!=easing:item.easing=easing;changed+=1
    return changed
