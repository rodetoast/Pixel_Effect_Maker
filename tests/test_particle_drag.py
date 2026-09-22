from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
import pytest
from PIL import Image

from app.models.animation_clip import AnimationClipAsset
from app.models.blend_mode import BLEND_ADDITIVE
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import LifetimeColorModulation, LifetimeScalarModulation, ParticleEmitter, ParticleEmitterSettings, ParticleInstance, ParticleMotionSettings
from app.models.project import Project
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer, render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.particle_natural_motion_service import effective_motion_age, gravity_displacement
from app.services.particle_render_service import build_particle_instances, evaluate_particle_motion, particle_motion_guide, particle_spawn_states, representative_particle_guide, render_particle_frame


def _settings(mode="linear", *, drag=True, strength=.2, gravity=0):
    return ParticleEmitterSettings("clip",drag_enabled=drag,drag_strength=strength,gravity_enabled=gravity!=0,gravity_strength=gravity,
        lifetime_min=20,lifetime_max=20,motion=ParticleMotionSettings(mode=mode,radius_start=4,radius_end=4,turns=1,axis_start=0,axis_end=10,helix_axis="z"))


def _instance(birth=0):
    return ParticleInstance(birth,20,10,10,2,0,1,0,0,0,1,31,particle_id=2,motion_phase_degrees=30)


def _position(settings,age,instance=None):
    instance=instance or _instance()
    return evaluate_particle_motion(settings,instance,age/instance.lifetime,particle_age=age)


def _project(*, drag=True,strength=.2,gravity=0,blend="normal",scale=None,color=None):
    project=Project.create_default(width=32,height=32,frame_count=8)
    clip=AnimationClipAsset("dot",[np.array([[[220,120,40,220]]],dtype=np.uint8)],pivot_x=0,pivot_y=0,playback_mode="hold");project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=8,particle_count_min=2,particle_count_max=2,
        emission_mode="over_time",emission_duration=3,lifetime_min=8,lifetime_max=8,origin_x=8,origin_y=8,
        speed_min=2,speed_max=2,direction_degrees=0,direction_spread_degrees=0,seed=23,
        drag_enabled=drag,drag_strength=strength,gravity_enabled=gravity!=0,gravity_strength=gravity,blend_mode=blend,
        scale_over_lifetime=scale or LifetimeScalarModulation(),color_over_lifetime=color or LifetimeColorModulation())
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("drag",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def test_drag_disabled_zero_strength_and_birth_are_exact_identity():
    assert effective_motion_age(7,False,.2)==7
    assert effective_motion_age(7,True,0)==7
    assert effective_motion_age(0,True,.2)==0
    assert _position(_settings(drag=False),5)==_position(_settings(strength=0),5)


@pytest.mark.parametrize("strength",[1e-12,1e-9,.001,.01,.1,.2,1,10])
def test_drag_expm1_formula_bounds_monotonic_and_finite(strength):
    ages=[0,1,5,20,512,1_000_000]
    values=[effective_motion_age(age,True,strength) for age in ages]
    assert all(math.isfinite(value) and 0<=value<=age for age,value in zip(ages,values,strict=True))
    assert values==sorted(values)
    assert values[2]==pytest.approx(-math.expm1(-strength*5)/strength)


def test_drag_linear_distance_direction_and_slowdown():
    settings=_settings(strength=.2);age=8;motion_age=-math.expm1(-.2*age)/.2
    result=_position(settings,age)
    assert result.x==pytest.approx(10+2*motion_age) and result.y==10
    positions=[_position(settings,age).x for age in range(5)]
    steps=[b-a for a,b in zip(positions,positions[1:])]
    assert steps==sorted(steps,reverse=True) and settings.speed_min==1


@pytest.mark.parametrize("mode",["orbit","helix"])
def test_drag_preserves_radius_center_initial_phase_and_slows_progression(mode):
    settings=_settings(mode,strength=.2);settings.motion.phase_spread_degrees=0
    initial=_position(settings,0);plain=_settings(mode,drag=False)
    assert initial==_position(plain,0)
    for age in (1,5,10):
        position=_position(settings,age)
        assert math.hypot(position.x-10,position.y-10)==pytest.approx(4)
        expected=_position(plain,effective_motion_age(age,True,.2))
        assert position==pytest.approx(expected)
    if mode=="helix":
        assert _position(settings,10).z < _position(plain,10).z


def test_drag_uses_actual_age_for_gravity_not_damped_age():
    settings=_settings(strength=.2,gravity=1.5)
    with_gravity=_position(settings,7)
    without=deepcopy(settings);without.gravity_enabled=False
    base=_position(without,7)
    assert with_gravity.y-base.y==pytest.approx(gravity_displacement(7,True,1.5))
    assert with_gravity.x==base.x


def test_drag_keeps_spawn_rng_and_cached_instances_identical():
    settings=_settings(drag=False);settings.particle_count_min=settings.particle_count_max=12
    before=build_particle_instances(settings,1);cached=particle_spawn_states(settings,1)
    settings.drag_enabled=True;settings.drag_strength=.2
    assert build_particle_instances(settings,1)==before and particle_spawn_states(settings,1) is cached


def test_drag_keeps_lifetime_tint_scale_alpha_and_sprite_timing():
    scale=LifetimeScalarModulation(True,.25,2,"Ease Out")
    color=LifetimeColorModulation(True,(255,255,255),(255,64,8),"Ease In")
    project,layer=_project(drag=False,scale=scale,color=color)
    off=[];render_particle_frame(project,layer.as_particle_emitter(),4,diagnostic_collector=off)
    layer.particle_settings.drag_enabled=True;layer.particle_settings.drag_strength=.2
    on=[];render_particle_frame(project,layer.as_particle_emitter(),4,diagnostic_collector=on)
    assert len(off)==len(on)
    for a,b in zip(off,on,strict=True):
        assert (a.age,a.lifetime,a.normalized_age,a.source_frame,a.opacity,a.scale,a.lifetime_tint_r,a.lifetime_tint_g,a.lifetime_tint_b)==(b.age,b.lifetime,b.normalized_age,b.source_frame,b.opacity,b.scale,b.lifetime_tint_r,b.lifetime_tint_g,b.lifetime_tint_b)


def test_drag_guide_uses_damped_base_motion_and_actual_gravity_age():
    settings=_settings("orbit",strength=.2,gravity=1)
    path=particle_motion_guide(settings,32,32,samples=3)
    instance=ParticleInstance(0,20,settings.origin_x,settings.origin_y,0,0,1,0,0,0,1,0)
    assert path[-1]==evaluate_particle_motion(settings,instance,19/20,particle_age=19)
    settings.motion.mode="linear"
    settings.direction_degrees=0
    guide=representative_particle_guide(settings)
    age=19
    assert guide["endpoint_x"]==pytest.approx(settings.origin_x+1.5*effective_motion_age(age,True,.2))
    assert guide["endpoint_y"]==pytest.approx(settings.origin_y+gravity_displacement(age,True,1))


def test_drag_cache_transitions_current_full_generated_png_parity(tmp_path):
    project,layer=_project(drag=False,gravity=.5,blend=BLEND_ADDITIVE,
        scale=LifetimeScalarModulation(True,.5,1.5),color=LifetimeColorModulation(True,(255,255,255),(255,32,16)))
    off=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.drag_enabled=True;layer.particle_settings.drag_strength=.05
    low=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.drag_strength=.2
    high=render_effect_resource_layer(project,layer)[5].copy()
    assert not np.array_equal(off,low) and not np.array_equal(low,high)
    full=render_effect_resource_layer(project,layer)
    assert all(np.array_equal(frame,render_effect_resource_layer_current_frame(project,layer,index)) for index,frame in enumerate(full))
    generated=apply_effect_resource_layer(project,layer,full)
    paths=export_png_frames(project,tmp_path/"png")
    for index,path in enumerate(paths):
        assert np.array_equal(full[index],project.frames[index].layer_pixels[generated.id])
        assert np.array_equal(np.asarray(Image.open(path)),project.compose_frame(index))
        assert np.asarray(Image.open(path)).shape==(32,32,4)
    layer.particle_settings.drag_enabled=False
    assert np.array_equal(render_effect_resource_layer(project,layer)[5],off)


def test_drag_direct_seek_is_independent_of_render_history_and_birth_time():
    project,layer=_project()
    instances=build_particle_instances(layer.particle_settings,1)
    assert {instance.birth_frame for instance in instances}=={0,2}
    target=render_effect_resource_layer_current_frame(project,layer,7).copy()
    for index in range(8):
        render_effect_resource_layer_current_frame(project,layer,index)
    assert np.array_equal(render_effect_resource_layer_current_frame(project,layer,7),target)
    assert np.array_equal(render_effect_resource_layer(project,layer)[7],target)
    assert effective_motion_age(7,True,.2)>effective_motion_age(5,True,.2)


def test_drag_preserves_parent_system_surface_2_5d_and_rotation_revolutions():
    project,parent=_project();child=deepcopy(parent);child.id="child";child.generated_layer_id=None;child.parent_id=parent.id;child.parent_offset=(1,0,3,0,1,-2,0,0,1)
    child.layer_space_transform.rotation_x=15;child.layer_space_transform.rotation_y=-20;child.layer_space_transform.rotation_z=720;child.layer_space_transform.perspective_strength=.2
    child.surface_transform.rotation_z=-360
    project.effect_resource_layers.append(child);project.repair_effect_hierarchy();before=deepcopy(child.to_dict())
    frames=render_effect_resource_layer(project,child)
    assert child.to_dict()==before and all(frame.shape==(32,32,4) for frame in frames)
