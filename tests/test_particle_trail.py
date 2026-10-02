from copy import deepcopy
from dataclasses import replace
import subprocess
import types
import sys
from unittest.mock import patch
import numpy as np
import pytest
from PIL import Image
from app.models.particle_emitter import ParticleTrailSettings as Trail, ParticleMotionSettings, LifetimeScalarModulation
from app.models.effect_resource_layer import EffectResourceLayer, EffectLayerTransform3D
from app.models.resource_composition import AnimationTrack
from app.services import particle_render_service as r
from app.services.particle_trail_render_service import iter_trail_samples
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies
from app.services.lifetime_modulation_service import normalized_lifetime_age, evaluate_lifetime_scalar_for_render, evaluate_lifetime_color_component
from app.services.effect_resource_layer_render_service import render_effect_resource_layer, render_effect_resource_layer_current_frame, apply_effect_resource_layer
from app.services.effect_playback_service import playback_relevant_revision, render_exact_playback_frame
from app.services.export_service import export_png_frames
from tests.test_particle_cyclic_emission import setup
from tests.test_lifetime_multi_point import curves


def scene(**changes):
    values=dict(emission_cycle_mode="one_shot",particle_count_min=1,particle_count_max=1,
        lifetime_min=5,lifetime_max=5,speed_min=1,speed_max=1,direction_degrees=0,direction_spread_degrees=0,
        opacity_start=1,opacity_end=1,random_start_frame=False,
        scale_over_lifetime=LifetimeScalarModulation(),trail=Trail(True))
    values.update(changes)
    return setup(**values)


def diagnostics(project,emitter,frame,**kwargs):
    values=[];pixels=r.render_particle_frame(project,emitter,frame,diagnostic_collector=values,**kwargs)
    return pixels,values


@pytest.mark.parametrize("duration,interval,expected",[(12,3,[9,6,3]),(12,2,[10,8,6,4,2]),(2,1,[1]),(240,239,[239]),(7,2,[6,4,2])])
def test_sample_formula_positive_offsets_and_linear_fade(duration,interval,expected):
    trail=Trail(True,duration,interval,.625)
    samples=list(iter_trail_samples(trail,240,1000))
    assert [delta for age,delta,factor in samples]==expected
    assert len(samples)==trail.sample_count and trail.delta_max==max(expected)
    for age,delta,factor in samples:
        assert 0<delta<duration and age==240-delta and factor==.625*(1-delta/duration)


def test_birth_has_no_trail_and_no_double_head_post_death_and_disappearance():
    project,emitter=scene()
    born,values=diagnostics(project,emitter,0)
    assert len(values)==1 and values[0].trail_delta==0
    off=deepcopy(emitter);off.settings.trail.enabled=False
    assert np.array_equal(born,r.render_particle_frame(project,off,0))
    for age in range(15):
        pixels,values=diagnostics(project,emitter,age)
        assert sum(d.trail_delta==0 for d in values)==int(age<5)
        assert len(values)==len({d.age for d in values})
        assert [d.age for d in values]==sorted(d.age for d in values)
        if age>=5:assert values and np.any(pixels[...,3])
    assert diagnostics(project,emitter,14)[1][-1].age==4
    pixels,values=diagnostics(project,emitter,15);assert values==[] and not np.any(pixels)


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
@pytest.mark.parametrize("g,d,n",[(False,False,False),(True,True,True),(True,False,True),(False,True,False)])
def test_historical_motion_sprite_rotation_and_multi_point_appearance(mode,g,d,n):
    project,emitter=scene(lifetime_min=16,lifetime_max=16,random_start_frame=True,clip_speed_min=.5,clip_speed_max=1.5,
        angular_velocity_min=17,angular_velocity_max=17,gravity_enabled=g,gravity_strength=.02,
        drag_enabled=d,drag_strength=.1,noise_enabled=n,noise_strength=2,noise_frequency=.12,
        motion=ParticleMotionSettings(mode=mode,radius_start=3,radius_end=7,turns=1,axis_start=-4,axis_end=5))
    curves(emitter.settings)
    settings=emitter.settings;slots=r.particle_spawn_states(settings,4)
    _,values=diagnostics(project,emitter,12)
    assert values and any(v.trail_delta for v in values)
    for value in values:
        slot=slots[value.particle_id];t=normalized_lifetime_age(value.age,slot.lifetime)
        expected=r.evaluate_particle_motion(settings,slot,value.age/slot.lifetime,12,particle_age=value.age)
        assert (value.local_x,value.local_y,value.local_z)==(expected.x,expected.y,expected.z)
        assert value.source_frame==r.particle_clip_frame_index(project.animation_clips[0],slot,value.age,project.fps)
        assert value.rotation==slot.rotation+slot.angular_velocity*value.age
        assert value.lifetime_scale==evaluate_lifetime_scalar_for_render(settings.scale_over_lifetime,t)
        assert value.lifetime_tint_g==evaluate_lifetime_color_component(settings.color_over_lifetime,t,1)
        multiplier=1 if value.trail_delta==0 else settings.trail.opacity*(1-value.trail_delta/settings.trail.duration_frames)
        assert value.opacity==evaluate_lifetime_scalar_for_render(settings.opacity_over_lifetime,t)*multiplier


@pytest.mark.parametrize("blend",["normal","additive"])
@pytest.mark.parametrize("lifetime,period,duration",[(3,6,12),(6,6,12),(16,6,12),(5,12,24),(1,6,12)])
def test_cyclic_steady_gate_tail_only_periodicity_large_reverse_seek(blend,lifetime,period,duration):
    project,emitter=scene(emission_cycle_mode="cyclic_steady",emission_period_frames=period,
        lifetime_min=lifetime,lifetime_max=lifetime,trail=Trail(True,duration,2),blend_mode=blend,
        gravity_enabled=True,gravity_strength=.02,drag_enabled=True,drag_strength=.1,noise_enabled=True,noise_strength=2)
    frame,values=diagnostics(project,emitter,0)
    assert any(d.cycle_index<0 for d in values)
    if lifetime<=period:assert any(d.copy_age>=lifetime for d in values)
    else:assert any(d.copy_age<lifetime and d.cycle_index<0 for d in values)
    full=r.render_particle_frames(project,emitter)
    for t in (23,0,17,2,5,1,0,100000):
        assert np.array_equal(r.render_particle_frame(project,emitter,t),r.render_particle_frame(project,emitter,t%period))
        if t<24:assert np.array_equal(full[t],r.render_particle_frame(project,emitter,t))
    slots=r.particle_spawn_states(emitter.settings,4)
    copies=list(iter_particle_cycle_copies(emitter.settings,slots,0,visibility_extension_frames=emitter.settings.trail.delta_max))
    assert any(-c.birth_frame>=lifetime for c in copies)
    assert all(c.canonical is slots[c.particle_id] for c in copies)


@pytest.mark.parametrize("blend",["normal","additive"])
def test_order_oldest_newest_head_and_tail_only_depth(blend):
    project,emitter=scene(emission_cycle_mode="cyclic_steady",particle_count_min=3,particle_count_max=3,
        lifetime_min=5,lifetime_max=5,blend_mode=blend,motion=ParticleMotionSettings(mode="helix",axis_end=8))
    _,values=diagnostics(project,emitter,6)
    groups={}
    for value in values:groups.setdefault(value.copy_key,[]).append(value)
    keys=[]
    for group in groups.values():
        assert [v.trail_delta for v in group]==sorted((v.trail_delta for v in group),reverse=True)
        assert all(v.depth_key==group[-1].depth_key for v in group)
        assert group[-1].depth_key[0]==group[-1].z
        if group[-1].copy_age<group[-1].lifetime:assert group[-1].trail_delta==0
        else:assert all(v.trail_delta>0 for v in group)
        keys.append(group[-1].depth_key)
    assert keys==sorted(keys)


@pytest.mark.parametrize("field,value",[("enabled",False),("duration_frames",17),("sample_interval_frames",3),("opacity",.625)])
def test_cache_invalidation_spawn_identity_no_rng(field,value):
    project,emitter=scene();settings=emitter.settings;slots=r.particle_spawn_states(settings,4)
    before=r.render_particle_frame(project,emitter,6)
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer)
    revision=playback_relevant_revision(project)
    setattr(settings.trail,field,value);setattr(layer.particle_settings.trail,field,value)
    assert playback_relevant_revision(project)!=revision
    with patch.object(r.random,"Random",side_effect=AssertionError("new RNG")):
        assert r.particle_spawn_states(settings,4) is slots
        after=r.render_particle_frame(project,emitter,6)
    assert not np.array_equal(before,after)


@pytest.fixture(scope="module")
def frozen_v23():
    module=types.ModuleType("pem_v23_frozen");sys.modules[module.__name__]=module
    source=subprocess.check_output(["git","show","9cf4a41:app/services/particle_render_service.py"],text=True,encoding="utf-8")
    exec(compile(source,"<frozen v23>","exec"),module.__dict__)
    yield module
    sys.modules.pop(module.__name__,None)


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
@pytest.mark.parametrize("cycle",["one_shot","cyclic_steady"])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_disabled_frozen_v23_exact(frozen_v23,mode,cycle,blend):
    project,emitter=scene(emission_cycle_mode=cycle,blend_mode=blend,lifetime_min=16,lifetime_max=16,
        trail=Trail(False,41,5,.3125),gravity_enabled=True,gravity_strength=.02,drag_enabled=True,drag_strength=.1,
        noise_enabled=True,noise_strength=2,motion=ParticleMotionSettings(mode=mode,radius_start=3,radius_end=6,axis_end=5))
    curves(emitter.settings)
    with patch("app.services.particle_trail_render_service.render_particle_trails",side_effect=AssertionError("off path trail")):
        for frame in (0,1,5,15,23,100000):assert np.array_equal(frozen_v23.render_particle_frame(project,emitter,frame),r.render_particle_frame(project,emitter,frame))


@pytest.mark.parametrize("cyclic",[False,True])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_parent_current_snapshot_system_surface_2_5d_parity_post_death_png(tmp_path,cyclic,blend):
    project,emitter=scene(emission_cycle_mode="cyclic_steady" if cyclic else "one_shot",blend_mode=blend)
    layer=EffectResourceLayer.from_particle_emitter(emitter);layer.layer_space_transform.rotation_x=25;layer.layer_space_transform.rotation_y=-15;layer.layer_space_transform.rotation_z=720
    layer.surface_transform.rotation_z=12
    parent=deepcopy(layer);parent.id="parent";parent.visible=False;parent.generated_layer_id=None
    parent.layer_space_transform.position_x=3
    parent.layer_space_transform.tracks["position_x"]=AnimationTrack("position_x",0)
    parent.layer_space_transform.tracks["position_x"].set_keyframe(0,0);parent.layer_space_transform.tracks["position_x"].set_keyframe(23,7)
    layer.parent_id=parent.id;layer.parent_offset=(1,0,2,0,1,-1,0,0,1)
    project.effect_resource_layers.extend((parent,layer));project.repair_effect_hierarchy();before=deepcopy(layer.to_dict())
    full=render_effect_resource_layer(project,layer);generated=apply_effect_resource_layer(project,layer)
    paths=export_png_frames(project,tmp_path/"png")
    for t in (0,3,5,6,14,15,23):
        assert np.array_equal(full[t],render_effect_resource_layer_current_frame(project,layer,t))
        assert np.array_equal(full[t],project.frames[t].layer_pixels[generated.id])
        assert np.array_equal(project.compose_frame(t),render_exact_playback_frame(project,t)[0])
        assert np.array_equal(project.compose_frame(t),np.asarray(Image.open(paths[t])))
        assert full[t].shape==(48,48,4)
    # Timing metadata is not extended by Trail, only generated_layer_id changes.
    assert layer.start_frame==before["start_frame"] and layer.end_frame==before["end_frame"] and len(project.frames)==24
    if not cyclic:assert np.any(full[6][...,3]) and not np.any(full[15][...,3])
    transform=EffectLayerTransform3D(position_x=8)
    pixels,values=diagnostics(project,emitter,6,layer_space_transform=transform)
    assert values and all(v.x==v.local_x+8 for v in values)
    assert all(v.trail_delta for v in values) if not cyclic else True


def test_trail_borrows_source_pixels_without_source_asset_copy_or_rng():
    project,emitter=scene()
    clip=r._resolve_particle_clip(project,emitter.settings)
    original=[frame.copy() for frame in clip.frames]
    r.particle_spawn_states(emitter.settings,len(clip.frames))
    with patch.object(r,"SourceAsset",side_effect=AssertionError("source copy")), patch.object(r.random,"Random",side_effect=AssertionError("RNG")):
        assert np.any(r.render_particle_frame(project,emitter,6)[...,3])
    assert all(np.array_equal(before,after) for before,after in zip(original,clip.frames))


@pytest.mark.parametrize("blend",["normal","additive"])
def test_trail_opacity_layer_alpha_and_rgb_are_independent(blend):
    project,emitter=scene(blend_mode=blend)
    curves(emitter.settings)
    original,values=diagnostics(project,emitter,6)
    transformed=r.render_particle_frame(project,emitter,6,layer_space_transform=EffectLayerTransform3D(opacity=.5))
    assert np.array_equal(transformed[...,:3],original[...,:3])
    assert np.array_equal(transformed[...,3],np.rint(original[...,3].astype(np.float64)*.5).astype(np.uint8))
    emitter.settings.trail.opacity=.3125
    _,changed=diagnostics(project,emitter,6)
    assert [(v.lifetime_tint_r,v.lifetime_tint_g,v.lifetime_tint_b) for v in changed]==[(v.lifetime_tint_r,v.lifetime_tint_g,v.lifetime_tint_b) for v in values]
    assert [v.opacity for v in changed]==pytest.approx([v.opacity*(.3125/.75) for v in values])


def test_current_transform_snapshot_does_not_replay_past_transform_keys():
    project,emitter=scene()
    first=EffectLayerTransform3D()
    first.tracks["position_x"]=AnimationTrack("position_x",0)
    first.tracks["position_x"].set_keyframe(0,-20)
    first.tracks["position_x"].set_keyframe(6,8)
    second=deepcopy(first)
    second.tracks["position_x"].set_keyframe(0,20)
    assert np.array_equal(r.render_particle_frame(project,emitter,6,layer_space_transform=first),r.render_particle_frame(project,emitter,6,layer_space_transform=second))
