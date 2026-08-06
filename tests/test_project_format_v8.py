import json

import numpy as np
import pytest

from app.frame_payload_codec import DEFAULT_FRAME_PAYLOAD_CODEC
from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings, ParticleMotionSettings
from app.models.project import FORMAT_VERSION, Project, ProjectError
from app.models.resource_composition import ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.project_io import save_project


def project_with_particle():
    project=Project.create_default();pixels=np.zeros((2,2,4),dtype=np.uint8);asset=SourceAsset("s",pixels);project.source_assets.append(asset)
    composition=ResourceComposition("c",layers=[]);project.resource_compositions.append(composition)
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",motion=ParticleMotionSettings(mode="helix",radius_start=12,radius_end=3,helix_axis="y",axis_end=40,perspective_strength=.4))
    layer=EffectResourceLayer("p",composition.id,placement_mode=PLACEMENT_PARTICLE,particle_settings=settings);project.effect_resource_layers.append(layer);return project,layer


def test_v8_motion_round_trip_and_tracks():
    project,layer=project_with_particle();layer.particle_settings.motion.set_keyframe("radius_end",4,18,"Ease Out")
    data=project.to_dict();loaded=Project.from_dict(data);motion=loaded.effect_resource_layers[0].particle_settings.motion
    assert data["format_version"]==FORMAT_VERSION==8 and motion.mode=="helix" and motion.helix_axis=="y" and motion.value("radius_end",4)==18


def test_v7_missing_motion_migrates_to_linear():
    project,layer=project_with_particle();data=project.to_dict();data["format_version"]=7;data["effect_resource_layers"][0]["particle_settings"].pop("motion")
    loaded=Project.from_dict(data);assert loaded.effect_resource_layers[0].particle_settings.motion==ParticleMotionSettings()


@pytest.mark.parametrize("version",range(1,8))
def test_v1_through_v7_migrate_existing_particles_to_linear(version):
    project,layer=project_with_particle();data=project.to_dict();data["format_version"]=version
    if version>=6:
        data["effect_resource_layers"][0]["particle_settings"].pop("motion")
    elif version>=3:
        emitter=layer.as_particle_emitter().to_dict();emitter["settings"].pop("motion")
        if version<5:
            pixels=np.zeros((2,2,4),dtype=np.uint8);clip=AnimationClipAsset("legacy",[pixels])
            data["animation_clips"]=[clip.to_dict()]
            emitter["settings"]["clip_asset_id"]=clip.id
            emitter["settings"]["resource_type"]="animation_clip"
        data["particle_emitters"]=[emitter];data["effect_resource_layers"]=[]
    else:
        data["effect_resource_layers"]=[]
    loaded=Project.from_dict(data)
    assert loaded.format_version==8
    assert all(item.particle_settings.motion.mode=="linear" for item in loaded.effect_resource_layers)


@pytest.mark.parametrize("value",[float("nan"),float("inf"),-float("inf")])
def test_nonfinite_motion_values_are_rejected(value):
    with pytest.raises(ValueError):ParticleMotionSettings(center_x=value).validate()


def test_motion_metadata_save_does_not_reencode_pixels(tmp_path):
    project,layer=project_with_particle();codec=DEFAULT_FRAME_PAYLOAD_CODEC;codec.clear();save_project(project,tmp_path/"first");codec.reset_stats();layer.particle_settings.motion.radius_start=77;save_project(project,tmp_path/"second")
    assert codec.stats.encode_calls==0


def test_v8_json_has_explicit_nested_motion_structure(tmp_path):
    project,_=project_with_particle();data=json.loads(save_project(project,tmp_path/"motion").read_text(encoding="utf-8"));motion=data["effect_resource_layers"][0]["particle_settings"]["motion"]
    assert motion["mode"]=="helix" and motion["center"]==[0,0,0] and motion["easing"]["axis"]=="Linear"
