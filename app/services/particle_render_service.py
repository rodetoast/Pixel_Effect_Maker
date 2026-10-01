"""Deterministic CPU renderer for animation-clip particles."""

from __future__ import annotations

import math
import random
import hashlib
from dataclasses import dataclass
from uuid import uuid4

import numpy as np

from app.models.animation_clip import AnimationClipAsset
from app.models.frame import empty_pixels
from app.models.layer import Layer
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings, ParticleInstance, ParticleMotionSettings
from app.models.project import Project
from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import EffectRenderError, render_transformed_source
from app.services.emitter_service import ease
from app.services.resource_composition_render_service import composition_as_clip
from app.services.effect_layer_transform_3d_render_service import focal_length
from app.services.layer_space_transform_service import project_local_points
from app.services.lifetime_modulation_service import eased_lifetime_amount, evaluate_lifetime_color_component, evaluate_lifetime_scalar, normalized_lifetime_age
from app.services.particle_natural_motion_service import effective_motion_age, gravity_displacement
from app.services.particle_noise_service import particle_noise_offset
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies
from app.models.particle_emitter import EMISSION_CYCLIC_STEADY


_SPAWN_STATE_CACHE: dict[tuple, tuple[ParticleInstance, ...]] = {}
_RESOURCE_CLIP_CACHE: dict[tuple, AnimationClipAsset] = {}
PARTICLE_RENDER_STATS = {"spawn_cache_hits": 0, "spawn_cache_misses": 0, "resource_cache_hits":0, "resource_cache_misses":0, "full_sequence_renders": 0, "current_frame_renders": 0}


def invalidate_particle_render_caches() -> None:
    _SPAWN_STATE_CACHE.clear()
    _RESOURCE_CLIP_CACHE.clear()


@dataclass(frozen=True)
class ParticleMotionPosition:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class ParticleFrameDiagnostic:
    """Immutable test/diagnostic snapshot of one visible particle evaluation."""
    particle_id: int
    generation_order: int | tuple[int, int]
    spawn_frame: int
    lifetime: int
    age: int
    normalized_age: float
    source_frame: int | None
    x: float
    y: float
    z: float
    rotation: float
    scale: float
    opacity: float
    depth_key: tuple[float, int | tuple[int, int]]
    local_x: float = 0.0
    local_y: float = 0.0
    local_z: float = 0.0
    lifetime_scale: float = 1.0
    lifetime_tint_r: float = 1.0
    lifetime_tint_g: float = 1.0
    lifetime_tint_b: float = 1.0
    cycle_index: int | None = None
    copy_key: tuple[int, int] | None = None


def _motion_ease(value: float, easing: str) -> float:
    value=max(0.0,min(1.0,float(value)))
    if easing=="Ease In": return value*value
    if easing=="Ease Out": return 1.0-(1.0-value)*(1.0-value)
    if easing=="Ease In/Out": return 2.0*value*value if value<0.5 else 1.0-((-2.0*value+2.0)**2)/2.0
    return value


def _stable_motion_phase(seed: int, particle_id: int, spread: float) -> float:
    if spread == 0.0: return 0.0
    digest=hashlib.sha256(f"{int(seed)}:{int(particle_id)}:motion-phase".encode("ascii")).digest()
    fraction=int.from_bytes(digest[:8],"big")/float(1<<64)
    return fraction*float(spread)


def evaluate_particle_motion(settings: ParticleEmitterSettings, instance: ParticleInstance, normalized_age: float, effect_frame: int = 0, *, evaluated_motion: ParticleMotionSettings | None = None, particle_age: float | None = None) -> ParticleMotionPosition:
    """Evaluate Linear, Orbit, or Helix in particle-local XYZ coordinates."""
    motion=evaluated_motion or settings.motion.evaluated(effect_frame)
    t=max(0.0,min(1.0,float(normalized_age)))
    age=t*instance.lifetime if particle_age is None else max(0.0,float(particle_age))
    motion_age=effective_motion_age(age,settings.drag_enabled,settings.drag_strength)
    if motion.mode=="linear":
        base=ParticleMotionPosition(instance.start_x+instance.velocity_x*motion_age,instance.start_y+instance.velocity_y*motion_age,0.0)
    else:
        motion_t=t if not settings.drag_enabled or settings.drag_strength==0.0 else max(0.0,min(1.0,motion_age/instance.lifetime))
        radius_t=_motion_ease(t,motion.radius_easing);angle_t=_motion_ease(motion_t,motion.angle_easing)
        radius=motion.radius_start+(motion.radius_end-motion.radius_start)*radius_t
        # Screen Y grows downward, so positive angles are visually clockwise.
        sign=1.0 if motion.direction=="clockwise" else -1.0
        phase=instance.motion_phase_unit*motion.phase_spread_degrees if instance.motion_phase_unit else instance.motion_phase_degrees
        angle=math.radians(motion.start_angle_degrees+sign*motion.turns*360.0*angle_t+phase)
        orbit_x=math.cos(angle)*radius*motion.ellipse_scale_x
        orbit_y=math.sin(angle)*radius*motion.ellipse_scale_y
        plane=math.radians(motion.orbit_plane_rotation_degrees)
        orbit_x,orbit_y=(orbit_x*math.cos(plane)-orbit_y*math.sin(plane),orbit_x*math.sin(plane)+orbit_y*math.cos(plane))
        cx=instance.start_x+motion.center_x;cy=instance.start_y+motion.center_y;cz=motion.center_z
        if motion.mode=="orbit": base=ParticleMotionPosition(cx+orbit_x,cy+orbit_y,cz)
        else:
            axis_t=_motion_ease(motion_t,motion.axis_easing);axis=motion.axis_start+(motion.axis_end-motion.axis_start)*axis_t
            if motion.helix_axis=="x": base=ParticleMotionPosition(cx+axis,cy+orbit_x,cz+orbit_y)
            elif motion.helix_axis=="y": base=ParticleMotionPosition(cx+orbit_x,cy+axis,cz+orbit_y)
            else: base=ParticleMotionPosition(cx+orbit_x,cy+orbit_y,cz+axis)
    gravity_y=gravity_displacement(age,settings.gravity_enabled,settings.gravity_strength)
    noise_x,noise_y=particle_noise_offset(settings.seed,instance.particle_id,age,settings.noise_enabled,settings.noise_strength,settings.noise_frequency)
    return ParticleMotionPosition(base.x+noise_x,base.y+gravity_y+noise_y,base.z)


def project_particle_billboard(position: ParticleMotionPosition, strength: float, width: int, height: int) -> tuple[float,float,float,bool]:
    """Project a billboard center and return x, y, scale, visibility safety."""
    if not all(math.isfinite(value) for value in (position.x,position.y,position.z,strength)): return 0.0,0.0,1.0,False
    if strength<=0.0:return position.x,position.y,1.0,True
    focal=focal_length(width,height,strength);denominator=focal-position.z
    if denominator<=focal*0.05:return 0.0,0.0,1.0,False
    factor=min(20.0,focal/denominator);cx=width/2.0;cy=height/2.0
    x=cx+(position.x-cx)*factor;y=cy+(position.y-cy)*factor
    return x,y,factor,math.isfinite(x) and math.isfinite(y)


def particle_motion_guide(settings: ParticleEmitterSettings, width: int, height: int, samples: int | None = None, effect_frame: int = 0) -> list[ParticleMotionPosition]:
    """Sample the exact renderer motion evaluator for Canvas guides."""
    count=samples or max(32,min(256,32+round(abs(settings.motion.turns)*24)))
    lifetime=max(1,round((settings.lifetime_min+settings.lifetime_max)/2))
    instance=ParticleInstance(0,lifetime,settings.origin_x,settings.origin_y,0,0,1,0,0,0,1,0)
    def guide_point(index: int) -> ParticleMotionPosition:
        fraction=index/max(1,count-1)
        age=fraction*max(0,lifetime-1)
        # Preserve the established undamped guide endpoint. Drag/Noise guides
        # represent actual surviving ages to match the renderer's path.
        path_is_age_based=(settings.drag_enabled and settings.drag_strength>0) or (settings.noise_enabled and settings.noise_strength>0 and settings.noise_frequency>0)
        normalized=age/lifetime if path_is_age_based else fraction
        return evaluate_particle_motion(settings,instance,normalized,effect_frame,particle_age=age)
    return [guide_point(index) for index in range(count)]


def velocity_from_direction_speed(direction_degrees: float, speed: float) -> tuple[float, float]:
    """Convert the renderer's degrees/pixels-per-frame values to velocity."""
    radians = math.radians(direction_degrees)
    return math.cos(radians) * speed, math.sin(radians) * speed


def representative_particle_guide(settings: ParticleEmitterSettings) -> dict[str, float]:
    """Return a deterministic editing guide using renderer units and midpoint ranges."""
    speed = (settings.speed_min + settings.speed_max) / 2.0
    lifetime = (settings.lifetime_min + settings.lifetime_max) / 2.0
    velocity_x, velocity_y = velocity_from_direction_speed(settings.direction_degrees, speed)
    age = max(0.0, lifetime - 1.0)
    noise_x,noise_y=particle_noise_offset(settings.seed,0,age,settings.noise_enabled,settings.noise_strength,settings.noise_frequency)
    return {
        "origin_x": float(settings.origin_x),
        "origin_y": float(settings.origin_y),
        "endpoint_x": float(settings.origin_x) + velocity_x * effective_motion_age(age,settings.drag_enabled,settings.drag_strength) + noise_x,
        "endpoint_y": float(settings.origin_y) + velocity_y * effective_motion_age(age,settings.drag_enabled,settings.drag_strength) + gravity_displacement(age,settings.gravity_enabled,settings.gravity_strength) + noise_y,
        "speed": speed,
        "lifetime": lifetime,
    }


def build_particle_instances(settings: ParticleEmitterSettings, clip_length: int) -> list[ParticleInstance]:
    """Resolve all randomness once; equal settings and seed produce equal instances."""
    settings.validate()
    rng = random.Random(settings.seed)
    count = rng.randint(settings.particle_count_min, settings.particle_count_max)
    result: list[ParticleInstance] = []
    for index in range(count):
        delay = rng.randint(settings.start_delay_min, settings.start_delay_max)
        spread_birth = 0 if settings.emission_mode == "burst" or count <= 1 else round(index * max(0, settings.emission_duration - 1) / (count - 1))
        x, y = _spawn_position(settings, rng)
        direction = settings.direction_degrees
        if settings.direction_mode == "radial_outward":
            dx, dy = x - settings.origin_x, y - settings.origin_y
            direction = math.degrees(math.atan2(dy, dx)) if abs(dx) + abs(dy) > 1e-9 else rng.uniform(0, 360)
        direction += rng.uniform(-settings.direction_spread_degrees, settings.direction_spread_degrees)
        speed = rng.uniform(settings.speed_min, settings.speed_max)
        velocity_x, velocity_y = velocity_from_direction_speed(direction, speed)
        phase_unit=_stable_motion_phase(settings.seed,index,1.0);phase=phase_unit*settings.motion.phase_spread_degrees
        result.append(ParticleInstance(
            birth_frame=settings.start_frame + spread_birth + delay,
            lifetime=rng.randint(settings.lifetime_min, settings.lifetime_max),
            start_x=x, start_y=y, velocity_x=velocity_x,
            velocity_y=velocity_y,
            scale=rng.uniform(settings.scale_min, settings.scale_max),
            rotation=rng.uniform(settings.rotation_min, settings.rotation_max),
            angular_velocity=rng.uniform(settings.angular_velocity_min, settings.angular_velocity_max),
            clip_start_frame=rng.randrange(clip_length) if settings.random_start_frame else 0,
            clip_playback_speed=rng.uniform(settings.clip_speed_min, settings.clip_speed_max),
            random_seed=rng.getrandbits(31),particle_id=index,motion_phase_degrees=phase,motion_phase_unit=phase_unit))
    return result


def _spawn_position(settings: ParticleEmitterSettings, rng: random.Random) -> tuple[float, float]:
    if settings.spawn_shape == "line":
        amount = rng.random(); return (settings.origin_x + (settings.line_end_x - settings.origin_x) * amount,
                                       settings.origin_y + (settings.line_end_y - settings.origin_y) * amount)
    if settings.spawn_shape == "circle":
        angle = math.radians(rng.uniform(settings.start_angle, settings.end_angle))
        return settings.origin_x + math.cos(angle) * settings.radius, settings.origin_y + math.sin(angle) * settings.radius
    if settings.spawn_shape == "box":
        return (settings.origin_x + rng.uniform(-settings.box_width / 2, settings.box_width / 2),
                settings.origin_y + rng.uniform(-settings.box_height / 2, settings.box_height / 2))
    return settings.origin_x, settings.origin_y


def particle_clip_frame_index(clip: AnimationClipAsset, instance: ParticleInstance, age: int, effect_fps: int | None = None) -> int | None:
    if clip.source_format == "composition":
        index = math.floor(age / max(1, effect_fps or clip.fps) * clip.fps * instance.clip_playback_speed) + instance.clip_start_frame
        if clip.playback_mode == "loop": index %= len(clip.frames)
        elif index >= len(clip.frames):
            if clip.playback_mode == "once": return None
            index = len(clip.frames)-1
        return max(0,index)
    durations = clip.frame_durations_ms or [max(1, round(1000 / clip.fps))] * len(clip.frames)
    elapsed = age * (1000.0 / max(1, effect_fps or clip.fps)) * instance.clip_playback_speed + sum(durations[:instance.clip_start_frame])
    total = sum(durations)
    if clip.playback_mode == "loop": elapsed %= total
    elif elapsed >= total:
        if clip.playback_mode == "once": return None
        elapsed = total - 1
    cumulative = 0
    for index, duration in enumerate(durations):
        cumulative += duration
        if elapsed < cumulative: break
    return index


def particle_clip_frame(clip: AnimationClipAsset, instance: ParticleInstance, age: int, effect_fps: int | None = None) -> np.ndarray | None:
    index=particle_clip_frame_index(clip,instance,age,effect_fps)
    return None if index is None else clip.frames[index]


def _resolve_particle_clip(project: Project, settings: ParticleEmitterSettings) -> AnimationClipAsset:
    clip = next((item for item in project.animation_clips if item.id == settings.clip_asset_id), None)
    if settings.resource_type == "source_asset":
        source = next((item for item in project.source_assets if item.id == settings.clip_asset_id), None)
        key=None if source is None else (id(project),"source_asset",source.id,id(source.pixels),source.pivot_x,source.pivot_y)
        clip=None if key is None else _RESOURCE_CLIP_CACHE.get(key)
        if key is not None and clip is None:
            PARTICLE_RENDER_STATS["resource_cache_misses"]+=1;clip=AnimationClipAsset(source.name, [source.pixels], fps=project.fps,
                pivot_x=source.pivot_x, pivot_y=source.pivot_y, playback_mode="hold",source_format=source.source_format, source_path=source.source_path);_RESOURCE_CLIP_CACHE[key]=clip
        elif clip is not None:PARTICLE_RENDER_STATS["resource_cache_hits"]+=1
    elif settings.resource_type == "resource_composition":
        composition=next((item for item in project.resource_compositions if item.id==settings.resource_id),None)
        key=None if composition is None else (id(project),"resource_composition",composition.id,composition.revision)
        clip=None if key is None else _RESOURCE_CLIP_CACHE.get(key)
        if key is not None and clip is None:PARTICLE_RENDER_STATS["resource_cache_misses"]+=1;clip=composition_as_clip(project,composition);_RESOURCE_CLIP_CACHE[key]=clip
        elif clip is not None:PARTICLE_RENDER_STATS["resource_cache_hits"]+=1
    if clip is None: raise EffectRenderError("the particle animation clip does not exist")
    if len(_RESOURCE_CLIP_CACHE)>16:_RESOURCE_CLIP_CACHE.pop(next(iter(_RESOURCE_CLIP_CACHE)))
    return clip


def _spawn_cache_key(settings: ParticleEmitterSettings, clip_length: int) -> tuple:
    values=settings.to_dict();values.pop("motion",None);values.pop("output_frame_count",None);values.pop("scale_over_lifetime",None);values.pop("color_over_lifetime",None);values.pop("gravity_enabled",None);values.pop("gravity_strength",None);values.pop("drag_enabled",None);values.pop("drag_strength",None);values.pop("noise_enabled",None);values.pop("noise_strength",None);values.pop("noise_frequency",None);values.pop("blend_mode",None);values.pop("easing",None);values.pop("opacity_start",None);values.pop("opacity_end",None)
    values.pop("emission_cycle_mode",None);values.pop("emission_period_frames",None)
    return repr(values),int(clip_length)


def particle_spawn_states(settings: ParticleEmitterSettings, clip_length: int) -> tuple[ParticleInstance,...]:
    key=_spawn_cache_key(settings,clip_length);cached=_SPAWN_STATE_CACHE.get(key)
    if cached is not None:PARTICLE_RENDER_STATS["spawn_cache_hits"]+=1;return cached
    PARTICLE_RENDER_STATS["spawn_cache_misses"]+=1;cached=tuple(build_particle_instances(settings,clip_length));_SPAWN_STATE_CACHE[key]=cached
    if len(_SPAWN_STATE_CACHE)>32:_SPAWN_STATE_CACHE.pop(next(iter(_SPAWN_STATE_CACHE)))
    return cached


def render_particle_frame(project: Project, emitter: ParticleEmitter, frame_index: int, *, clip: AnimationClipAsset | None = None, instances=None, diagnostic_collector: list[ParticleFrameDiagnostic] | None = None, layer_space_transform: EffectLayerTransform3D | None = None, layer_space_affine=None) -> np.ndarray:
    """Render one exact frame while reusing deterministic spawn/resource state."""
    settings=emitter.settings;settings.validate();clip=clip or _resolve_particle_clip(project,settings)
    instances=particle_spawn_states(settings,len(clip.frames)) if instances is None else instances
    output=empty_pixels(project.width,project.height);alive=[];candidates=[];local_points=[]
    layer_space_transform = layer_space_transform or EffectLayerTransform3D()
    layer_value = layer_space_transform.evaluated(frame_index)
    motion_value=settings.motion.evaluated(frame_index)
    motion_perspective=motion_value.perspective_strength
    cyclic = settings.emission_cycle_mode == EMISSION_CYCLIC_STEADY
    if cyclic:
        instances = iter_particle_cycle_copies(settings, instances, frame_index)
    for order,instance in enumerate(instances):
            if cyclic: order = instance.copy_key
            age = frame_index - instance.birth_frame
            if age < 0 or age >= instance.lifetime: continue
            pixels=particle_clip_frame(clip,instance,age,project.fps)
            if pixels is None: continue
            lifetime_age = normalized_lifetime_age(age, instance.lifetime)
            amount = ease(lifetime_age, settings.easing)
            normalized=0.0 if instance.lifetime<=0 else age/instance.lifetime
            position=evaluate_particle_motion(settings,instance,normalized,frame_index,evaluated_motion=motion_value,particle_age=age)
            local_x,local_y,motion_scale,visible=project_particle_billboard(position,motion_perspective,project.width,project.height)
            if not visible:continue
            lifetime_scale=evaluate_lifetime_scalar(settings.scale_over_lifetime,lifetime_age)
            color=settings.color_over_lifetime
            if color.enabled:
                color_amount=eased_lifetime_amount(lifetime_age,color.easing)
                tint_r=evaluate_lifetime_color_component(color,lifetime_age,0,eased_amount=color_amount)
                tint_g=evaluate_lifetime_color_component(color,lifetime_age,1,eased_amount=color_amount)
                tint_b=evaluate_lifetime_color_component(color,lifetime_age,2,eased_amount=color_amount)
            else:tint_r=tint_g=tint_b=1.0
            candidates.append((order,instance,pixels,amount,motion_scale,lifetime_scale,tint_r,tint_g,tint_b,age,normalized,position))
            local_points.append((local_x,local_y,position.z))
    if candidates:
        projected_xy,depths,perspective_scales,valid_points=project_local_points(
            np.asarray(local_points,dtype=np.float64),layer_value,project.width,project.height,
            post_affine=layer_space_affine,
        )
        if layer_space_affine is not None:
            from app.services.layer_parenting_service import affine_axis_scales
            inherited_scale_x,inherited_scale_y=affine_axis_scales(layer_space_affine)
        else:inherited_scale_x,inherited_scale_y=abs(layer_value.scale_x),abs(layer_value.scale_y)
    for index,(order,instance,pixels,amount,motion_scale,lifetime_scale,tint_r,tint_g,tint_b,age,normalized,position) in enumerate(candidates):
            if not valid_points[index]:continue
            x,y=map(float,projected_xy[index]);view_z=float(depths[index]);perspective_scale=float(perspective_scales[index])
            scale_x=instance.scale*lifetime_scale*motion_scale*perspective_scale*inherited_scale_x
            scale_y=instance.scale*lifetime_scale*motion_scale*perspective_scale*inherited_scale_y
            if diagnostic_collector is not None:
                source_frame=particle_clip_frame_index(clip,instance,age,project.fps)
                diagnostic_collector.append(ParticleFrameDiagnostic(
                    instance.particle_id,order,instance.birth_frame,instance.lifetime,age,normalized,source_frame,
                    x,y,view_z,instance.rotation+instance.angular_velocity*age,
                    (scale_x+scale_y)*0.5,
                    settings.opacity_start+(settings.opacity_end-settings.opacity_start)*amount,
                    (view_z,order),position.x,position.y,position.z,lifetime_scale,tint_r,tint_g,tint_b,
                    instance.cycle_index if cyclic else None,instance.copy_key if cyclic else None,
                ))
            alive.append((view_z,order,instance,pixels,amount,x,y,scale_x,scale_y,tint_r,tint_g,tint_b,age))
    alive.sort(key=lambda item:(item[0],item[1]))
    for _,_,instance,pixels,amount,x,y,scale_x,scale_y,tint_r,tint_g,tint_b,age in alive:
            asset = SourceAsset(name="particle", pixels=pixels, pivot_x=clip.pivot_x, pivot_y=clip.pivot_y)
            render_transformed_source(output, asset,
                position_x=x, position_y=y,
                rotation=instance.rotation + instance.angular_velocity * age,
                scale_x=scale_x, scale_y=scale_y,
                horizontal_tilt=0, vertical_tilt=0, perspective=0,
                opacity=settings.opacity_start + (settings.opacity_end - settings.opacity_start) * amount,
                tint_r=tint_r,tint_g=tint_g,tint_b=tint_b,
                blend_mode=settings.blend_mode)
    if layer_value.opacity < 1.0:
        output[...,3]=np.rint(output[...,3].astype(np.float64)*layer_value.opacity).astype(np.uint8)
    PARTICLE_RENDER_STATS["current_frame_renders"]+=1
    return output


def render_particle_frames(project: Project, emitter: ParticleEmitter, *, layer_space_transform: EffectLayerTransform3D | None = None, layer_space_affine=None) -> list[np.ndarray]:
    settings = emitter.settings; settings.validate();clip=_resolve_particle_clip(project,settings)
    instances=particle_spawn_states(settings,len(clip.frames));PARTICLE_RENDER_STATS["full_sequence_renders"]+=1
    outputs=[render_particle_frame(project,emitter,index,clip=clip,instances=instances,layer_space_transform=layer_space_transform,layer_space_affine=layer_space_affine) for index in range(settings.output_frame_count)]
    return outputs


def apply_particle_frames(project: Project, emitter: ParticleEmitter, outputs: list[np.ndarray]) -> Layer:
    if not outputs: raise EffectRenderError("particle output contains no frames")
    expected = (project.height, project.width, 4)
    if any(item.dtype != np.uint8 or item.shape != expected for item in outputs): raise EffectRenderError("invalid particle RGBA output")
    layer = next((item for item in project.layers if item.id == emitter.generated_layer_id), None)
    new = layer is None
    if new: layer = Layer(id=uuid4().hex, name=f"Particle System: {emitter.name}", kind="generated", generator_id=emitter.id)
    while len(project.frames) < len(outputs): project.add_frame()
    if new: project.layers.append(layer)
    assert layer is not None
    for index, frame in enumerate(project.frames):
        frame.layer_pixels[layer.id] = outputs[index].copy() if index < len(outputs) else empty_pixels(project.width, project.height)
    layer.name = f"Particle System: {emitter.name}"; layer.kind = "generated"; layer.generator_id = emitter.id
    emitter.generated_layer_id = layer.id
    return layer
