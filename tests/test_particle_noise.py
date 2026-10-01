from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
import pytest
from PIL import Image

from app.models.animation_clip import AnimationClipAsset
from app.models.blend_mode import BLEND_ADDITIVE
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import (
    LifetimeColorModulation, LifetimeScalarModulation, ParticleEmitter,
    ParticleEmitterSettings, ParticleInstance, ParticleMotionSettings,
)
from app.models.project import Project
from app.services.effect_resource_layer_render_service import (
    apply_effect_resource_layer, render_effect_resource_layer,
    render_effect_resource_layer_current_frame,
)
from app.services.export_service import export_png_frames
from app.services.particle_noise_service import (
    lattice_value, mix64, particle_noise_offset, particle_noise_seeds,
    quintic_fade, smooth_value_noise,
)
from app.services.particle_render_service import (
    build_particle_instances, evaluate_particle_motion, particle_motion_guide,
    particle_spawn_states, render_particle_frame,
)


def _settings(mode="linear", **overrides):
    values=dict(noise_enabled=True,noise_strength=3.125,noise_frequency=.1,
        drag_enabled=True,drag_strength=.2,gravity_enabled=True,gravity_strength=.5,
        lifetime_min=20,lifetime_max=20,seed=23,
        motion=ParticleMotionSettings(mode=mode,radius_start=4,radius_end=4,turns=1,
            axis_start=0,axis_end=10,helix_axis="z"))
    values.update(overrides)
    return ParticleEmitterSettings("clip",**values)


def _instance(particle_id=7, birth=0):
    return ParticleInstance(birth,20,10,10,2,0,1,0,0,0,1,31,particle_id=particle_id)


def _position(settings,age,instance=None):
    instance=instance or _instance()
    return evaluate_particle_motion(settings,instance,age/instance.lifetime,particle_age=age)


def _project(**overrides):
    project=Project.create_default(width=32,height=32,frame_count=8)
    clip=AnimationClipAsset("dot",[np.array([[[220,120,40,220]]],dtype=np.uint8)],pivot_x=0,pivot_y=0,playback_mode="hold")
    project.animation_clips.append(clip)
    values=dict(output_frame_count=8,particle_count_min=2,particle_count_max=2,
        emission_mode="over_time",emission_duration=3,lifetime_min=8,lifetime_max=8,
        origin_x=8,origin_y=8,speed_min=2,speed_max=2,direction_degrees=0,
        seed=23,noise_enabled=True,noise_strength=3.125,noise_frequency=.1)
    values.update(overrides)
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("noise",ParticleEmitterSettings(clip.id,**values)))
    project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def test_fixed_integer_mixer_lattice_and_axis_sentinels():
    assert mix64(0)==0xE220A8397B1DCDAF
    assert particle_noise_seeds(23,7)==(2525515013692760755,11259770399353984268)
    assert lattice_value(particle_noise_seeds(23,7)[0],0)==0
    assert lattice_value(particle_noise_seeds(23,7)[0],1)==0.5048677975042288
    assert particle_noise_seeds(23,7)!=particle_noise_seeds(23,8)
    assert particle_noise_seeds(23,7)[0]!=particle_noise_seeds(23,7)[1]


@pytest.mark.parametrize("enabled,strength,frequency,age",[
    (False,3,.1,5),(True,0,.1,5),(True,3,0,5),(True,3,.1,0),
])
def test_noise_identity_and_exact_birth(enabled,strength,frequency,age):
    assert particle_noise_offset(23,7,age,enabled,strength,frequency)==(0,0)


def test_quintic_fade_value_derivative_and_lattice_continuity():
    assert quintic_fade(0)==0 and quintic_fade(1)==1
    seed=particle_noise_seeds(23,7)[0]
    for boundary in (1,2,10):
        center=smooth_value_noise(seed,boundary)
        assert center==lattice_value(seed,boundary)
        assert abs(smooth_value_noise(seed,boundary-1e-5)-center)<1e-8
        assert abs(smooth_value_noise(seed,boundary+1e-5)-center)<1e-8


@pytest.mark.parametrize("age,frequency,strength",[(.001,.0001,3),(5,.1,3.125),(512,1,4096),(10**6,.01,100)])
def test_noise_bounds_finite_large_age_and_frequency(age,frequency,strength):
    x,y=particle_noise_offset(2**63+17,2**40+3,age,True,strength,frequency)
    assert math.isfinite(x) and math.isfinite(y)
    assert abs(x)<=strength+1e-10 and abs(y)<=strength+1e-10


def test_same_identity_same_age_is_exact_and_different_particles_are_independent():
    first=particle_noise_offset(23,7,5,True,3.125,.1)
    assert first==particle_noise_offset(23,7,5,True,3.125,.1)
    assert first!=particle_noise_offset(23,8,5,True,3.125,.1)
    ids=[7,8,9,10]
    forward={pid:particle_noise_offset(23,pid,5,True,3.125,.1) for pid in ids}
    reverse={pid:particle_noise_offset(23,pid,5,True,3.125,.1) for pid in reversed(ids)}
    assert forward==reverse


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_noise_is_positional_xy_after_drag_and_gravity(mode):
    settings=_settings(mode)
    plain=deepcopy(settings);plain.noise_enabled=False
    before=plain.to_dict();age=7;instance=_instance()
    actual=_position(settings,age,instance);base=_position(plain,age,instance)
    dx,dy=particle_noise_offset(settings.seed,instance.particle_id,age,True,3.125,.1)
    assert actual.x-base.x==pytest.approx(dx)
    assert actual.y-base.y==pytest.approx(dy)
    assert actual.z==base.z
    assert plain.to_dict()==before
    settings.drag_strength=1
    stronger_drag=_position(settings,age,instance)
    stronger_plain=deepcopy(settings);stronger_plain.noise_enabled=False
    no_noise=_position(stronger_plain,age,instance)
    assert stronger_drag.x-no_noise.x==pytest.approx(dx)
    assert stronger_drag.y-no_noise.y==pytest.approx(dy)


def test_noise_does_not_change_spawn_draws_or_cached_instances():
    settings=_settings(noise_enabled=False,particle_count_min=12,particle_count_max=12)
    before=build_particle_instances(settings,3);cached=particle_spawn_states(settings,3)
    settings.noise_enabled=True;settings.noise_strength=8;settings.noise_frequency=.5
    assert build_particle_instances(settings,3)==before
    assert particle_spawn_states(settings,3) is cached


def test_noise_does_not_change_lifetime_scale_color_opacity_or_sprite_frame():
    project,layer=_project(noise_enabled=False,
        scale_over_lifetime=LifetimeScalarModulation(True,.25,2,"Ease Out"),
        color_over_lifetime=LifetimeColorModulation(True,(255,255,255),(255,64,8),"Ease In"))
    off=[];render_particle_frame(project,layer.as_particle_emitter(),4,diagnostic_collector=off)
    layer.particle_settings.noise_enabled=True
    on=[];render_particle_frame(project,layer.as_particle_emitter(),4,diagnostic_collector=on)
    assert len(off)==len(on)
    for a,b in zip(off,on,strict=True):
        assert (a.particle_id,a.spawn_frame,a.lifetime,a.age,a.normalized_age,a.source_frame,a.opacity,a.scale,a.lifetime_tint_r,a.lifetime_tint_g,a.lifetime_tint_b)==(b.particle_id,b.spawn_frame,b.lifetime,b.age,b.normalized_age,b.source_frame,b.opacity,b.scale,b.lifetime_tint_r,b.lifetime_tint_g,b.lifetime_tint_b)


def test_noise_guide_uses_fixed_representative_particle():
    settings=_settings("orbit")
    path=particle_motion_guide(settings,32,32,samples=3)
    instance=ParticleInstance(0,20,settings.origin_x,settings.origin_y,0,0,1,0,0,0,1,0)
    assert path==particle_motion_guide(settings,32,32,samples=3)
    assert path[-1]==evaluate_particle_motion(settings,instance,19/20,particle_age=19)


def test_noise_guide_matches_surviving_age_without_drag():
    settings=_settings("orbit",drag_enabled=False)
    settings.motion.radius_end=10
    path=particle_motion_guide(settings,32,32,samples=3)
    instance=ParticleInstance(0,20,settings.origin_x,settings.origin_y,0,0,1,0,0,0,1,0)
    assert path[-1]==evaluate_particle_motion(settings,instance,19/20,particle_age=19)


def test_noise_cache_transitions_direct_seek_full_generated_png(tmp_path):
    project,layer=_project(noise_enabled=False,gravity_enabled=True,gravity_strength=.5,
        drag_enabled=True,drag_strength=.2,blend_mode=BLEND_ADDITIVE,
        scale_over_lifetime=LifetimeScalarModulation(True,.5,1.5),
        color_over_lifetime=LifetimeColorModulation(True,(255,255,255),(255,32,16)))
    off=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.noise_enabled=True
    low=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.noise_strength=8
    strong=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.noise_frequency=.3
    fast=render_effect_resource_layer(project,layer)[5].copy()
    assert not np.array_equal(off,low) and not np.array_equal(low,strong) and not np.array_equal(strong,fast)
    direct=render_effect_resource_layer_current_frame(project,layer,5).copy()
    full=render_effect_resource_layer(project,layer)
    assert np.array_equal(direct,full[5])
    for index in range(8):render_effect_resource_layer_current_frame(project,layer,index)
    assert np.array_equal(render_effect_resource_layer_current_frame(project,layer,5),direct)
    generated=apply_effect_resource_layer(project,layer,full)
    paths=export_png_frames(project,tmp_path/"noise")
    for index,path in enumerate(paths):
        assert np.array_equal(full[index],project.frames[index].layer_pixels[generated.id])
        assert np.array_equal(np.asarray(Image.open(path)),project.compose_frame(index))
        assert np.asarray(Image.open(path)).shape==(32,32,4)
    layer.particle_settings.noise_enabled=False
    assert np.array_equal(render_effect_resource_layer(project,layer)[5],off)


def test_noise_preserves_parent_system_surface_2_5d_and_revolutions():
    project,parent=_project()
    child=deepcopy(parent);child.id="child";child.generated_layer_id=None;child.parent_id=parent.id
    child.parent_offset=(1,0,3,0,1,-2,0,0,1)
    child.layer_space_transform.rotation_x=15;child.layer_space_transform.rotation_y=-20
    child.layer_space_transform.rotation_z=720;child.layer_space_transform.perspective_strength=.2
    child.surface_transform.rotation_z=-360
    project.effect_resource_layers.append(child);project.repair_effect_hierarchy();before=deepcopy(child.to_dict())
    frames=render_effect_resource_layer(project,child)
    assert child.to_dict()==before and all(frame.shape==(32,32,4) for frame in frames)
