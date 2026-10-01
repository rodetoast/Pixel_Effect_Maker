from __future__ import annotations

from dataclasses import replace
import hashlib
from unittest.mock import patch
import numpy as np
import pytest
from PIL import Image
from app.models.animation_clip import AnimationClipAsset
from app.models.particle_emitter import (ParticleEmitter, ParticleEmitterSettings,
    ParticleMotionSettings, LifetimeScalarModulation, LifetimeColorModulation)
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import Project
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies
from app.services.particle_render_service import (build_particle_instances, particle_spawn_states,
    render_particle_frame, render_particle_frames, invalidate_particle_render_caches)
from app.services.effect_resource_layer_render_service import (
    render_effect_resource_layer, render_effect_resource_layer_current_frame,
    apply_effect_resource_layer)
from app.services.effect_playback_service import playback_relevant_revision
from app.services.export_service import export_png_frames
from app.services.lifetime_modulation_service import normalized_lifetime_age, evaluate_lifetime_scalar
from app.services.particle_natural_motion_service import effective_motion_age, gravity_displacement
from app.services.particle_noise_service import particle_noise_offset


def setup(**changes):
    project=Project.create_default(width=48,height=48,frame_count=24)
    pixels=np.full((3,3,4),255,np.uint8)
    frames=[pixels.copy() for _ in range(4)]
    for i,frame in enumerate(frames):frame[...,1]=200-i*30
    clip=AnimationClipAsset("sprite",frames,fps=project.fps,playback_mode="loop")
    project.animation_clips.append(clip)
    values=dict(clip_asset_id=clip.id,output_frame_count=24,origin_x=24,origin_y=24,
        emission_cycle_mode="cyclic_steady",emission_period_frames=6,
        particle_count_min=3,particle_count_max=3,lifetime_min=16,lifetime_max=16,
        speed_min=.25,speed_max=.8,direction_spread_degrees=50,seed=21022,
        opacity_start=.8,opacity_end=.1,random_start_frame=True,
        scale_over_lifetime=LifetimeScalarModulation(True,.5,1.5),
        color_over_lifetime=LifetimeColorModulation(True,(255,255,255),(255,40,10)))
    values.update(changes)
    emitter=ParticleEmitter("cyclic",ParticleEmitterSettings(**values))
    return project,emitter


@pytest.mark.parametrize("blend",["normal","additive"])
@pytest.mark.parametrize("mode",["linear","orbit","helix"])
@pytest.mark.parametrize("g,d,n",[(False,False,False),(True,True,False),(False,True,True),(True,True,True)])
def test_periodicity_motion_blend_and_large_seek(blend,mode,g,d,n):
    project,emitter=setup(blend_mode=blend,gravity_enabled=g,gravity_strength=.02,
        drag_enabled=d,drag_strength=.1,noise_enabled=n,noise_strength=2,noise_frequency=.12,
        motion=ParticleMotionSettings(mode=mode,radius_start=4,radius_end=6,
            turns=1,phase_spread_degrees=360,axis_end=6))
    frames=render_particle_frames(project,emitter)
    assert any(np.any(frame[...,3]) for frame in frames)
    for t in (0,1,5,6,7,11):
        for shift in (0,6,12):
            assert np.array_equal(frames[t],render_particle_frame(project,emitter,t+shift))
    assert np.array_equal(render_particle_frame(project,emitter,100000),frames[100000%6])
    for t in (23,0,17,2,17,0):assert np.array_equal(frames[t],render_particle_frame(project,emitter,t))


@pytest.mark.parametrize("lifetime,period",[(1,1),(1,6),(6,6),(7,6),(16,6),(96,12),(512,512)])
def test_alive_integer_bounds_and_steady_gate(lifetime,period):
    project,emitter=setup(lifetime_min=lifetime,lifetime_max=lifetime,
        emission_period_frames=period,start_frame=7)
    slots=build_particle_instances(emitter.settings,4)
    assert list(iter_particle_cycle_copies(emitter.settings,slots,6))==[]
    assert not np.any(render_particle_frame(project,emitter,6))
    for frame in (7,8,7+period-1,7+period,100000):
        copies=list(iter_particle_cycle_copies(emitter.settings,slots,frame))
        expected={(k,s.particle_id) for s in slots
            for k in range((frame-7)//period-lifetime//period-2,(frame-7)//period+2)
            if 0<=frame-(s.birth_frame+k*period)<s.lifetime}
        assert {copy.copy_key for copy in copies}==expected
        assert len({copy.copy_key for copy in copies})==len(copies)
        assert all(copy.canonical is slots[copy.particle_id] for copy in copies)
    if lifetime>period:assert any(copy.cycle_index<0 for copy in iter_particle_cycle_copies(emitter.settings,slots,7))


@pytest.mark.parametrize("schedule,count,duration,delay",[("burst",3,99,2),("over_time",5,5,1),("over_time",1,99,2),("burst",0,99,99)])
def test_canonical_schedule_and_rng_reuse(schedule,count,duration,delay):
    project,emitter=setup(emission_mode=schedule,particle_count_min=count,particle_count_max=count,
        emission_duration=duration,start_delay_min=delay,start_delay_max=delay)
    s=emitter.settings
    old=replace(s,emission_cycle_mode="one_shot",emission_period_frames=41)
    assert build_particle_instances(s,4)==build_particle_instances(old,4)
    for i,slot in enumerate(build_particle_instances(s,4)):
        spread=0 if schedule=="burst" or count<=1 else round(i*(duration-1)/(count-1))
        assert slot.birth_frame==spread+delay
    invalidate_particle_render_caches()
    canonical=particle_spawn_states(old,4)
    with patch("app.services.particle_render_service.random.Random",side_effect=AssertionError("new RNG")):
        assert particle_spawn_states(s,4) is canonical
        assert particle_spawn_states(replace(s,emission_period_frames=12),4) is canonical
        for t in (0,100000):list(iter_particle_cycle_copies(s,canonical,t))
        render_particle_frame(project,emitter,100000)


def test_prewarm_all_channels_use_copy_age_and_canonical_noise():
    project,emitter=setup(particle_count_min=1,particle_count_max=1,
        gravity_enabled=True,gravity_strength=.02,drag_enabled=True,drag_strength=.1,
        noise_enabled=True,noise_strength=2,noise_frequency=.12,direction_degrees=0,
        direction_spread_degrees=0,speed_min=1,speed_max=1)
    s=emitter.settings;slot=build_particle_instances(s,4)[0];diagnostics=[]
    render_particle_frame(project,emitter,0,diagnostic_collector=diagnostics)
    assert {x.age for x in diagnostics}=={0,6,12}
    from app.services.particle_render_service import particle_clip_frame_index
    for value in diagnostics:
        age=value.age;t=normalized_lifetime_age(age,16)
        nx,ny=particle_noise_offset(s.seed,slot.particle_id,age,True,2,.12)
        assert value.local_x==pytest.approx(slot.start_x+effective_motion_age(age,True,.1)+nx)
        assert value.local_y==pytest.approx(slot.start_y+gravity_displacement(age,True,.02)+ny)
        assert value.lifetime_scale==evaluate_lifetime_scalar(s.scale_over_lifetime,t)
        assert value.lifetime_tint_g==pytest.approx(1+(40/255-1)*t)
        assert value.opacity==pytest.approx(.8+(.1-.8)*t)
        assert value.source_frame==particle_clip_frame_index(project.animation_clips[0],slot,age,project.fps)
        assert value.particle_id==0 and value.copy_key==(value.cycle_index,0)
    shifted=[];render_particle_frame(project,emitter,6,diagnostic_collector=shifted)
    left=sorted(diagnostics,key=lambda x:x.copy_key);right=sorted(shifted,key=lambda x:x.copy_key)
    assert [(x.age,x.local_x,x.local_y,x.source_frame) for x in left]==[(x.age,x.local_x,x.local_y,x.source_frame) for x in right]
    assert [x.cycle_index+1 for x in left]==[x.cycle_index for x in right]


@pytest.mark.parametrize("field,value",[("emission_cycle_mode","nope"),("emission_cycle_mode",[]),
    ("emission_period_frames",0),("emission_period_frames",513),("emission_period_frames",1.0),
    ("emission_period_frames",True),("emission_period_frames","6"),("emission_period_frames",float("inf"))])
def test_invalid_cycle_payload(field,value):
    data=setup()[1].settings.to_dict();data[field]=value
    with pytest.raises(ValueError):ParticleEmitterSettings.from_dict(data)


@pytest.mark.parametrize("count,lifetime,period,valid",[(4096,1,1,True),(2048,2,1,True),
    (2049,2,1,False),(1,4096,1,True),(1,4097,1,False),(0,4097,1,True)])
def test_active_copy_limit_exact_bound(count,lifetime,period,valid):
    s=setup(particle_count_min=count,particle_count_max=count,lifetime_min=lifetime,
        lifetime_max=lifetime,emission_period_frames=period)[1].settings
    assert s.cyclic_active_copy_bound()==count*((lifetime+period-1)//period)
    if valid:
        s.validate();slots=build_particle_instances(s,4)
        assert len(list(iter_particle_cycle_copies(s,slots,0)))==count*((lifetime-1)//period+1)
    else:
        with pytest.raises(ValueError,match="4096 active"):s.validate()


@pytest.mark.parametrize("kwargs",[dict(start_delay_max=6),dict(emission_mode="over_time",emission_duration=7),
    dict(emission_mode="over_time",emission_duration=5,start_delay_max=2)])
def test_birth_offset_rejection_without_wrap(kwargs):
    s=setup(**kwargs)[1].settings
    with pytest.raises(ValueError,match="birth offset"):s.validate()
    replace(s,emission_period_frames=12).validate()


@pytest.mark.parametrize("parented,advanced",[(False,False),(False,True),(True,True)])
def test_current_full_generated_png_parity_transforms(tmp_path,parented,advanced):
    project,emitter=setup()
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer)
    layer.advanced_transform_enabled=advanced
    layer.layer_space_transform.rotation_x=20;layer.layer_space_transform.rotation_y=-10
    layer.layer_space_transform.rotation_z=720;layer.layer_space_transform.perspective_strength=.2
    layer.surface_transform.rotation_z=12;layer.surface_transform.scale_x=.8
    if parented:
        from copy import deepcopy
        parent=deepcopy(layer);parent.id="parent";parent.visible=False;parent.generated_layer_id=None
        parent.layer_space_transform.position_x=2
        project.effect_resource_layers.append(parent);layer.parent_id=parent.id
        layer.parent_offset=(1,0,3,0,1,-2,0,0,1)
    project.repair_effect_hierarchy()
    reference=render_effect_resource_layer(project,layer)
    for frame in (23,0,5,12):
        assert np.array_equal(reference[frame],render_effect_resource_layer_current_frame(project,layer,frame))
    generated=apply_effect_resource_layer(project,layer)
    paths=export_png_frames(project,tmp_path)
    for i,path in enumerate(paths):
        from app.services.effect_playback_service import render_exact_playback_frame
        assert np.array_equal(reference[i],project.frames[i].layer_pixels[generated.id])
        assert np.array_equal(render_exact_playback_frame(project,i)[0],project.compose_frame(i))
        assert np.array_equal(project.compose_frame(i),np.asarray(Image.open(path)))
        assert reference[i].shape==(48,48,4)
    assert np.array_equal(render_particle_frame(project,emitter,24),render_particle_frame(project,emitter,0))
    assert not np.array_equal(render_particle_frame(project,emitter,23),render_particle_frame(project,emitter,0))


def test_cache_mode_period_and_nonperiodic_global_tracks():
    from app.models.resource_composition import AnimationTrack,Keyframe
    project,emitter=setup(emission_cycle_mode="one_shot")
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer)
    first=render_effect_resource_layer(project,layer)[0].copy();rev=playback_relevant_revision(project)
    layer.particle_settings.emission_cycle_mode="cyclic_steady"
    second=render_effect_resource_layer(project,layer)[0].copy()
    assert not np.array_equal(first,second) and rev!=playback_relevant_revision(project)
    layer.particle_settings.emission_period_frames=12
    third=render_effect_resource_layer(project,layer)[0]
    assert not np.array_equal(second,third)
    layer.particle_settings.emission_cycle_mode="one_shot"
    assert np.array_equal(first,render_effect_resource_layer(project,layer)[0])
    layer.particle_settings.emission_cycle_mode="cyclic_steady"
    layer.layer_space_transform.tracks["position_x"]=AnimationTrack("position_x",0,[Keyframe(0,0),Keyframe(23,10)])
    assert not np.array_equal(render_effect_resource_layer_current_frame(project,layer,0),render_effect_resource_layer_current_frame(project,layer,12))


def test_cyclic_keep_world_and_parent_offset_preserved():
    from copy import deepcopy
    from app.services.layer_parenting_service import set_parent_keep_world,effect_local_affine
    project,emitter=setup();child=EffectResourceLayer.from_particle_emitter(emitter)
    parent=deepcopy(child);parent.id="parent";parent.layer_space_transform.position_x=5
    project.effect_resource_layers.extend([child,parent]);project.repair_effect_hierarchy()
    before=render_effect_resource_layer_current_frame(project,child,0)
    assert set_parent_keep_world(project.effect_resource_layers,child.id,parent.id,0,lambda layer,frame:effect_local_affine(layer,frame,project))
    offset=child.parent_offset
    assert np.array_equal(before,render_effect_resource_layer_current_frame(project,child,0))
    assert np.array_equal(before,render_effect_resource_layer_current_frame(project,child,6))
    child.particle_settings.emission_period_frames=12
    render_effect_resource_layer_current_frame(project,child,0)
    assert child.parent_offset==offset


# Pixel hashes captured by the actual v0.0.21 baseline before production edits.
@pytest.mark.parametrize("name,expected",[
    ("Hit Spark","fa33ae0a311f953a33bbb770c7f0af20ebfd98b96b9710cb872ec8068516ecb8"),
    ("Explosion","297d65d2293682721c4c0f02bfe2ee88d571fb7143f602caea500322bbbb91ac"),
    ("Smoke Puff","b683d6fcf09cb83bc688fa122a07e822b146290a418a0a314d7e1fa06c9589c6"),
    ("Fire Ember","592a50192dc6ae6b1b1ec6d046a216b1da6c85115155094ef4caed199105fef3"),
    ("Magic Wisp","6aee98c1133f07202ed2acb8e381499a68bb85f30002b2561010da1b54724dcb"),
    ("Projectile","7e6fdac8d0107df35bad72d11b806a03c6310a5bb6a50dce9079deb46a8b9458"),
    ("Sword Slash","691bb7cf0dffdddd0e2a2ffff500257d3994145524ff41b4fa7491d88d63afb2"),
    ("Area Dust","5a1cea75983ac7ec2295972d62bb8bbc11e29cdbe9c90289b62bb710981b3ea3"),
    ("Ring Burst","5415a4c49f57f8f6082b4c91fa4080f94dd0bdebca8d4aa13c7608b6fc3499df"),
    ("Rain Snow","4d6ee1993035405e511466a853e3dde1aefa97a4976d80e2eb3f16a69c78c14a")])
def test_one_shot_v21_pixel_golden(name,expected):
    from tools.recheck_effect_capabilities import fixture,materialize
    project=fixture(name)
    assert all(layer.particle_settings.emission_cycle_mode=="one_shot" for layer in project.effect_resource_layers)
    assert hashlib.sha256(b"".join(frame.tobytes() for frame in materialize(project))).hexdigest()==expected
