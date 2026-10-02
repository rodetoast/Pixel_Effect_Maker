from copy import deepcopy
import json
import math
import pytest
import numpy as np
from app.models.particle_emitter import ParticleTrailSettings as Trail, ParticleEmitterSettings
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import Project, FORMAT_VERSION
from app.services.project_io import save_project,load_project
from app.services.particle_render_service import render_particle_frame
from tests.test_particle_trail import scene,diagnostics


@pytest.mark.parametrize("field,bad",[
    ("enabled",1),("enabled","false"),
    ("duration_frames",1),("duration_frames",241),("duration_frames",12.0),("duration_frames",True),
    ("sample_interval_frames",0),("sample_interval_frames",12),("sample_interval_frames",13),
    ("sample_interval_frames",2.0),("sample_interval_frames",True),
    ("opacity",-1),("opacity",1.01),("opacity",math.nan),("opacity",math.inf),("opacity",True),("opacity",".5"),
])
def test_invalid_payload_deterministic_reject(field,bad):
    data=Trail().to_dict();data[field]=bad
    with pytest.raises(ValueError):Trail.from_dict(data)


@pytest.mark.parametrize("data",[[],False,"trail",{"unknown":1}])
def test_bad_trail_payload_structure(data):
    with pytest.raises(ValueError):Trail.from_dict(data)


def test_format20_missing_trail_defaults_disabled_no_rewrite_exact(tmp_path):
    project,emitter=scene(trail=Trail(False))
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    payload=project.to_dict();payload["format_version"]=20
    payload["effect_resource_layers"][0]["particle_settings"].pop("trail")
    path=tmp_path/"legacy.peffect.json";path.write_text(json.dumps(payload),encoding="utf-8");before=path.read_bytes()
    loaded=load_project(path)
    assert path.read_bytes()==before and loaded.format_version==FORMAT_VERSION==22
    actual=loaded.effect_resource_layers[0].as_particle_emitter()
    assert actual.settings.trail==Trail()
    for t in (0,1,5,6,14):assert np.array_equal(render_particle_frame(project,emitter,t),render_particle_frame(loaded,actual,t))


@pytest.mark.parametrize("enabled",[False,True])
def test_format21_sentinel_roundtrip_exact(enabled,tmp_path):
    project,emitter=scene(trail=Trail(enabled,17,3,.625));project.effect_resource_layers.append(EffectResourceLayer.from_particle_emitter(emitter));project.repair_effect_hierarchy()
    path=save_project(project,tmp_path/"trail");loaded=load_project(path)
    settings=loaded.effect_resource_layers[0].particle_settings
    assert settings==emitter.settings and settings.trail.to_dict()==dict(enabled=enabled,duration_frames=17,sample_interval_frames=3,opacity=.625)
    assert loaded.to_dict()["format_version"]==22
    for t in (0,5,6,19,20):assert np.array_equal(render_particle_frame(project,emitter,t),render_particle_frame(loaded,loaded.effect_resource_layers[0].as_particle_emitter(),t))


def test_visual_copy_bound_includes_tail_exact_and_plus_one_rejection():
    _,emitter=scene(emission_cycle_mode="cyclic_steady",emission_period_frames=1,
        particle_count_min=256,particle_count_max=256,lifetime_min=15,lifetime_max=15,trail=Trail(True,2,1,.75))
    settings=emitter.settings
    assert settings.cyclic_active_copy_bound()==4096 and settings.trail_stamp_bound()==4096
    settings.validate()
    settings.particle_count_min=settings.particle_count_max=241;settings.lifetime_min=settings.lifetime_max=16
    assert settings.cyclic_active_copy_bound()==4097
    with pytest.raises(ValueError,match="4096"):settings.validate()
    settings.trail.enabled=False;settings.validate()
    assert settings.cyclic_active_copy_bound()==241*16


def test_stamp_budget_exact_8192_and_plus_one_rejected():
    _,emitter=scene(particle_count_min=4096,particle_count_max=4096,trail=Trail(True,3,1,.75))
    settings=emitter.settings;assert settings.trail_stamp_bound()==8192;settings.validate()
    settings.particle_count_min=settings.particle_count_max=2731;settings.trail.duration_frames=4
    assert settings.trail_stamp_bound()==8193
    with pytest.raises(ValueError,match="8192"):settings.validate()
    settings.trail.enabled=False;settings.validate();assert settings.trail_stamp_bound()==0


def test_no_silent_drop_and_visual_lifetime_last_age():
    project,emitter=scene(particle_count_min=2,particle_count_max=2,lifetime_min=32,lifetime_max=32,trail=Trail(True,5,1,.75))
    pixels,values=diagnostics(project,emitter,6)
    assert len(values)==10 and sum(d.trail_delta>0 for d in values)==emitter.settings.trail_stamp_bound()==8
    assert sum(d.trail_delta==0 for d in values)==2
    _,last=diagnostics(project,emitter,35)
    assert last and all(d.trail_delta==4 and d.age==31 for d in last)
    pixels,expired=diagnostics(project,emitter,36);assert expired==[] and not np.any(pixels)
