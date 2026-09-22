from __future__ import annotations

from copy import deepcopy

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
from app.services.lifetime_modulation_service import normalized_lifetime_age
from app.services.particle_natural_motion_service import gravity_displacement
from app.services.particle_render_service import PARTICLE_RENDER_STATS, build_particle_instances, evaluate_particle_motion, particle_motion_guide, particle_spawn_states, render_particle_frame


def _instance(*, birth=0, lifetime=10):
    return ParticleInstance(birth,lifetime,10,8,2,-1,1,0,0,0,1,17,particle_id=3,motion_phase_degrees=15)


def _settings(mode="linear", *, enabled=True, strength=2.0):
    return ParticleEmitterSettings("clip",gravity_enabled=enabled,gravity_strength=strength,
        lifetime_min=10,lifetime_max=10,speed_min=1,speed_max=1,direction_spread_degrees=0,
        motion=ParticleMotionSettings(mode=mode,radius_start=4,radius_end=4,start_angle_degrees=10,turns=.5,axis_start=-2,axis_end=3,helix_axis="z"))


def _position(settings,age,instance=None):
    instance=instance or _instance();return evaluate_particle_motion(settings,instance,age/instance.lifetime,particle_age=age)


def _project(*, strength=1.0, blend="normal", scale=None, color=None):
    project=Project.create_default(width=32,height=32,fps=12,frame_count=8)
    clip=AnimationClipAsset("dot",[np.array([[[220,120,40,220]]],dtype=np.uint8)],fps=12,pivot_x=0,pivot_y=0,playback_mode="hold");project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=8,particle_count_min=2,particle_count_max=2,
        emission_mode="over_time",emission_duration=3,lifetime_min=8,lifetime_max=8,origin_x=8,origin_y=8,
        speed_min=1,speed_max=1,direction_degrees=-90,direction_spread_degrees=0,seed=23,
        gravity_enabled=True,gravity_strength=strength,blend_mode=blend,
        scale_over_lifetime=scale or LifetimeScalarModulation(),color_over_lifetime=color or LifetimeColorModulation())
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("gravity",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy();return project,layer


def _diagnostics(project,layer,frame):
    values=[];render_particle_frame(project,layer.as_particle_emitter(),frame,diagnostic_collector=values);return values


def test_gravity_disabled_and_zero_strength_have_zero_offset():
    baseline=_position(_settings(enabled=False,strength=99),4)
    zero=_position(_settings(enabled=True,strength=0),4)
    expected=_position(_settings(enabled=False,strength=0),4)
    assert baseline==expected==zero


def test_gravity_birth_direction_and_half_at_squared_formula():
    assert gravity_displacement(0,True,2)==0
    assert gravity_displacement(3,True,2)==9
    assert gravity_displacement(3,True,-2)==-9
    base=_position(_settings(enabled=False),3);down=_position(_settings(strength=2),3);up=_position(_settings(strength=-2),3)
    assert down.x==up.x==base.x and down.y-base.y==pytest.approx(9) and up.y-base.y==pytest.approx(-9)


def test_gravity_uses_particle_age_not_composition_frame_or_normalized_lifetime():
    settings=_settings(strength=1.5);instance=_instance(birth=20,lifetime=10)
    at_birth=evaluate_particle_motion(settings,instance,0,effect_frame=20,particle_age=0)
    later=evaluate_particle_motion(settings,instance,.3,effect_frame=23,particle_age=3)
    assert at_birth.y==8 and later.y-(8-3)==pytest.approx(.5*1.5*9)
    assert normalized_lifetime_age(3,10)!=3 and gravity_displacement(3,True,1.5)==pytest.approx(6.75)


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_gravity_adds_after_base_motion_without_changing_xyz_contract(mode):
    base=_settings(mode,enabled=False);gravity=_settings(mode,strength=1.25);age=4
    a=_position(base,age);b=_position(gravity,age)
    assert b.x==pytest.approx(a.x) and b.z==pytest.approx(a.z)
    assert b.y-a.y==pytest.approx(.5*1.25*age*age)
    assert gravity.motion==base.motion


def test_orbit_and_helix_radius_phase_axis_are_preserved():
    for mode in ("orbit","helix"):
        settings=_settings(mode,strength=3);plain=deepcopy(settings);plain.gravity_enabled=False
        for age in (0,2,7):
            a=_position(plain,age);b=_position(settings,age)
            assert (b.x,b.y-gravity_displacement(age,True,3),b.z)==pytest.approx((a.x,a.y,a.z))


def test_different_birth_times_have_independent_gravity_displacement():
    project,layer=_project(strength=2);values=_diagnostics(project,layer,3);by_birth={item.spawn_frame:item for item in values}
    assert set(by_birth)=={0,2}
    assert by_birth[0].local_y-by_birth[2].local_y==pytest.approx(6)


def test_gravity_does_not_consume_random_draws_or_change_spawn_identity():
    settings=_settings(enabled=False);settings.particle_count_min=settings.particle_count_max=20
    before=build_particle_instances(deepcopy(settings),4);settings.gravity_enabled=True;settings.gravity_strength=-.625
    after=build_particle_instances(settings,4)
    assert before==after


def test_gravity_changes_reuse_spawn_cache_but_change_render_cache_identity():
    settings=_settings(enabled=False);settings.particle_count_min=settings.particle_count_max=4
    before_hits=PARTICLE_RENDER_STATS["spawn_cache_hits"];first=particle_spawn_states(settings,2)
    settings.gravity_enabled=True;settings.gravity_strength=1;second=particle_spawn_states(settings,2)
    settings.gravity_strength=2;third=particle_spawn_states(settings,2)
    settings.gravity_enabled=False;fourth=particle_spawn_states(settings,2)
    assert first is second is third is fourth and PARTICLE_RENDER_STATS["spawn_cache_hits"]>=before_hits+3


def test_gravity_direct_seek_current_full_and_generated_are_exact():
    project,layer=_project(strength=1.25);full=render_effect_resource_layer(project,layer)
    direct=[render_effect_resource_layer_current_frame(project,layer,index).copy() for index in range(8)]
    assert all(np.array_equal(a,b) for a,b in zip(full,direct,strict=True))
    generated=apply_effect_resource_layer(project,layer,full)
    assert all(np.array_equal(project.frames[index].layer_pixels[generated.id],full[index]) for index in range(8))


def test_gravity_png_export_matches_generated_output_and_dimensions(tmp_path):
    project,layer=_project(strength=.75,blend=BLEND_ADDITIVE);full=render_effect_resource_layer(project,layer);apply_effect_resource_layer(project,layer,full)
    paths=export_png_frames(project,tmp_path/"gravity-png")
    assert len(paths)==8
    for index,path in enumerate(paths):
        decoded=np.asarray(Image.open(path));assert decoded.shape==(32,32,4) and np.array_equal(decoded,project.compose_frame(index))


def test_gravity_enable_strength_disable_never_returns_stale_base_frames():
    project,layer=_project(strength=0);layer.particle_settings.gravity_enabled=False;off=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.gravity_enabled=True;layer.particle_settings.gravity_strength=1;one=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.gravity_strength=2;two=render_effect_resource_layer(project,layer)[5].copy()
    layer.particle_settings.gravity_enabled=False;restored=render_effect_resource_layer(project,layer)[5].copy()
    assert not np.array_equal(off,one) and not np.array_equal(one,two) and np.array_equal(off,restored)


def test_gravity_preserves_parent_system_surface_and_2_5d_state():
    project,parent=_project(strength=1);child=deepcopy(parent);child.id="gravity-child";child.generated_layer_id=None;child.parent_id=parent.id;child.parent_offset=(1,0,3,0,1,-2,0,0,1)
    child.layer_space_transform.position_z=2;child.layer_space_transform.rotation_x=15;child.layer_space_transform.rotation_y=-20;child.layer_space_transform.rotation_z=720;child.layer_space_transform.perspective_strength=.2
    child.surface_transform.position_x=1;child.surface_transform.rotation_z=-360
    project.effect_resource_layers.append(child);project.repair_effect_hierarchy();before=deepcopy(child.to_dict());frames=render_effect_resource_layer(project,child)
    assert child.to_dict()==before and child.parent_id==parent.id and child.parent_offset==(1,0,3,0,1,-2,0,0,1)
    assert all(frame.shape==(32,32,4) for frame in frames)


def test_gravity_scale_color_additive_combination_is_deterministic():
    project,layer=_project(strength=1.5,blend=BLEND_ADDITIVE,
        scale=LifetimeScalarModulation(True,.25,1.5,"Ease Out"),
        color=LifetimeColorModulation(True,(255,255,255),(255,64,8),"Ease In"))
    first=render_effect_resource_layer(project,layer);second=render_effect_resource_layer(project,layer)
    assert all(np.array_equal(a,b) for a,b in zip(first,second,strict=True))
    assert layer.particle_settings.scale_over_lifetime.enabled and layer.particle_settings.color_over_lifetime.enabled


def test_gravity_guide_uses_renderer_evaluator_and_representative_age():
    settings=_settings("orbit",strength=2);path=particle_motion_guide(settings,64,64,samples=3)
    instance=ParticleInstance(0,10,settings.origin_x,settings.origin_y,0,0,1,0,0,0,1,0)
    expected=evaluate_particle_motion(settings,instance,1,particle_age=9)
    plain=_settings("orbit",enabled=False)
    base=evaluate_particle_motion(plain,instance,1,particle_age=9)
    assert path[-1]==expected and path[-1].y-base.y==pytest.approx(81)


def test_large_ui_range_gravity_stays_finite_and_output_is_strictly_clipped():
    assert np.isfinite(gravity_displacement(511,True,1024))
    project,layer=_project(strength=1024);frames=render_effect_resource_layer(project,layer)
    assert all(frame.shape==(32,32,4) for frame in frames)
