"""Analytic, target-frame-local sprite trails. No playback history or RNG."""
from dataclasses import dataclass
import numpy as np
from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.particle_emitter import EMISSION_CYCLIC_STEADY
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies
from app.services.lifetime_modulation_service import (normalized_lifetime_age,
    evaluate_lifetime_scalar_for_render, evaluate_lifetime_color_component, eased_lifetime_amount)


def iter_trail_samples(trail, copy_age, lifetime):
    """Oldest to newest, positive interval multiples only, strict delta<D."""
    for delta in range(trail.delta_max, 0, -trail.sample_interval_frames):
        age=copy_age-delta
        if 0 <= age < lifetime:
            yield age, delta, trail.opacity*(1-delta/trail.duration_frames)


@dataclass(slots=True)
class _SpriteView:
    """Read-only borrowed pixels; SourceAsset's defensive image copy is not needed."""
    pixels: np.ndarray
    pivot_x: float
    pivot_y: float
    @property
    def width(self): return self.pixels.shape[1]
    @property
    def height(self): return self.pixels.shape[0]


@dataclass(slots=True)
class _Stamp:
    settings: object
    clip: object
    instance: object
    order: object
    age: int
    copy_age: int
    delta: int
    pixels: np.ndarray
    opacity: float
    motion_scale: float
    lifetime_scale: float
    tint_r: float
    tint_g: float
    tint_b: float
    position: object


def render_particle_trails(project,emitter,frame,clip,instances,diagnostics,transform,affine,*,streams=None):
    # Local import avoids a renderer/service cycle. Existing pure evaluators and
    # the exact existing raster are shared, not reimplemented.
    from app.services import particle_render_service as r
    from app.services.layer_space_transform_service import project_local_points
    from app.services.layer_parenting_service import affine_axis_scales
    settings=emitter.settings;trail=settings.trail
    output=r.empty_pixels(project.width,project.height)
    layer=(transform or EffectLayerTransform3D()).evaluated(frame)
    cyclic=settings.emission_cycle_mode==EMISSION_CYCLIC_STEADY
    if streams is None:
        if cyclic:instances=iter_particle_cycle_copies(settings,instances,frame,visibility_extension_frames=trail.delta_max)
        streams=((settings,clip,instances),)
    stamps=[];points=[];groups=[]
    for settings,clip,instances in streams:
        trail=settings.trail
        motion=settings.motion.evaluated(frame)
        for order,instance in enumerate(instances):
            if hasattr(instance,"render_key"):order=instance.render_key
            elif settings.emission_cycle_mode==EMISSION_CYCLIC_STEADY:order=instance.copy_key
            copy_age=frame-instance.birth_frame
            if not 0 <= copy_age < instance.lifetime+trail.delta_max:continue
            begin=len(stamps)
            def append_stamp(age,delta,multiplier):
                pixels=r.particle_clip_frame(clip,instance,age,project.fps)
                if pixels is None:return
                t=normalized_lifetime_age(age,instance.lifetime)
                opacity=evaluate_lifetime_scalar_for_render(settings.opacity_over_lifetime,t)*multiplier
                position=r.evaluate_particle_motion(settings,instance,age/instance.lifetime,frame,evaluated_motion=motion,particle_age=age)
                origin=getattr(instance,"event_origin",None)
                if origin is not None:position=r.ParticleMotionPosition(position.x+origin.x,position.y+origin.y,position.z+origin.z)
                x,y,scale,visible=r.project_particle_billboard(position,motion.perspective_strength,project.width,project.height)
                if not visible:return
                lifetime_scale=evaluate_lifetime_scalar_for_render(settings.scale_over_lifetime,t)
                color=settings.color_over_lifetime
                if color.enabled:
                    amount=eased_lifetime_amount(t,color.easing) if len(color.points)==2 else None
                    red=evaluate_lifetime_color_component(color,t,0,eased_amount=amount)
                    green=evaluate_lifetime_color_component(color,t,1,eased_amount=amount)
                    blue=evaluate_lifetime_color_component(color,t,2,eased_amount=amount)
                else:red=green=blue=1.0
                stamps.append(_Stamp(settings,clip,instance,order,age,copy_age,delta,pixels,opacity,scale,lifetime_scale,red,green,blue,position))
                points.append((x,y,position.z))
            if trail.enabled:
                for age,delta,multiplier in iter_trail_samples(trail,copy_age,instance.lifetime):append_stamp(age,delta,multiplier)
            if copy_age < instance.lifetime:append_stamp(copy_age,0,1.0)
            if len(stamps)>begin:groups.append((begin,len(stamps),order))
    if not stamps:
        r.PARTICLE_RENDER_STATS["current_frame_renders"]+=1;return output
    xy,depths,perspectives,valid=project_local_points(np.asarray(points,dtype=np.float64),layer,project.width,project.height,post_affine=affine)
    sx,sy=affine_axis_scales(affine) if affine is not None else (abs(layer.scale_x),abs(layer.scale_y))
    # Live head is last. Tail-only depth uses latest valid historical stamp.
    # Invisibility fallback also uses latest projectable stamp, deterministically.
    ordered=[]
    for begin,end,order in groups:
        latest=next((i for i in range(end-1,begin-1,-1) if valid[i]),None)
        if latest is not None:ordered.append((float(depths[latest]),order,begin,end))
    ordered.sort(key=lambda group:(group[0],group[1]))
    for group_depth,order,begin,end in ordered:
        for index in range(begin,end):
            if not valid[index]:continue
            stamp=stamps[index];instance=stamp.instance;clip=stamp.clip
            x,y=map(float,xy[index]);z=float(depths[index])
            factor=instance.scale*stamp.lifetime_scale*stamp.motion_scale*float(perspectives[index])
            scale_x=factor*sx;scale_y=factor*sy
            rotation=instance.rotation+instance.angular_velocity*stamp.age
            if diagnostics is not None:
                diagnostics.append(r.ParticleFrameDiagnostic(instance.particle_id,order,instance.birth_frame,instance.lifetime,
                    stamp.age,stamp.age/instance.lifetime,r.particle_clip_frame_index(clip,instance,stamp.age,project.fps),
                    x,y,z,rotation,(scale_x+scale_y)*.5,stamp.opacity,(group_depth,order),
                    stamp.position.x,stamp.position.y,stamp.position.z,stamp.lifetime_scale,stamp.tint_r,stamp.tint_g,stamp.tint_b,
                    getattr(instance,"cycle_index",None),getattr(instance,"copy_key",None),stamp.delta,stamp.copy_age))
            r.render_transformed_source(output,_SpriteView(stamp.pixels,clip.pivot_x,clip.pivot_y),position_x=x,position_y=y,
                rotation=rotation,scale_x=scale_x,scale_y=scale_y,horizontal_tilt=0,vertical_tilt=0,perspective=0,
                opacity=stamp.opacity,tint_r=stamp.tint_r,tint_g=stamp.tint_g,tint_b=stamp.tint_b,blend_mode=stamp.settings.blend_mode)
    if layer.opacity<1:
        output[...,3]=np.rint(output[...,3].astype(np.float64)*layer.opacity).astype(np.uint8)
    r.PARTICLE_RENDER_STATS["current_frame_renders"]+=1
    return output
