"""Bounded read-only event invocations. No fired flags, RNG or recursion."""
from dataclasses import dataclass, replace

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleSubEmitterEventSettings, EMISSION_CYCLIC_STEADY
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies


def events(settings):
    return (("birth", settings.birth_sub_emitter), ("death", settings.death_sub_emitter))


def template_settings(settings):
    # A request-level shallow adapter; canonical slots remain cached and immutable.
    return replace(settings, emission_cycle_mode="one_shot",
                   birth_sub_emitter=ParticleSubEmitterEventSettings(),
                   death_sub_emitter=ParticleSubEmitterEventSettings())


def contribution_bounds(settings, by_id, parent_id):
    """Settings-based conservative horizon/count bounds, before rendering/RNG."""
    settings.validate()
    visual = settings.cyclic_active_copy_bound() if settings.emission_cycle_mode == EMISSION_CYCLIC_STEADY else settings.particle_count_max
    stamps = settings.trail_stamp_bound()
    detail = []
    for kind,event in events(settings):
        event.validate()
        if event.target_layer_id is not None:
            target = by_id.get(event.target_layer_id)
            if target is None or target.id == parent_id or target.placement_mode != PLACEMENT_PARTICLE:
                raise ValueError("sub-emitter target must be another existing Particle Layer")
        if not event.enabled: continue
        child = template_settings(target.particle_settings)
        child.validate()
        relative_max = child.start_delay_max + (child.emission_duration-1 if child.emission_mode == "over_time" else 0)
        horizon = relative_max + child.lifetime_max + child.trail.delta_max if child.particle_count_max else 0
        overlaps = (horizon+settings.emission_period_frames-1)//settings.emission_period_frames if settings.emission_cycle_mode == EMISSION_CYCLIC_STEADY else (1 if horizon else 0)
        count = settings.particle_count_max * overlaps * child.particle_count_max
        trail_count = count*child.trail.sample_count if child.trail.enabled else 0
        visual += count; stamps += trail_count
        detail.append((kind,horizon,count,trail_count))
    if visual > 4096: raise ValueError("sub-emitter combined visual-copy bound exceeds 4096")
    if stamps > 8192: raise ValueError("sub-emitter combined trail-stamp bound exceeds 8192")
    return visual,stamps,tuple(detail)


def validate_project_sub_emitters(project, *, candidate_id=None, candidate_settings=None):
    by_id = {layer.id:layer for layer in project.effect_resource_layers}
    if candidate_id in by_id:
        original = by_id[candidate_id]
        by_id[candidate_id] = replace(original, particle_settings=candidate_settings)
    for layer in by_id.values():
        if layer.placement_mode == PLACEMENT_PARTICLE:
            contribution_bounds(layer.particle_settings,by_id,layer.id)


@dataclass(frozen=True)
class RenderCopy:
    canonical: object
    birth_frame: int
    render_key: tuple
    event_origin: object = None
    cycle_index: int = 0

    @property
    def copy_key(self): return self.render_key

    def __getattr__(self,name): return getattr(self.canonical,name)


@dataclass(frozen=True)
class EventInvocation:
    key: tuple
    event_frame: int
    origin: object
    children: tuple


def iter_invocations(parent_id, settings, parents, kind, children, child_settings, frame):
    from app.services.particle_render_service import evaluate_particle_motion
    horizon = max((child.birth_frame-child_settings.start_frame+child.lifetime+child_settings.trail.delta_max for child in children),default=0)
    if not horizon or frame < settings.start_frame: return
    cyclic = settings.emission_cycle_mode == EMISSION_CYCLIC_STEADY
    period = settings.emission_period_frames
    motion = settings.motion.evaluated(frame)
    for parent in parents:
        offset = 0 if kind == "birth" else parent.lifetime
        event0 = parent.birth_frame+offset
        if cyclic:
            minimum = -(-(frame-event0-(horizon-1))//period)
            maximum = (frame-event0)//period
        else: minimum=maximum=0
        for cycle in range(minimum,maximum+1):
            birth = parent.birth_frame+(cycle*period if cyclic else 0)
            event_frame = birth+offset
            if not 0 <= frame-event_frame < horizon: continue
            age = 0 if kind == "birth" else parent.lifetime-1
            origin = evaluate_particle_motion(settings,parent,age/parent.lifetime,frame,evaluated_motion=motion,particle_age=age)
            key = (parent_id,kind,cycle,parent.particle_id,birth)
            copies = tuple(RenderCopy(child,event_frame+child.birth_frame-child_settings.start_frame,
                          (1,0 if kind=="birth" else 1,cycle,parent.particle_id,birth,parent_id,child.particle_id),origin,cycle)
                          for child in children if 0 <= frame-(event_frame+child.birth_frame-child_settings.start_frame) < child.lifetime+child_settings.trail.delta_max)
            if copies: yield EventInvocation(key,event_frame,origin,copies)


def render_layer_particles(project,layer,frame,*,transform=None,affine=None,diagnostics=None):
    from app.services import particle_render_service as r
    from app.services.particle_trail_render_service import render_particle_trails
    settings=layer.particle_settings
    if not any(event.enabled for _,event in events(settings)):
        return r.render_particle_frame(project,layer.as_particle_emitter(),frame,layer_space_transform=transform,layer_space_affine=affine,diagnostic_collector=diagnostics)
    by_id={item.id:item for item in project.effect_resource_layers}
    contribution_bounds(settings,by_id,layer.id)
    clip=r._resolve_particle_clip(project,settings)
    parents=r.particle_spawn_states(settings,len(clip.frames))
    parent_copies=iter_particle_cycle_copies(settings,parents,frame,visibility_extension_frames=settings.trail.delta_max) if settings.emission_cycle_mode==EMISSION_CYCLIC_STEADY else parents
    copies=(RenderCopy(copy,copy.birth_frame,(0,getattr(copy,"cycle_index",0),copy.particle_id),cycle_index=getattr(copy,"cycle_index",0)) for copy in parent_copies)
    streams=[(settings,clip,copies)]
    for kind,event in events(settings):
        if not event.enabled: continue
        target=by_id[event.target_layer_id]
        child=template_settings(target.particle_settings)
        child_clip=r._resolve_particle_clip(project,child)
        children=r.particle_spawn_states(child,len(child_clip.frames))
        invocations=iter_invocations(layer.id,settings,parents,kind,children,child,frame)
        # Generator is consumed by the shared group collector, not a recursive render.
        child_copies=(copy for invocation in invocations for copy in invocation.children)
        streams.append((child,child_clip,child_copies))
    return render_particle_trails(project,layer.as_particle_emitter(),frame,clip,(),diagnostics,transform,affine,streams=streams)


def template_dependencies(project,layer):
    by_id={item.id:item for item in project.effect_resource_layers}
    result=[]
    for kind,event in events(layer.particle_settings):
        if event.enabled:
            target=by_id.get(event.target_layer_id)
            result.append((kind,event.target_layer_id,repr(template_settings(target.particle_settings).to_dict()) if target else None))
    return tuple(result)
