"""Deterministic nearest-neighbor Resource Composition renderer."""
from __future__ import annotations
from collections import OrderedDict
import math
import numpy as np
from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.frame import empty_pixels
from app.models.project import Project
from app.models.resource_composition import ResourceComposition,CompositionLayer
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import _source_over,render_transformed_source,_homography_from_unit_square,_render_affine_source
from app.services.layer_space_transform_service import projected_layer_quad
from app.services.layer_parenting_service import resource_local_affine,resolve_world_affines,local_only_transform
from app.models.layer_parenting import parent_offset_is_identity

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
    """Final output always clips after transformation to current Composition bounds."""
    return _render_region(project,composition,frame,preview,(0,0,composition.width,composition.height))

def render_editor_region(project,composition,frame,region):
    """Editor-only visible composition-space region; never used by export/cache."""
    x,y,width,height=map(int,region)
    if width<1 or height<1 or width*height>16_777_216:
        raise ValueError("editor region exceeds viewport allocation budget")
    return _render_region(project,composition,frame,True,(x,y,width,height))

def _render_region(project,composition,frame,preview,region):
    if not 0<=frame<composition.frame_count:raise ValueError("composition frame out of range")
    left,top,width,height=region
    output=empty_pixels(width,height)
    has_solo=preview and composition.preview_solo_active()
    world_affines=resolve_world_affines(composition.layers,frame,lambda layer,value:resource_local_affine(layer,value,composition))
    for layer in composition.layers:
        if not composition.effective_visible(layer) or frame<layer.start_frame or frame>layer.end_frame:continue
        if has_solo and not composition.preview_soloed(layer):continue
        pixels=_pixels_at(project,composition,layer,frame)
        if pixels is None:continue
        position=layer.value("position",frame);rotation=float(layer.value("rotation",frame));scale=layer.value("scale",frame);opacity=float(layer.value("opacity",frame))
        asset=SourceAsset(layer.name,pixels,pivot_x=layer.pivot_x,pivot_y=layer.pivot_y)
        parented=layer.parent_id is not None or not parent_offset_is_identity(layer.parent_offset)
        if not parented and not _has_sprite_2_5d(layer,frame):
            # Preserve the exact legacy 2D raster path and canonical `rotation` result.
            if (left or top) and (abs(math.remainder(rotation,360))>1e-9 or abs(scale[0]-1)>1e-9 or abs(scale[1]-1)>1e-9):
                _render_affine_source(output,asset,composition.width/2+float(position[0]),composition.height/2+float(position[1]),rotation,float(scale[0]),float(scale[1]),max(0,min(1,opacity)),canvas_origin=(left,top))
                continue
            render_transformed_source(output,asset,position_x=composition.width/2+float(position[0])-left,position_y=composition.height/2+float(position[1])-top,rotation=rotation,scale_x=float(scale[0]),scale_y=float(scale[1]),horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=max(0,min(1,opacity)))
        else:
            transform=composition_layer_transform(layer,frame)
            _draw_projected_source(output,asset,composition,local_only_transform(transform,frame) if parented else transform,world_affines[layer.id] if parented else None,left,top)
    return output

def _draw_projected_source(output,asset,composition,transform,post_affine,left,top):
    """Project source cells directly: no pre-transform Composition-sized crop.

    Intersect the destination before allocating sampling grids, so distant or
    enormous transformed bounds cost no more than the visible render target.
    """
    if transform.opacity<=0:return
    cx=composition.width/2-asset.pivot_x;cy=composition.height/2-asset.pivot_y
    source=asset.pixels
    # Retain the established pixel lattice for fractional source pivots without
    # clipping it to output dimensions before the world transform.
    if abs(cx-round(cx))>1e-9 or abs(cy-round(cy))>1e-9:
        lx=math.floor(cx);ly=math.floor(cy)
        local=empty_pixels(asset.width+2,asset.height+2)
        render_transformed_source(local,asset,position_x=composition.width/2-lx,position_y=composition.height/2-ly,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=1)
        source=local;cx=lx;cy=ly
    ys,xs=np.nonzero(source[...,3])
    if not len(xs):return
    xlo,xhi=int(xs.min()),int(xs.max())+1;ylo,yhi=int(ys.min()),int(ys.max())+1
    source=source[ylo:yhi,xlo:xhi]
    quad,valid=projected_layer_quad((cx+xlo,cy+ylo,cx+xhi,cy+yhi),transform,composition.width,composition.height,local_z_spin=True,post_affine=post_affine)
    if not valid.all():return
    height,width=output.shape[:2]
    x0=max(0,math.floor(quad[:,0].min())-left);x1=min(width,math.ceil(quad[:,0].max())-left)
    y0=max(0,math.floor(quad[:,1].min())-top);y1=min(height,math.ceil(quad[:,1].max())-top)
    if x1<=x0 or y1<=y0:return
    try:inverse=np.linalg.inv(_homography_from_unit_square(quad))
    except np.linalg.LinAlgError:return
    gx,gy=np.meshgrid(np.arange(x0,x1)+left+.5,np.arange(y0,y1)+top+.5)
    mapped=np.stack((gx,gy,np.ones_like(gx)),axis=-1)@inverse.T
    denominator=mapped[...,2];safe=np.where(np.abs(denominator)>1e-10,denominator,1)
    u=mapped[...,0]/safe;v=mapped[...,1]/safe
    inside=(np.abs(denominator)>1e-10)&(u>=0)&(u<1)&(v>=0)&(v<1)
    sx=np.floor(np.where(inside,u,0)*source.shape[1]).astype(int)
    sy=np.floor(np.where(inside,v,0)*source.shape[0]).astype(int)
    sampled=source[sy,sx].copy();sampled[~inside]=0
    if transform.opacity<1:sampled[...,3]=np.rint(sampled[...,3]*transform.opacity).astype(np.uint8)
    _source_over(output[y0:y1,x0:x1],sampled)
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
