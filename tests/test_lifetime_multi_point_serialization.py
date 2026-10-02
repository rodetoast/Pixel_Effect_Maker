from copy import deepcopy
import json
import math

import numpy as np
import pytest
from app.models.particle_emitter import LifetimeScalarPoint as S, LifetimeColorPoint as C, LifetimeScalarModulation, LifetimeColorModulation, ParticleEmitterSettings
from app.models.project import Project, FORMAT_VERSION
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.resource_composition import EASINGS
from app.services.project_io import load_project, save_project
from app.services.particle_render_service import render_particle_frame
from tests.test_particle_cyclic_emission import setup
from tests.test_lifetime_multi_point import curves


@pytest.mark.parametrize("points",[
    (), (S(0,1),), tuple(S(i/8,1) for i in range(9)),
    (S(.1,1),S(1,1)), (S(0,1),S(.9,1)),
    (S(0,1),S(.5,1),S(.5,2),S(1,1)),
    (S(0,1),S(.7,1),S(.3,1),S(1,1)),
    (S(0,1),S(math.nan,1),S(1,1)), (S(0,1),S(math.inf,1),S(1,1)),
    (S(0,1),S(1,math.nan)), (S(0,1),S(1,math.inf)),
    (S(0,1),S(1,-1)),(S(0,1),S(1,17)),
    (S(0,1,"Cubic"),S(1,1)),(S(0,True),S(1,1)),
    ({"time":0,"value":1}, S(1,1)),
])
def test_scalar_invalid_points_rejected_not_sorted(points):
    channel=LifetimeScalarModulation(True,points=points)
    with pytest.raises(ValueError):channel.validate()
    assert channel.points==points


@pytest.mark.parametrize("rgb",[(1,2), (1,2,3,4),(-1,2,3),(256,2,3),(True,2,3),(1.0,2,3)])
def test_rgb_invalid_alpha_and_channels_rejected(rgb):
    with pytest.raises(ValueError):LifetimeColorModulation(True,points=(C(0,rgb),C(1,(255,255,255)))).validate()


@pytest.mark.parametrize("easing",EASINGS)
def test_format19_migrates_all_channels_exact_and_does_not_rewrite(tmp_path,easing):
    project,emitter=setup(easing=easing,
        scale_over_lifetime=LifetimeScalarModulation(True,.2,1.4,easing),
        color_over_lifetime=LifetimeColorModulation(True,(241,162,3),(153,34,204),easing))
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    payload=project.to_dict();payload["format_version"]=19
    data=payload["effect_resource_layers"][0]["particle_settings"]
    data["scale_over_lifetime"]={"enabled":True,"start":.2,"end":1.4,"easing":easing}
    data["color_over_lifetime"]={"enabled":True,"start_rgb":[241,162,3],"end_rgb":[153,34,204],"easing":easing}
    data.pop("opacity_over_lifetime");data.update(opacity_start=.8,opacity_end=.1,easing=easing)
    path=tmp_path/"legacy.pemproj";path.write_text(json.dumps(payload),encoding="utf-8");raw=path.read_bytes()
    loaded=load_project(path);assert path.read_bytes()==raw and loaded.format_version==21
    actual=loaded.effect_resource_layers[0].particle_settings
    assert actual==emitter.settings
    for t in (0,1,5,12,23):assert np.array_equal(render_particle_frame(project,emitter,t),render_particle_frame(loaded,loaded.effect_resource_layers[0].as_particle_emitter(),t))
    assert len(actual.scale_over_lifetime.points)==len(actual.opacity_over_lifetime.points)==len(actual.color_over_lifetime.points)==2


def test_format20_roundtrip_canonical_only_and_legacy_accessors_share_points(tmp_path):
    project,emitter=setup();curves(emitter.settings)
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    path=save_project(project,tmp_path/"points");loaded=load_project(path)
    assert FORMAT_VERSION==21 and loaded.effect_resource_layers[0].particle_settings==emitter.settings
    serialized=emitter.settings.to_dict()
    assert not set(serialized)&{"opacity_start","opacity_end","easing"}
    for name in ("scale_over_lifetime","opacity_over_lifetime","color_over_lifetime"):
        assert set(serialized[name])=={"enabled","points"}
    points=emitter.settings.opacity_over_lifetime.points
    emitter.settings.opacity_start=.23
    assert emitter.settings.opacity_over_lifetime.points[0].value==.23 and emitter.settings.opacity_over_lifetime.points[1:]==points[1:]
    assert "opacity_start" not in emitter.settings.__dict__


@pytest.mark.parametrize("change",[
    lambda d:d["opacity_over_lifetime"]["points"][1].update(value=1.01),
    lambda d:d["opacity_over_lifetime"].update(enabled=False),
    lambda d:d["scale_over_lifetime"].update(start=1),
    lambda d:d["color_over_lifetime"]["points"][0].update(alpha=.5),
    lambda d:d.update(easing="Linear"),
])
def test_invalid_payload_rejected(change):
    _,emitter=setup();curves(emitter.settings);payload=emitter.settings.to_dict();change(payload)
    with pytest.raises(ValueError):ParticleEmitterSettings.from_dict(payload)


def test_format19_missing_channels_migrate_defaults():
    channel=ParticleEmitterSettings.from_dict({"clip_asset_id":"resource"})
    assert channel.scale_over_lifetime==LifetimeScalarModulation()
    assert channel.color_over_lifetime==LifetimeColorModulation()
    assert channel.opacity_over_lifetime==LifetimeScalarModulation(True,1,0,"Linear")


@pytest.mark.parametrize("channel",["scale_over_lifetime","color_over_lifetime","opacity_over_lifetime"])
def test_format20_requires_canonical_curve_payload(channel):
    project,emitter=setup();project.effect_resource_layers.append(EffectResourceLayer.from_particle_emitter(emitter));project.repair_effect_hierarchy()
    payload=project.to_dict();payload["effect_resource_layers"][0]["particle_settings"].pop(channel)
    with pytest.raises(ValueError,match="canonical lifetime points"):Project.from_dict(payload)
