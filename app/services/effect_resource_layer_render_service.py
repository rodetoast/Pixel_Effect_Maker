"""Render dispatch for unified Effect Resource Layers."""

from __future__ import annotations
from collections import OrderedDict

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.services.effect_composition_layer_render_service import (
    apply_effect_composition_layer,
    render_effect_composition_layer,
)
from app.services.particle_render_service import apply_particle_frames, render_particle_frame, render_particle_frames
from app.services.effect_layer_transform_3d_render_service import transform_rgba_frame

_BASE_CACHE: OrderedDict[str, tuple[tuple, list]] = OrderedDict()
_TRANSFORM_CACHE: OrderedDict[tuple, object] = OrderedDict()
_BASE_CACHE_BYTES=0
_TRANSFORM_CACHE_BYTES=0
_MAX_BASE_CACHE_BYTES=256*1024*1024
_MAX_TRANSFORM_CACHE_BYTES=128*1024*1024


def _frames_bytes(frames) -> int:return sum(frame.nbytes for frame in frames)


def _put_base(layer_id: str,key: tuple,frames) -> None:
    global _BASE_CACHE_BYTES
    previous=_BASE_CACHE.pop(layer_id,None)
    if previous is not None:_BASE_CACHE_BYTES-=_frames_bytes(previous[1])
    size=_frames_bytes(frames)
    if size>_MAX_BASE_CACHE_BYTES:return
    _BASE_CACHE[layer_id]=(key,frames);_BASE_CACHE_BYTES+=size
    while _BASE_CACHE_BYTES>_MAX_BASE_CACHE_BYTES:
        _,removed=_BASE_CACHE.popitem(last=False);_BASE_CACHE_BYTES-=_frames_bytes(removed[1])


def _put_transform(key: tuple,frame) -> None:
    global _TRANSFORM_CACHE_BYTES
    previous=_TRANSFORM_CACHE.pop(key,None)
    if previous is not None:_TRANSFORM_CACHE_BYTES-=previous.nbytes
    if frame.nbytes>_MAX_TRANSFORM_CACHE_BYTES:return
    _TRANSFORM_CACHE[key]=frame;_TRANSFORM_CACHE_BYTES+=frame.nbytes
    while _TRANSFORM_CACHE_BYTES>_MAX_TRANSFORM_CACHE_BYTES:
        _,removed=_TRANSFORM_CACHE.popitem(last=False);_TRANSFORM_CACHE_BYTES-=removed.nbytes


def _resource_revisions(project) -> tuple:
    return tuple((item.id,item.revision) for item in project.resource_compositions)


def _base_key(project, layer: EffectResourceLayer) -> tuple:
    settings = layer.particle_settings.to_dict() if layer.placement_mode == PLACEMENT_PARTICLE else layer.single_settings.to_dict()
    return (id(project),layer.placement_mode,repr(settings),project.width,project.height,project.fps,_resource_revisions(project))


def effect_resource_layer_base_frame_key(project, layer: EffectResourceLayer, frame: int) -> tuple:
    """Describe a base frame without forcing particle/composition rendering."""
    index=max(0,int(frame))
    cached=_BASE_CACHE.get(layer.id)
    if cached is not None and cached[0]==_base_key(project,layer) and cached[1]:
        index=min(index,len(cached[1])-1)
    return (layer.id,_base_key(project,layer),index)


def _transform_values(layer: EffectResourceLayer, frame: int) -> tuple:
    value=layer.layer_transform.evaluated(frame)
    return tuple(getattr(value,name) for name in ("position_x","position_y","position_z","rotation_x","rotation_y","rotation_z","scale_x","scale_y","opacity","pivot_x","pivot_y","perspective_strength"))


def invalidate_effect_resource_layer_base(layer_id: str | None = None) -> None:
    global _BASE_CACHE_BYTES,_TRANSFORM_CACHE_BYTES
    if layer_id is None:
        _BASE_CACHE.clear();_TRANSFORM_CACHE.clear();_BASE_CACHE_BYTES=0;_TRANSFORM_CACHE_BYTES=0;return
    removed=_BASE_CACHE.pop(layer_id,None)
    if removed is not None:_BASE_CACHE_BYTES-=_frames_bytes(removed[1])
    for key in list(_TRANSFORM_CACHE):
        if key[0]==layer_id:_TRANSFORM_CACHE_BYTES-=_TRANSFORM_CACHE.pop(key).nbytes


def render_effect_resource_layer_base(project, layer: EffectResourceLayer):
    key=_base_key(project,layer);cached=_BASE_CACHE.get(layer.id)
    if cached is not None and cached[0]==key:
        _BASE_CACHE.move_to_end(layer.id);return cached[1]
    if layer.placement_mode == PLACEMENT_PARTICLE:
        frames=render_particle_frames(project,layer.as_particle_emitter())
    else:
        frames=render_effect_composition_layer(project,layer.as_composition_layer())
    _put_base(layer.id,key,frames)
    for cache_key in list(_TRANSFORM_CACHE):
        if cache_key[0]==layer.id:_TRANSFORM_CACHE.pop(cache_key,None)
    return frames


def render_effect_resource_layer_base_frame(project, layer: EffectResourceLayer, frame: int):
    """Return a stable base frame and token without applying the common transform."""
    frames=render_effect_resource_layer_base(project,layer)
    if not frames:return None,None
    index=max(0,min(int(frame),len(frames)-1))
    return frames[index],effect_resource_layer_base_frame_key(project,layer,index)


def render_effect_resource_layer_frame(project,layer: EffectResourceLayer,frame: int):
    base=render_effect_resource_layer_base(project,layer)
    if not base:return None
    frame=max(0,min(int(frame),len(base)-1));base_key=_base_key(project,layer);key=(layer.id,base_key,frame,_transform_values(layer,frame))
    cached=_TRANSFORM_CACHE.get(key)
    if cached is None:
        for cache_key in list(_TRANSFORM_CACHE):
            if cache_key[:3]==key[:3]:
                global _TRANSFORM_CACHE_BYTES
                _TRANSFORM_CACHE_BYTES-=_TRANSFORM_CACHE.pop(cache_key).nbytes
        cached=transform_rgba_frame(base[frame],layer.layer_transform,frame);_put_transform(key,cached)
    else:_TRANSFORM_CACHE.move_to_end(key)
    return cached


def render_effect_resource_layer_current_frame(project, layer: EffectResourceLayer, frame: int):
    """Render one exact particle frame without materializing its output sequence."""
    if layer.placement_mode != PLACEMENT_PARTICLE:
        return render_effect_resource_layer_frame(project,layer,frame)
    base=render_particle_frame(project,layer.as_particle_emitter(),int(frame))
    return transform_rgba_frame(base,layer.layer_transform,int(frame))


def render_effect_resource_layer_current_base_frame(project, layer: EffectResourceLayer, frame: int):
    """Render one exact untransformed frame for the shared Canvas proxy."""
    if layer.placement_mode == PLACEMENT_PARTICLE:
        return render_particle_frame(project, layer.as_particle_emitter(), int(frame))
    base, _ = render_effect_resource_layer_base_frame(project, layer, int(frame))
    return base


def render_effect_resource_layer(project, layer: EffectResourceLayer):
    frames=render_effect_resource_layer_base(project,layer)
    return [render_effect_resource_layer_frame(project,layer,index) for index in range(len(frames))]


def apply_effect_resource_layer_current_frame(project,layer: EffectResourceLayer,frame: int):
    generated=next((item for item in project.layers if item.id==layer.generated_layer_id),None)
    if generated is None:return apply_effect_resource_layer(project,layer)
    pixels=render_effect_resource_layer_current_frame(project,layer,frame)
    if pixels is None:return generated
    while len(project.frames)<=frame:project.add_frame()
    project.frames[frame].layer_pixels[generated.id]=pixels.copy();generated.visible=layer.visible
    return generated


def apply_effect_resource_layer(project, layer: EffectResourceLayer, frames=None):
    frames = render_effect_resource_layer(project, layer) if frames is None else frames
    if layer.placement_mode == PLACEMENT_PARTICLE:
        generated = apply_particle_frames(project, layer.as_particle_emitter(), frames)
    else:
        generated = apply_effect_composition_layer(project, layer.as_composition_layer(), frames)
    layer.generated_layer_id = generated.id
    layer.sync_active_adapter()
    # Unified Resource Layers own the user-facing name.  The legacy particle
    # renderer still supplies its compatibility name, so replace it here.
    generated.name = layer.name
    generated.visible = layer.visible
    return generated
