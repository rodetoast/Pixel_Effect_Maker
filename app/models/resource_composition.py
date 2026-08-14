"""Timeline-driven reusable resource compositions."""
from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any
from math import isfinite
from uuid import uuid4
from .layer_group import LayerGroup,flatten_hierarchy,layer_node,parent_group,repair_hierarchy
from .layer_parenting import IDENTITY_PARENT_OFFSET,normalize_parent_offset,repair_parent_links

EASINGS={"Linear","Ease In","Ease Out","Ease In/Out"}
PROPERTY_DEFAULTS={
    "position":[0.0,0.0],"rotation":0.0,"scale":[1.0,1.0],"opacity":1.0,
    "position_x":0.0,"position_y":0.0,"position_z":0.0,
    "rotation_x":0.0,"rotation_y":0.0,"rotation_z":0.0,
    "scale_x":1.0,"scale_y":1.0,"perspective_strength":0.0,
    "motion_center_x":0.0,"motion_center_y":0.0,"motion_center_z":0.0,
    "motion_radius_start":0.0,"motion_radius_end":0.0,
    "motion_ellipse_scale_x":1.0,"motion_ellipse_scale_y":1.0,
    "motion_start_angle_degrees":0.0,"motion_turns":1.0,
    "motion_phase_spread_degrees":0.0,"motion_orbit_plane_rotation_degrees":0.0,
    "motion_axis_start":0.0,"motion_axis_end":0.0,
    "motion_perspective_strength":0.0,
}

@dataclass
class Keyframe:
    frame:int;value:Any;easing:str="Linear"
    def __post_init__(self):
        self.frame=int(self.frame)
        if self.frame<0:raise ValueError("keyframe frame must be non-negative")
        if self.easing not in EASINGS:raise ValueError("unsupported keyframe easing")
    def to_dict(self):return {"frame":self.frame,"value":self.value,"easing":self.easing}
    @classmethod
    def from_dict(cls,data):return cls(int(data["frame"]),data["value"],str(data.get("easing","Linear")))

@dataclass
class AnimationTrack:
    property_id:str;default_value:Any;keyframes:list[Keyframe]=field(default_factory=list)
    def __post_init__(self):
        if self.property_id not in PROPERTY_DEFAULTS:raise ValueError("unsupported composition property")
        self._normalize()
    def _normalize(self):
        by_frame={k.frame:k for k in self.keyframes};self.keyframes=sorted(by_frame.values(),key=lambda k:k.frame)
    def set_keyframe(self,frame,value,easing="Linear"):
        self.keyframes.append(Keyframe(frame,value,easing));self._normalize();return next(k for k in self.keyframes if k.frame==frame)
    def keyframe_at(self,frame):return next((key for key in self.keyframes if key.frame==int(frame)),None)
    def has_keyframe(self,frame):return self.keyframe_at(frame) is not None
    def delete_keyframe(self,frame):
        """Delete one key, preserving its value when the track becomes static."""
        key=self.keyframe_at(frame)
        if key is None:return False
        self.keyframes=[item for item in self.keyframes if item.frame!=int(frame)]
        if not self.keyframes:self.default_value=key.value
        return True
    def move_keyframe(self,source_frame,target_frame,frame_count=None):
        """Move a key without overwriting a target key; timeline bounds are clamped."""
        source=int(source_frame);target=int(target_frame)
        if frame_count is not None:target=max(0,min(target,max(0,int(frame_count)-1)))
        if target<0:raise ValueError("keyframe frame must be non-negative")
        key=self.keyframe_at(source)
        if key is None:return False
        if target!=source and self.has_keyframe(target):return False
        key.frame=target;self._normalize();return True
    def evaluate(self,frame):
        if not self.keyframes:return self.default_value
        if frame<=self.keyframes[0].frame:return self.keyframes[0].value
        if frame>=self.keyframes[-1].frame:return self.keyframes[-1].value
        left=self.keyframes[0];right=self.keyframes[-1]
        for a,b in zip(self.keyframes,self.keyframes[1:]):
            if a.frame<=frame<=b.frame:left,right=a,b;break
        amount=(frame-left.frame)/(right.frame-left.frame)
        if left.easing=="Ease In":amount=amount*amount
        elif left.easing=="Ease Out":amount=1-(1-amount)*(1-amount)
        elif left.easing=="Ease In/Out":amount=2*amount*amount if amount<.5 else 1-((-2*amount+2)**2)/2
        def mix(a,b):return float(a)+(float(b)-float(a))*amount
        if isinstance(left.value,(list,tuple)):return [mix(a,b) for a,b in zip(left.value,right.value)]
        return mix(left.value,right.value)
    def to_dict(self):return {"property_id":self.property_id,"default_value":self.default_value,"keyframes":[k.to_dict() for k in self.keyframes]}
    @classmethod
    def from_dict(cls,data):
        keyframes=[Keyframe.from_dict(k) for k in data.get("keyframes",[])]
        if len({key.frame for key in keyframes}) != len(keyframes):
            raise ValueError("keyframe frames must be unique")
        return cls(str(data["property_id"]),data.get("default_value",PROPERTY_DEFAULTS[str(data["property_id"])]),keyframes)

@dataclass
class CompositionLayer:
    name:str;source_type:str;source_id:str;start_frame:int;end_frame:int;source_start_frame:int=0;visible:bool=True;locked:bool=False;solo:bool=False;pivot_x:float=0.0;pivot_y:float=0.0;tracks:dict[str,AnimationTrack]=field(default_factory=dict);id:str=field(default_factory=lambda:uuid4().hex);parent_id:str|None=None;parent_offset:tuple[float,...]=field(default_factory=lambda:IDENTITY_PARENT_OFFSET)
    def __post_init__(self):
        if self.source_type not in {"source_asset","animation_clip"}:raise ValueError("unsupported composition layer source")
        if self.start_frame<0 or self.end_frame<self.start_frame:raise ValueError("invalid composition layer range")
        if self.source_start_frame < 0 or not isfinite(float(self.pivot_x)) or not isfinite(float(self.pivot_y)):
            raise ValueError("invalid composition layer coordinates")
        self.parent_id=None if self.parent_id is None else str(self.parent_id);self.parent_offset=normalize_parent_offset(self.parent_offset)
    def add_property(self,property_id):
        if property_id not in PROPERTY_DEFAULTS:raise ValueError("unsupported composition property")
        return self.tracks.setdefault(property_id,AnimationTrack(property_id,PROPERTY_DEFAULTS[property_id]))
    def remove_property(self,property_id):self.tracks.pop(property_id,None)
    def value(self,property_id,frame):return self.tracks[property_id].evaluate(frame) if property_id in self.tracks else PROPERTY_DEFAULTS[property_id]
    def to_dict(self):return {"id":self.id,"name":self.name,"visible":self.visible,"locked":self.locked,"solo":self.solo,"source_type":self.source_type,"source_id":self.source_id,"start_frame":self.start_frame,"end_frame":self.end_frame,"source_start_frame":self.source_start_frame,"pivot_x":self.pivot_x,"pivot_y":self.pivot_y,"tracks":{k:v.to_dict() for k,v in self.tracks.items()},"parent_id":self.parent_id,"parent_offset":list(self.parent_offset)}
    @classmethod
    def from_dict(cls,data):return cls(id=str(data["id"]),name=str(data["name"]),visible=bool(data.get("visible",True)),locked=bool(data.get("locked",False)),solo=bool(data.get("solo",False)),source_type=str(data["source_type"]),source_id=str(data["source_id"]),start_frame=int(data.get("start_frame",0)),end_frame=int(data["end_frame"]),source_start_frame=int(data.get("source_start_frame",0)),pivot_x=float(data.get("pivot_x",0)),pivot_y=float(data.get("pivot_y",0)),tracks={k:AnimationTrack.from_dict(v) for k,v in data.get("tracks",{}).items()},parent_id=None if data.get("parent_id") is None else str(data.get("parent_id")),parent_offset=normalize_parent_offset(data.get("parent_offset")))

@dataclass
class ResourceComposition:
    name:str;width:int=64;height:int=64;fps:int=12;frame_count:int=12;loop:bool=True;layers:list[CompositionLayer]=field(default_factory=list);background_mode:str="transparent";pivot_x:float|None=None;pivot_y:float|None=None;revision:int=0;id:str=field(default_factory=lambda:uuid4().hex);groups:list[LayerGroup]=field(default_factory=list);root_order:list[dict[str,str]]=field(default_factory=list)
    def __post_init__(self):
        if not 1<=self.width<=1024 or not 1<=self.height<=1024:raise ValueError("composition size must be 1..1024")
        if not 1<=self.fps<=120 or not 1<=self.frame_count<=512:raise ValueError("invalid composition timing")
        if self.background_mode!="transparent":raise ValueError("only transparent compositions are supported")
        if self.pivot_x is None:self.pivot_x=self.width/2
        if self.pivot_y is None:self.pivot_y=self.height/2
        if not isfinite(float(self.pivot_x)) or not isfinite(float(self.pivot_y)):
            raise ValueError("composition pivot must be finite")
        if len({layer.id for layer in self.layers})!=len(self.layers):raise ValueError("composition layer IDs must be unique")
        self.repair_hierarchy()
    def touch(self):self.revision+=1
    def repair_hierarchy(self):
        leaf_ids=[layer.id for layer in self.layers]
        if not self.groups:self.root_order=[layer_node(identifier) for identifier in leaf_ids]
        self.groups,self.root_order=repair_hierarchy(leaf_ids,self.groups,self.root_order)
        self.sync_flat_order()
        repair_parent_links(self.layers)
    def sync_flat_order(self):
        by_id={layer.id:layer for layer in self.layers};ordered=flatten_hierarchy(self.groups,self.root_order)
        self.layers=[by_id[value] for value in ordered if value in by_id]
    def flatten_layer_ids(self):return flatten_hierarchy(self.groups,self.root_order)
    def group_by_id(self,identifier):return next((group for group in self.groups if group.id==identifier),None)
    def parent_group(self,leaf_id):return parent_group(self.groups,leaf_id)
    def effective_visible(self,leaf):
        group=self.parent_group(leaf.id);return leaf.visible and (group is None or group.visible)
    def effective_locked(self,leaf):
        group=self.parent_group(leaf.id);return leaf.locked or bool(group and group.locked)
    def preview_solo_active(self):return any(layer.solo for layer in self.layers) or any(group.solo for group in self.groups)
    def preview_soloed(self,leaf):
        group=self.parent_group(leaf.id);return leaf.solo or bool(group and group.solo)
    def to_dict(self):
        self.repair_hierarchy();return {"id":self.id,"name":self.name,"width":self.width,"height":self.height,"fps":self.fps,"frame_count":self.frame_count,"loop":self.loop,"background_mode":self.background_mode,"pivot_x":self.pivot_x,"pivot_y":self.pivot_y,"revision":self.revision,"layers":[l.to_dict() for l in self.layers],"groups":[group.to_dict() for group in self.groups],"root_order":self.root_order}
    @classmethod
    def from_dict(cls,data):return cls(id=str(data["id"]),name=str(data["name"]),width=int(data["width"]),height=int(data["height"]),fps=int(data["fps"]),frame_count=int(data["frame_count"]),loop=bool(data.get("loop",True)),background_mode=str(data.get("background_mode","transparent")),pivot_x=float(data.get("pivot_x",int(data["width"])/2)),pivot_y=float(data.get("pivot_y",int(data["height"])/2)),revision=int(data.get("revision",0)),layers=[CompositionLayer.from_dict(v) for v in data.get("layers",[])],groups=[LayerGroup.from_dict(v) for v in data.get("groups",[])],root_order=list(data.get("root_order",[])) if isinstance(data.get("root_order",[]),list) else [])
