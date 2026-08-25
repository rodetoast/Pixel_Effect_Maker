"""Runtime-only selection and atomic mutation helpers for Timeline keys."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from math import isfinite
from typing import Iterable, Mapping

from app.models.resource_composition import AnimationTrack, EASINGS


TIMELINE_KEY_MIME = "application/x-pixel-effect-maker-timeline-keys"
TIMELINE_CLIPBOARD_VERSION = 1
TIMELINE_KINDS = {"resource", "effect"}
PASTE_INVALID = "invalid"
PASTE_INCOMPATIBLE = "incompatible"
PASTE_MISSING_TRACK = "missing_track"
PASTE_OUT_OF_RANGE = "out_of_range"
PASTE_COLLISION = "collision"


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


def _clipboard_value_is_valid(value) -> bool:
    if value is None or isinstance(value,(str,bool)):return True
    if isinstance(value,(int,float)):return not isinstance(value,bool) and isfinite(float(value))
    if isinstance(value,(list,tuple)):return all(_clipboard_value_is_valid(part) for part in value)
    if isinstance(value,dict):return all(isinstance(key,str) and _clipboard_value_is_valid(part) for key,part in value.items())
    return False


def build_timeline_clipboard_payload(
    timeline_kind: str,
    context_id: str,
    keys: Iterable[TimelineKey],
    tracks: Mapping[tuple[str,str,str],AnimationTrack],
    primary: TimelineKey | None = None,
) -> bytes | None:
    """Snapshot selected keys into a versioned, relative-frame JSON payload."""

    kind=str(timeline_kind);context=str(context_id);selected=sorted(set(keys),key=lambda key:(key.frame,key.track_id))
    if kind not in TIMELINE_KINDS or not context or not selected:return None
    anchor=min(key.frame for key in selected);entries=[];primary_index=None
    for key in selected:
        track=tracks.get(key.track_id);item=track.keyframe_at(key.frame) if track else None
        if item is None or item.easing not in EASINGS or not _clipboard_value_is_valid(item.value):return None
        entry={"layer_id":key.layer_id,"scope":key.scope,"property_id":key.property_id,"relative_frame":key.frame-anchor,"value":deepcopy(item.value),"easing":item.easing}
        if key==primary:primary_index=len(entries)
        entries.append(entry)
    payload={"version":TIMELINE_CLIPBOARD_VERSION,"timeline_kind":kind,"context_id":context,"anchor_frame":anchor,"primary_index":primary_index,"entries":entries}
    try:return json.dumps(payload,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    except (TypeError,ValueError):return None


def decode_timeline_clipboard_payload(data) -> dict | None:
    """Strictly validate untrusted custom clipboard bytes."""

    try:
        raw=bytes(data);payload=json.loads(raw.decode("utf-8"))
    except (TypeError,ValueError,UnicodeDecodeError,json.JSONDecodeError):return None
    if not isinstance(payload,dict) or payload.get("version")!=TIMELINE_CLIPBOARD_VERSION:return None
    kind=payload.get("timeline_kind");context=payload.get("context_id");anchor=payload.get("anchor_frame");primary=payload.get("primary_index");entries=payload.get("entries")
    if kind not in TIMELINE_KINDS or not isinstance(context,str) or not context or not isinstance(anchor,int) or isinstance(anchor,bool) or anchor<0:return None
    if not isinstance(entries,list) or not entries:return None
    if primary is not None and (not isinstance(primary,int) or isinstance(primary,bool) or not 0<=primary<len(entries)):return None
    seen=set();minimum=None
    for entry in entries:
        if not isinstance(entry,dict) or set(entry)!={"layer_id","scope","property_id","relative_frame","value","easing"}:return None
        layer_id=entry["layer_id"];scope=entry["scope"];property_id=entry["property_id"];relative=entry["relative_frame"]
        if not all(isinstance(value,str) and value for value in (layer_id,scope,property_id)):return None
        if kind=="resource" and scope!="resource":return None
        if kind=="effect" and scope not in {"effect_transform","effect_motion"}:return None
        if not isinstance(relative,int) or isinstance(relative,bool) or relative<0:return None
        if entry["easing"] not in EASINGS or not _clipboard_value_is_valid(entry["value"]):return None
        identity=(layer_id,scope,property_id,relative)
        if identity in seen:return None
        seen.add(identity);minimum=relative if minimum is None else min(minimum,relative)
    if minimum!=0:return None
    return deepcopy(payload)


def read_timeline_clipboard_payload() -> dict | None:
    from PySide6.QtWidgets import QApplication
    mime=QApplication.clipboard().mimeData()
    return decode_timeline_clipboard_payload(mime.data(TIMELINE_KEY_MIME)) if mime and mime.hasFormat(TIMELINE_KEY_MIME) else None


def write_timeline_clipboard_payload(data: bytes) -> bool:
    from PySide6.QtCore import QMimeData
    from PySide6.QtWidgets import QApplication
    if decode_timeline_clipboard_payload(data) is None:return False
    mime=QMimeData();mime.setData(TIMELINE_KEY_MIME,data);QApplication.clipboard().setMimeData(mime);return True


def timeline_clipboard_matches(timeline_kind: str,context_id: str | None=None) -> bool:
    payload=read_timeline_clipboard_payload()
    return bool(payload and payload["timeline_kind"]==timeline_kind and (context_id is None or payload["context_id"]==context_id))


def paste_timeline_keys_atomic(
    tracks: Mapping[tuple[str,str,str],AnimationTrack],
    payload: dict | None,
    timeline_kind: str,
    context_id: str,
    playhead_frame: int,
    frame_count: int,
) -> tuple[str | None,set[TimelineKey],TimelineKey | None]:
    """Validate then create all destination keys, or leave every track untouched."""

    if not isinstance(payload,dict):return PASTE_INVALID,set(),None
    try:validated=decode_timeline_clipboard_payload(json.dumps(payload,allow_nan=False).encode("utf-8"))
    except (TypeError,ValueError):validated=None
    if validated is None:return PASTE_INVALID,set(),None
    payload=validated
    if payload["timeline_kind"]!=timeline_kind or payload["context_id"]!=context_id:return PASTE_INCOMPATIBLE,set(),None
    anchor=int(playhead_frame);count=int(frame_count)
    destinations=[]
    for entry in payload["entries"]:
        frame=anchor+entry["relative_frame"]
        if frame<0 or frame>=count:return PASTE_OUT_OF_RANGE,set(),None
        key=TimelineKey(entry["layer_id"],entry["scope"],entry["property_id"],frame);track=tracks.get(key.track_id)
        if track is None:return PASTE_MISSING_TRACK,set(),None
        if track.keyframe_at(frame) is not None:return PASTE_COLLISION,set(),None
        destinations.append((key,track,entry))
    if len({key for key,_track,_entry in destinations})!=len(destinations):return PASTE_INVALID,set(),None
    for key,track,entry in destinations:track.set_keyframe(key.frame,deepcopy(entry["value"]),entry["easing"])
    selected={key for key,_track,_entry in destinations};primary_index=payload.get("primary_index");primary=destinations[primary_index][0] if primary_index is not None else min(selected,key=lambda key:(key.frame,key.track_id))
    return None,selected,primary
