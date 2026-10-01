from __future__ import annotations

import numpy as np
import pytest

from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import LifetimeColorModulation, ParticleEmitter, ParticleEmitterSettings
from app.models.project import FORMAT_VERSION, Project
from app.services.effect_resource_layer_render_service import render_effect_resource_layer
from app.services.project_io import load_project, save_project


def _project(channel=None):
    project=Project.create_default(width=8,height=8,frame_count=5);clip=AnimationClipAsset("dot",[np.array([[[200,100,50,180]]],dtype=np.uint8)],pivot_x=0,pivot_y=0);project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=5,particle_count_min=1,particle_count_max=1,lifetime_min=5,lifetime_max=5,speed_min=0,speed_max=0,origin_x=2,origin_y=3,color_over_lifetime=channel or LifetimeColorModulation())
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("particle",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy();return project,layer


def test_format13_project_defaults_color_lifetime_to_disabled_identity_and_preserves_render():
    project,layer=_project();before=render_effect_resource_layer(project,layer);payload=project.to_dict();payload["format_version"]=13
    for item in payload["effect_resource_layers"]:item["particle_settings"].pop("color_over_lifetime",None)
    loaded=Project.from_dict(payload);restored=loaded.effect_resource_layers[0]
    assert restored.particle_settings.color_over_lifetime==LifetimeColorModulation()
    assert all(np.array_equal(a,b) for a,b in zip(before,render_effect_resource_layer(loaded,restored),strict=True))


@pytest.mark.parametrize("easing",["Linear","Ease In","Ease Out","Ease In/Out"])
def test_format14_color_lifetime_round_trip_is_exact(tmp_path,easing):
    expected=LifetimeColorModulation(True,(241,13,73),(17,199,226),easing);project,_layer=_project(expected);path=save_project(project,tmp_path/f"color-{easing}")
    loaded=load_project(path);actual=loaded.effect_resource_layers[0].particle_settings.color_over_lifetime
    assert FORMAT_VERSION==20 and loaded.format_version==20 and actual==expected
    data=actual.to_dict();assert data=={"enabled":True,"points":[{"time":0.0,"rgb":[241,13,73],"easing_to_next":easing},{"time":1.0,"rgb":[17,199,226],"easing_to_next":"Linear"}]} and "alpha" not in data


@pytest.mark.parametrize("data",[
    {"enabled":1},
    {"enabled":True,"start_rgb":[0,0,0,255]},
    {"enabled":True,"end_rgb":[0,-1,0]},
    {"enabled":True,"start_rgb":[0.5,0,0]},
])
def test_corrupt_color_lifetime_payload_is_rejected(data):
    with pytest.raises(ValueError):LifetimeColorModulation.from_dict(data)
