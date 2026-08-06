import numpy as np
import pytest

from app.models.animation_clip import AnimationClipAsset
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings, ParticleInstance, ParticleMotionSettings
from app.models.project import Project
from app.services import particle_render_service as renderer


def particle(**changes):
    values=dict(birth_frame=0,lifetime=10,start_x=10,start_y=20,velocity_x=0,velocity_y=0,scale=1,rotation=0,angular_velocity=0,clip_start_frame=0,clip_playback_speed=1,random_seed=1,particle_id=0,motion_phase_degrees=0);values.update(changes);return ParticleInstance(**values)


@pytest.mark.parametrize(("axis","expected"),[("z",(10,30,5)),("x",(15,20,10)),("y",(10,25,10))])
def test_helix_axis_positions(axis,expected):
    motion=ParticleMotionSettings(mode="helix",radius_start=10,radius_end=10,start_angle_degrees=0,turns=.5,direction="clockwise",helix_axis=axis,axis_start=0,axis_end=10)
    value=renderer.evaluate_particle_motion(ParticleEmitterSettings("c",motion=motion),particle(),.5)
    assert (value.x,value.y,value.z)==pytest.approx(expected)


def test_axis_easing_and_center_z():
    motion=ParticleMotionSettings(mode="helix",radius_start=0,radius_end=0,helix_axis="z",axis_start=0,axis_end=100,axis_easing="Ease In",center_z=7)
    value=renderer.evaluate_particle_motion(ParticleEmitterSettings("c",motion=motion),particle(),.5)
    assert value.z==32


def test_local_z_stable_sort_and_positive_z_composites_later(monkeypatch):
    project=Project.create_default(width=8,height=8);pixel=np.zeros((1,1,4),dtype=np.uint8);clip=AnimationClipAsset("c",[pixel]);project.animation_clips.append(clip)
    motion=ParticleMotionSettings(mode="helix",radius_start=0,radius_end=0,helix_axis="z",axis_start=0,axis_end=10)
    settings=ParticleEmitterSettings(clip.id,motion=motion,opacity_start=1,opacity_end=1);emitter=ParticleEmitter("p",settings)
    instances=(particle(start_x=4,start_y=4,lifetime=20,random_seed=1),particle(start_x=4,start_y=4,lifetime=10,random_seed=2))
    def sprite(_clip,item,_age,_fps):
        result=np.zeros((1,1,4),dtype=np.uint8);result[0,0]=[255,0,0,255] if item.random_seed==1 else [0,0,255,255];return result
    monkeypatch.setattr(renderer,"particle_clip_frame",sprite)
    output=renderer.render_particle_frame(project,emitter,1,clip=clip,instances=instances)
    assert tuple(output[4,4])==(0,0,255,255)


def test_equal_local_z_preserves_generation_order(monkeypatch):
    project=Project.create_default(width=8,height=8);pixel=np.zeros((1,1,4),dtype=np.uint8);clip=AnimationClipAsset("c",[pixel]);project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,motion=ParticleMotionSettings(mode="orbit",radius_start=0,radius_end=0),opacity_start=1,opacity_end=1);emitter=ParticleEmitter("p",settings)
    instances=(particle(start_x=4,start_y=4,random_seed=1),particle(start_x=4,start_y=4,random_seed=2))
    def sprite(_clip,item,_age,_fps):
        result=np.zeros((1,1,4),dtype=np.uint8);result[0,0]=[255,0,0,255] if item.random_seed==1 else [0,255,0,255];return result
    monkeypatch.setattr(renderer,"particle_clip_frame",sprite)
    output=renderer.render_particle_frame(project,emitter,0,clip=clip,instances=instances)
    assert tuple(output[4,4])==(0,255,0,255)


@pytest.mark.parametrize("axis",["x","y","z"])
def test_helix_guide_matches_renderer_for_all_axes(axis):
    motion=ParticleMotionSettings(mode="helix",radius_start=6,radius_end=12,turns=1.5,direction="counter_clockwise",helix_axis=axis,axis_start=-4,axis_end=9)
    settings=ParticleEmitterSettings("c",origin_x=10,origin_y=20,motion=motion)
    path=renderer.particle_motion_guide(settings,64,64,41)
    probe=particle(start_x=10,start_y=20)
    for index in (0,10,20,30,40):
        assert path[index]==renderer.evaluate_particle_motion(settings,probe,index/40)
