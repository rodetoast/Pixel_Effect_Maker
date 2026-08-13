"""Deterministic nearest-neighbor Resource Composition renderer."""
from __future__ import annotations
from collections import OrderedDict
import numpy as np
from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.frame import empty_pixels
from app.models.project import Project
from app.models.resource_composition import ResourceComposition,CompositionLayer
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import _source_over,render_transformed_source
from app.services.layer_space_transform_service import transform_layer_space_rgba_frame

_CACHE:OrderedDict[tuple,list[np.ndarray]]=OrderedDict()
_CACHE_BYTES=0
_MAX_CACHE_BYTES=256*1024*1024
def invalidate_composition_cache(composition_id=None):
    global _CACHE_BYTES
    if composition_id is None:_CACHE.clear();_CACHE_BYTES=0
    else:
        for key in list(_CACHE):
            if key[0]==composition_id:
                _CACHE_BYTES-=sum(frame.nbytes for frame in _CACHE.pop(key,[]))

def _source(project,layer):
    items=project.source_assets if layer.source_type=="source_asset" else project.animation_clips
    return next((item for item in items if item.id==layer.source_id),None)
def _clip_index(clip,elapsed_ms):
    durations=clip.frame_durations_ms or [max(1,round(1000/clip.fps))]*len(clip.frames);total=sum(durations)
    if clip.loop or clip.playback_mode=="loop":elapsed_ms%=total
    elif elapsed_ms>=total:
        if clip.playback_mode=="once":return None
        return len(clip.frames)-1
    cumulative=0
    for index,duration in enumerate(durations):
        cumulative+=duration
        if elapsed_ms<cumulative:return index
    return len(clip.frames)-1
def _pixels_at(project,composition,layer,frame):
    source=_source(project,layer)
    if source is None:return None
    if isinstance(source,SourceAsset):return source.pixels
    local=max(0,frame-layer.start_frame+layer.source_start_frame);elapsed=local*1000/composition.fps;index=_clip_index(source,elapsed)
    return None if index is None else source.frames[index]

def composition_layer_transform(layer:CompositionLayer,frame:int)->EffectLayerTransform3D:
    """Build the Resource Editor sprite-plane transform without sharing Effect state."""
    position=layer.value("position",frame);scale=layer.value("scale",frame)
    return EffectLayerTransform3D(
        position_x=float(position[0]),position_y=float(position[1]),
        position_z=float(layer.value("position_z",frame)),
        rotation_x=float(layer.value("rotation_x",frame)),
        rotation_y=float(layer.value("rotation_y",frame)),
        # Resource Composition's established `rotation` track is canonical Z.
        rotation_z=float(layer.value("rotation",frame)),
        scale_x=float(scale[0]),scale_y=float(scale[1]),
        opacity=max(0.0,min(1.0,float(layer.value("opacity",frame)))),
        perspective_strength=max(0.0,float(layer.value("perspective_strength",frame))),
    )

def _has_sprite_2_5d(layer:CompositionLayer,frame:int)->bool:
    return any(abs(float(layer.value(name,frame)))>1e-9 for name in ("rotation_x","rotation_y","position_z","perspective_strength"))

def render_composition_frame(project:Project,composition:ResourceComposition,frame:int,preview:bool=False)->np.ndarray:
    if not 0<=frame<composition.frame_count:raise ValueError("composition frame out of range")
    output=empty_pixels(composition.width,composition.height)
    has_solo=preview and any(layer.solo for layer in composition.layers)
    for layer in composition.layers:
        if not layer.visible or frame<layer.start_frame or frame>layer.end_frame:continue
        if has_solo and not layer.solo:continue
        pixels=_pixels_at(project,composition,layer,frame)
        if pixels is None:continue
        position=layer.value("position",frame);rotation=float(layer.value("rotation",frame));scale=layer.value("scale",frame);opacity=float(layer.value("opacity",frame))
        asset=SourceAsset(layer.name,pixels,pivot_x=layer.pivot_x,pivot_y=layer.pivot_y)
        if not _has_sprite_2_5d(layer,frame):
            # Preserve the exact legacy 2D raster path and canonical `rotation` result.
            render_transformed_source(output,asset,position_x=composition.width/2+float(position[0]),position_y=composition.height/2+float(position[1]),rotation=rotation,scale_x=float(scale[0]),scale_y=float(scale[1]),horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=max(0,min(1,opacity)))
        else:
            local=empty_pixels(composition.width,composition.height)
            render_transformed_source(local,asset,position_x=composition.width/2,position_y=composition.height/2,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=1)
            transformed=transform_layer_space_rgba_frame(local,composition_layer_transform(layer,frame),local_z_spin=True)
            _source_over(output,transformed)
    return output
def render_composition_frames(project,composition,use_cache=True):
    global _CACHE_BYTES
    key=(composition.id,composition.revision,composition.width,composition.height,composition.fps,composition.frame_count,id(project))
    if use_cache and key in _CACHE:
        _CACHE.move_to_end(key);return [frame.copy() for frame in _CACHE[key]]
    frames=[render_composition_frame(project,composition,index) for index in range(composition.frame_count)]
    cached=[frame.copy() for frame in frames];byte_size=sum(frame.nbytes for frame in cached)
    previous=_CACHE.pop(key,None)
    if previous is not None:_CACHE_BYTES-=sum(frame.nbytes for frame in previous)
    if byte_size<=_MAX_CACHE_BYTES:
        _CACHE[key]=cached;_CACHE_BYTES+=byte_size
        while _CACHE_BYTES>_MAX_CACHE_BYTES:
            _,removed=_CACHE.popitem(last=False);_CACHE_BYTES-=sum(frame.nbytes for frame in removed)
    return frames
def composition_as_clip(project,composition):
    return AnimationClipAsset(composition.name,render_composition_frames(project,composition),fps=composition.fps,pivot_x=composition.pivot_x,pivot_y=composition.pivot_y,playback_mode="loop" if composition.loop else "hold",loop=composition.loop,source_format="composition",frame_durations_ms=[max(1,round(1000/composition.fps))]*composition.frame_count)
