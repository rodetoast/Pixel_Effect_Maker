import math
from copy import deepcopy

import numpy as np
import pytest

from app.models.animation_clip import AnimationClipAsset
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings, ParticleInstance, ParticleMotionSettings
from app.models.project import Project
from app.services.particle_render_service import (
    PARTICLE_RENDER_STATS, build_particle_instances, evaluate_particle_motion,
    particle_motion_guide, particle_spawn_states, project_particle_billboard,
    render_particle_frame, render_particle_frames,
)


def instance(**changes):
    values=dict(birth_frame=0,lifetime=10,start_x=100,start_y=80,velocity_x=2,velocity_y=-1,scale=1,rotation=0,angular_velocity=0,clip_start_frame=0,clip_playback_speed=1,random_seed=1,particle_id=3,motion_phase_degrees=0)
    values.update(changes);return ParticleInstance(**values)


def settings(mode="orbit",**changes):
    motion=ParticleMotionSettings(mode=mode,radius_start=20,radius_end=20,turns=1)
    for name,value in changes.items():setattr(motion,name,value)
    return ParticleEmitterSettings("clip",motion=motion)


def assert_position(value,x,y,z=0):
    assert value.x==pytest.approx(x,abs=1e-7);assert value.y==pytest.approx(y,abs=1e-7);assert value.z==pytest.approx(z,abs=1e-7)


def test_particle_motion_defaults_to_linear():
    value=ParticleEmitterSettings("clip");assert value.motion==ParticleMotionSettings()
    assert_position(evaluate_particle_motion(value,instance(),.5),110,75)


def test_orbit_zero_and_quarter_turn_positions():
    value=settings(direction="clockwise")
    assert_position(evaluate_particle_motion(value,instance(),0),120,80)
    assert_position(evaluate_particle_motion(value,instance(),.25),100,100)


def test_orbit_counter_clockwise_is_screen_counter_clockwise():
    value=settings(direction="counter_clockwise")
    assert_position(evaluate_particle_motion(value,instance(),.25),100,60)


def test_orbit_radius_ellipse_center_and_plane_rotation():
    value=settings(center_x=5,center_y=-3,center_z=7,radius_start=10,radius_end=30,ellipse_scale_x=2,ellipse_scale_y=.5,orbit_plane_rotation_degrees=90,direction="clockwise",turns=0)
    assert_position(evaluate_particle_motion(value,instance(),.5),105,117,7)


def test_multiple_turns_are_not_shortest_path():
    value=settings(turns=3,direction="clockwise")
    assert_position(evaluate_particle_motion(value,instance(),1/6),80,80)


def test_easing_changes_radius_and_angle_independently():
    value=settings(radius_start=0,radius_end=100,turns=.25,direction="clockwise",radius_easing="Ease In",angle_easing="Ease Out")
    result=evaluate_particle_motion(value,instance(),.5)
    angle=math.radians(67.5);assert_position(result,100+math.cos(angle)*25,80+math.sin(angle)*25)


def test_phase_spread_is_deterministic_without_changing_linear_rng():
    base=ParticleEmitterSettings("clip",particle_count_min=8,particle_count_max=8,seed=123)
    linear=build_particle_instances(base,1)
    orbit=deepcopy(base);orbit.motion=ParticleMotionSettings(mode="orbit",phase_spread_degrees=360)
    first=build_particle_instances(orbit,1);second=build_particle_instances(deepcopy(orbit),1)
    assert first==second and len({round(item.motion_phase_degrees,6) for item in first})>1
    assert [(p.start_x,p.start_y,p.velocity_x,p.velocity_y,p.random_seed) for p in first]==[(p.start_x,p.start_y,p.velocity_x,p.velocity_y,p.random_seed) for p in linear]


def test_spawn_shape_position_is_each_particle_motion_center():
    value=settings(center_x=2,center_y=3)
    assert_position(evaluate_particle_motion(value,instance(start_x=11,start_y=13),0),33,16)


def test_motion_guide_uses_exact_evaluator():
    value=settings(direction="clockwise",turns=2)
    path=particle_motion_guide(value,256,256,33);probe=instance(start_x=value.origin_x,start_y=value.origin_y,particle_id=0)
    assert path[8]==evaluate_particle_motion(value,probe,.25)


def test_local_perspective_zero_and_positive_z_billboard_scale():
    point=evaluate_particle_motion(settings(center_z=50),instance(),0)
    assert project_particle_billboard(point,0,200,160)==(point.x,point.y,1,True)
    x,y,scale,valid=project_particle_billboard(point,.5,200,160)
    assert valid and scale>1 and x>point.x


def test_near_plane_and_nonfinite_projection_are_safe():
    from app.services.particle_render_service import ParticleMotionPosition
    assert not project_particle_billboard(ParticleMotionPosition(1,2,10_000),1,64,64)[3]
    assert not project_particle_billboard(ParticleMotionPosition(float("nan"),2,0),1,64,64)[3]


def test_spawn_state_cache_reuses_motion_only_changes():
    value=settings();PARTICLE_RENDER_STATS["spawn_cache_hits"]=PARTICLE_RENDER_STATS["spawn_cache_misses"]=0
    first=particle_spawn_states(value,1);value.motion.radius_end=99;second=particle_spawn_states(value,1)
    assert first is second and PARTICLE_RENDER_STATS["spawn_cache_misses"]==1 and PARTICLE_RENDER_STATS["spawn_cache_hits"]==1


def test_current_frame_render_does_not_materialize_sequence():
    project=Project.create_default(width=32,height=32);pixels=np.zeros((1,1,4),dtype=np.uint8);pixels[0,0]=255
    clip=AnimationClipAsset("c",[pixels]);project.animation_clips.append(clip);value=settings();value.clip_asset_id=clip.id
    emitter=ParticleEmitter("p",value);before=PARTICLE_RENDER_STATS["full_sequence_renders"]
    frame=render_particle_frame(project,emitter,0)
    assert frame.shape==(32,32,4) and PARTICLE_RENDER_STATS["full_sequence_renders"]==before


def test_same_seed_and_scrub_order_produce_same_frames():
    project=Project.create_default(width=64,height=64);pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[1,1]=[255,20,5,255]
    clip=AnimationClipAsset("c",[pixels]);project.animation_clips.append(clip);value=settings(phase_spread_degrees=360);value.clip_asset_id=clip.id;value.particle_count_min=value.particle_count_max=12
    emitter=ParticleEmitter("p",value);direct={i:render_particle_frame(project,emitter,i) for i in (5,1,7,0)};sequence=render_particle_frames(project,emitter)
    assert all(np.array_equal(direct[i],sequence[i]) for i in direct)
