from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
import subprocess
import types
import sys
import numpy as np
import pytest
from PIL import Image
from app.models.particle_emitter import ParticleSubEmitterEventSettings as Event, ParticleTrailSettings as Trail, ParticleMotionSettings
from app.models.effect_resource_layer import EffectResourceLayer, EffectLayerTransform3D
from app.services import particle_render_service as r
from app.services.particle_sub_emitter_service import (render_layer_particles, iter_invocations, template_settings, contribution_bounds, validate_project_sub_emitters)
from app.services.effect_resource_layer_render_service import (render_effect_resource_layer_current_frame,render_effect_resource_layer,apply_effect_resource_layer,_base_key)
from app.services.effect_playback_service import render_exact_playback_frame,playback_relevant_revision
from app.services.export_service import export_png_frames
from tests.test_particle_trail import scene
from tests.test_lifetime_multi_point import curves


def setup(kind="death",cyclic=False,child_trail=False,**changes):
    project,emitter=scene(emission_cycle_mode="cyclic_steady" if cyclic else "one_shot",emission_period_frames=6,trail=Trail(True,7,2,.75))
    parent=EffectResourceLayer.from_particle_emitter(emitter);parent.id="parent";parent.name="Projectile"
    child=deepcopy(parent);child.id="target";child.name="Impact";child.visible=False;child.generated_layer_id=None
    child.particle_settings=replace(emitter.settings,start_frame=12,origin_x=0,origin_y=0,speed_min=0,speed_max=0,
        lifetime_min=4,lifetime_max=4,trail=Trail(child_trail,7,2,.75))
    for name,value in changes.items():setattr(child.particle_settings,name,value)
    project.effect_resource_layers.extend((parent,child));project.repair_effect_hierarchy()
    for event_kind in ("birth","death"):
        if kind in (event_kind,"both"):setattr(parent.particle_settings,event_kind+"_sub_emitter",Event(True,child.id))
    return project,parent,child


def collect(project,parent,frame,**kwargs):
    values=[]
    pixels=render_layer_particles(project,parent,frame,diagnostics=values,**kwargs)
    return pixels,values


def children(values):return [v for v in values if v.generation_order[0]==1]


@pytest.mark.parametrize("kind,event_frame,origin_age",[("birth",0,0),("death",5,4)])
def test_event_frame_origin_and_parent_trail_separation(kind,event_frame,origin_age):
    project,parent,target=setup(kind)
    _,before=collect(project,parent,event_frame-1) if event_frame else (None,[])
    assert not children(before)
    _,values=collect(project,parent,event_frame)
    child=children(values);assert len(child)==1 and child[0].age==0 and child[0].spawn_frame==event_frame
    slot=r.particle_spawn_states(parent.particle_settings,4)[0]
    origin=r.evaluate_particle_motion(parent.particle_settings,slot,origin_age/slot.lifetime,event_frame,particle_age=origin_age)
    assert child[0].local_x==origin.x and child[0].local_y==origin.y
    if kind=="death":assert any(v.generation_order[0]==0 and v.trail_delta for v in values)


@pytest.mark.parametrize("kind",["birth","death","both"])
@pytest.mark.parametrize("parent_mode",["linear","orbit","helix"])
@pytest.mark.parametrize("child_mode",["linear","orbit","helix"])
def test_child_motion_origin_and_historical_appearance(kind,parent_mode,child_mode):
    project,parent,target=setup(kind,child_trail=True,gravity_enabled=True,gravity_strength=.03,
        drag_enabled=True,drag_strength=.1,noise_enabled=True,noise_strength=2,
        motion=ParticleMotionSettings(mode=child_mode,radius_start=2,radius_end=5,axis_end=6),
        speed_min=1,speed_max=1,angular_velocity_min=13,angular_velocity_max=13,
        random_start_frame=True,clip_speed_min=.5,clip_speed_max=1.5)
    parent.particle_settings.motion=ParticleMotionSettings(mode=parent_mode,radius_start=1,radius_end=3,axis_end=5)
    parent.particle_settings.gravity_enabled=True;parent.particle_settings.gravity_strength=.01
    parent.particle_settings.drag_enabled=True;parent.particle_settings.drag_strength=.1
    parent.particle_settings.noise_enabled=True;parent.particle_settings.noise_strength=1
    curves(target.particle_settings)
    _,values=collect(project,parent,7 if kind!="birth" else 3)
    child_settings=template_settings(target.particle_settings);child_slots=r.particle_spawn_states(child_settings,4)
    parent_slots=r.particle_spawn_states(parent.particle_settings,4)
    for kind2,event in (("birth",parent.particle_settings.birth_sub_emitter),("death",parent.particle_settings.death_sub_emitter)):
        if not event.enabled:continue
        invocations=list(iter_invocations(parent.id,parent.particle_settings,parent_slots,kind2,child_slots,child_settings,7 if kind!="birth" else 3))
        assert invocations
        for diagnostic in children(values):
            if diagnostic.generation_order[1]!=(0 if kind2=="birth" else 1):continue
            invocation=next(i for i in invocations if i.event_frame==diagnostic.spawn_frame)
            slot=child_slots[diagnostic.particle_id]
            position=r.evaluate_particle_motion(child_settings,slot,diagnostic.age/slot.lifetime,7 if kind!="birth" else 3,particle_age=diagnostic.age)
            assert diagnostic.local_x==position.x+invocation.origin.x
            assert diagnostic.local_y==position.y+invocation.origin.y
            assert diagnostic.rotation==slot.rotation+slot.angular_velocity*diagnostic.age
            assert diagnostic.source_frame==r.particle_clip_frame_index(r._resolve_particle_clip(project,child_settings),slot,diagnostic.age,project.fps)
            age=r.normalized_lifetime_age(diagnostic.age,slot.lifetime)
            assert diagnostic.lifetime_scale==r.evaluate_lifetime_scalar_for_render(child_settings.scale_over_lifetime,age)
            expected_opacity=r.evaluate_lifetime_scalar_for_render(child_settings.opacity_over_lifetime,age)
            if diagnostic.trail_delta:expected_opacity*=child_settings.trail.opacity*(1-diagnostic.trail_delta/child_settings.trail.duration_frames)
            assert diagnostic.opacity==expected_opacity
            assert (diagnostic.lifetime_tint_r,diagnostic.lifetime_tint_g,diagnostic.lifetime_tint_b)==tuple(r.evaluate_lifetime_color_component(child_settings.color_over_lifetime,age,channel) for channel in range(3))


@pytest.mark.parametrize("kind",["birth","death","both"])
@pytest.mark.parametrize("trail",[False,True])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_cyclic_periodicity_random_seek_and_unique_identity(kind,trail,blend):
    project,parent,target=setup(kind,True,trail,blend_mode=blend,lifetime_min=9,lifetime_max=9)
    curves(target.particle_settings)
    values=[]
    for t in (100000,0,17,3,2,1,0,23,100000):
        pixel,diag=collect(project,parent,t)
        assert np.array_equal(pixel,collect(project,parent,t%6)[0])
        keys=[(v.generation_order,v.trail_delta) for v in diag]
        assert len(keys)==len(set(keys))
        assert [v.depth_key for v in diag]==sorted(v.depth_key for v in diag)
        values.append(pixel)
    assert np.array_equal(values[0],values[-1])


@pytest.mark.parametrize("field,value",[("start_frame",21),("emission_cycle_mode","cyclic_steady"),("emission_period_frames",12)])
def test_target_absolute_start_and_cyclic_do_not_change_single_schedule(field,value):
    project,parent,target=setup()
    before=collect(project,parent,6)[0]
    setattr(target.particle_settings,field,value)
    assert np.array_equal(before,collect(project,parent,6)[0])
    assert not children(collect(project,parent,20)[1])


@pytest.mark.parametrize("field,value",[("visible",True),("solo",True),("locked",True),("parent_id","parent")])
def test_target_flags_high_transform_parent_and_nested_events_ignored(field,value):
    project,parent,target=setup()
    before=collect(project,parent,6)[0]
    setattr(target,field,value);target.layer_space_transform.position_x=100;target.surface_transform.position_y=100
    target.particle_settings.birth_sub_emitter=Event(True,parent.id)
    target.particle_settings.death_sub_emitter=Event(True,parent.id)
    assert np.array_equal(before,collect(project,parent,6)[0])


def test_delayed_over_time_child_schedule_and_random_parent_lifetimes():
    project,parent,target=setup("both",particle_count_min=3,particle_count_max=3,emission_mode="over_time",emission_duration=4,start_delay_min=2,start_delay_max=3)
    parent.particle_settings.lifetime_min=2;parent.particle_settings.lifetime_max=6
    parent.particle_settings.particle_count_min=parent.particle_settings.particle_count_max=3
    parent.particle_settings.start_delay_min=1;parent.particle_settings.start_delay_max=4
    for t in range(24):
        _,values=collect(project,parent,t)
        slots=r.particle_spawn_states(template_settings(target.particle_settings),4)
        for child in children(values):
            key=child.generation_order;birth=key[4];event_frame=birth+(r.particle_spawn_states(parent.particle_settings,4)[key[3]].lifetime if key[1]==1 else 0)
            assert child.spawn_frame==event_frame+slots[child.particle_id].birth_frame-target.particle_settings.start_frame


def test_event_reuses_parent_target_spawn_tuples_and_no_rng_per_invocation():
    project,parent,target=setup("both",True,True)
    ps=r.particle_spawn_states(parent.particle_settings,4);cs=r.particle_spawn_states(template_settings(target.particle_settings),4)
    with patch.object(r.random,"Random",side_effect=AssertionError("new RNG")):
        for frame in (0,3,100000,5):collect(project,parent,frame)
        assert r.particle_spawn_states(parent.particle_settings,4) is ps
        assert r.particle_spawn_states(template_settings(target.particle_settings),4) is cs
        parent.particle_settings.birth_sub_emitter.enabled=False
        assert r.particle_spawn_states(parent.particle_settings,4) is ps


def test_child_inherits_only_origin_not_parent_particle_appearance_or_noise_identity():
    project,parent,target=setup("death",child_trail=True,speed_min=1,speed_max=1,noise_enabled=True,noise_strength=2)
    _,before=collect(project,parent,7)
    slots=r.particle_spawn_states(template_settings(target.particle_settings),4)
    settings=parent.particle_settings
    settings.speed_min=settings.speed_max=3;settings.rotation_min=settings.rotation_max=90
    settings.scale_min=settings.scale_max=2;settings.angular_velocity_min=settings.angular_velocity_max=45
    settings.color_over_lifetime.enabled=True;settings.color_over_lifetime.start_rgb=(255,0,0);settings.color_over_lifetime.end_rgb=(0,255,0)
    settings.opacity_start=.125;settings.opacity_end=.25;settings.seed+=1
    _,after=collect(project,parent,7)
    fields=lambda value:(value.age,value.source_frame,value.rotation,value.scale,value.opacity,value.lifetime_scale,value.lifetime_tint_r,value.lifetime_tint_g,value.lifetime_tint_b)
    assert [fields(v) for v in children(before)]==[fields(v) for v in children(after)]
    assert r.particle_spawn_states(template_settings(target.particle_settings),4) is slots


def test_zero_child_horizon_and_origin_current_higher_transform_translation():
    project,parent,target=setup("both",particle_count_min=0,particle_count_max=0)
    slots=r.particle_spawn_states(parent.particle_settings,4)
    assert list(iter_invocations(parent.id,parent.particle_settings,slots,"birth",(),template_settings(target.particle_settings),100000))==[]
    assert not children(collect(project,parent,6)[1])
    target.particle_settings.particle_count_min=target.particle_settings.particle_count_max=1
    _,plain=collect(project,parent,6)
    _,shifted=collect(project,parent,6,transform=EffectLayerTransform3D(position_x=8,position_y=3))
    assert [(v.x+8,v.y+3) for v in plain]==[(v.x,v.y) for v in shifted]


@pytest.mark.parametrize("blend",["normal","additive"])
def test_current_full_generated_playback_save_reload_png_and_transform(tmp_path,blend):
    from app.services.project_io import save_project,load_project
    project,parent,target=setup("both",True,True,blend_mode=blend)
    parent.layer_space_transform.rotation_x=20;parent.layer_space_transform.rotation_y=-10;parent.layer_space_transform.rotation_z=720
    parent.surface_transform.rotation_z=15
    full=render_effect_resource_layer(project,parent);generated=apply_effect_resource_layer(project,parent)
    apply_effect_resource_layer(project,target)
    paths=export_png_frames(project,tmp_path/"png")
    loaded=load_project(save_project(project,tmp_path/"test"))
    for t in (0,1,5,6,14,23):
        assert np.array_equal(full[t],render_effect_resource_layer_current_frame(project,parent,t))
        assert np.array_equal(full[t],project.frames[t].layer_pixels[generated.id])
        assert np.array_equal(project.compose_frame(t),render_exact_playback_frame(project,t)[0])
        assert np.array_equal(project.compose_frame(t),np.asarray(Image.open(paths[t])))
        assert np.array_equal(full[t],render_effect_resource_layer_current_frame(loaded,loaded.effect_resource_layers[0],t))
        assert full[t].shape==(48,48,4) and len(full)==24


def test_target_dependencies_and_rename():
    project,parent,target=setup(speed_min=2,speed_max=2)
    before=_base_key(project,parent);revision=playback_relevant_revision(project);pixel=collect(project,parent,8)[0]
    target.name="Renamed"
    assert _base_key(project,parent)==before and np.array_equal(pixel,collect(project,parent,8)[0])
    target.layer_space_transform.position_x=10;target.visible=True
    assert _base_key(project,parent)==before
    target.particle_settings.trail.enabled=True
    assert _base_key(project,parent)!=before and playback_relevant_revision(project)!=revision
    assert not np.array_equal(pixel,collect(project,parent,8)[0])


@pytest.mark.parametrize("cyclic",[False,True])
@pytest.mark.parametrize("trail",[False,True])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_both_off_frozen_v24_exact(cyclic,trail,blend):
    project,parent,target=setup("none",cyclic,trail,blend_mode=blend)
    parent.particle_settings.trail.enabled=trail;parent.particle_settings.blend_mode=blend
    frozen=types.ModuleType("frozen_v24_render");sys.modules[frozen.__name__]=frozen
    frozen_trail=types.ModuleType("frozen_v24_trail");sys.modules[frozen_trail.__name__]=frozen_trail
    for module,path in ((frozen,"particle_render_service"),(frozen_trail,"particle_trail_render_service")):
        source=subprocess.check_output(["git","show",f"2470af2:app/services/{path}.py"],text=True,encoding="utf-8")
        exec(compile(source,"<frozen v24>","exec"),module.__dict__)
    try:
        for frame in (0,5,14,23,100000):
            actual=collect(project,parent,frame)[0]
            with patch("app.services.particle_trail_render_service.render_particle_trails",frozen_trail.render_particle_trails):
                expected=frozen.render_particle_frame(project,parent.as_particle_emitter(),frame)
            assert np.array_equal(actual,expected)
    finally:
        sys.modules.pop(frozen.__name__,None);sys.modules.pop(frozen_trail.__name__,None)
