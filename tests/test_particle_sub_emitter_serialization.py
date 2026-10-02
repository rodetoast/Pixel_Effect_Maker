from copy import deepcopy
import json
import pytest
import numpy as np
from app.models.particle_emitter import ParticleSubEmitterEventSettings as Event, ParticleTrailSettings as Trail
from app.models.project import FORMAT_VERSION,Project
from app.services.project_io import save_project,load_project
from app.services.particle_sub_emitter_service import contribution_bounds,validate_project_sub_emitters
from tests.test_particle_sub_emitter import setup,collect,children


@pytest.mark.parametrize("payload",[[],False,"event",{"unknown":1},{"enabled":1},{"enabled":"true"},{"target_layer_id":1},{"target_layer_id":""},{"target_layer_id":" "},{"enabled":True}])
def test_invalid_model_payload_rejected(payload):
    with pytest.raises(ValueError):Event.from_dict(payload)


def test_defaults_roundtrip_same_target_and_format21_missing_no_rewrite(tmp_path):
    assert Event()==Event(False,None)
    project,parent,target=setup("both")
    path=save_project(project,tmp_path/"new");loaded=load_project(path)
    assert FORMAT_VERSION==22 and loaded.effect_resource_layers[0].particle_settings==parent.particle_settings
    parent.particle_settings.birth_sub_emitter=Event();parent.particle_settings.death_sub_emitter=Event()
    expected=collect(project,parent,6)[0];data=project.to_dict();data["format_version"]=21
    for item in data["effect_resource_layers"]:
        for key in ("birth_sub_emitter","death_sub_emitter"):item["particle_settings"].pop(key)
    legacy=tmp_path/"legacy.peffect.json";legacy.write_text(json.dumps(data),encoding="utf-8");before=legacy.read_bytes()
    migrated=load_project(legacy)
    assert legacy.read_bytes()==before and migrated.format_version==22
    assert migrated.effect_resource_layers[0].particle_settings.birth_sub_emitter==Event()
    assert np.array_equal(expected,collect(migrated,migrated.effect_resource_layers[0],6)[0])


@pytest.mark.parametrize("bad",["parent","missing","target"])
def test_self_missing_non_particle_target_rejected(bad):
    project,parent,target=setup()
    if bad=="target":target.placement_mode="single"
    parent.particle_settings.death_sub_emitter.target_layer_id=bad
    with pytest.raises(ValueError,match="another existing Particle"):validate_project_sub_emitters(project)


def test_missing_load_safe_clear_not_arbitrary_retarget(tmp_path):
    project,parent,target=setup()
    data=project.to_dict();data["effect_resource_layers"][0]["particle_settings"]["death_sub_emitter"]["target_layer_id"]="missing"
    path=tmp_path/"missing.peffect.json";path.write_text(json.dumps(data),encoding="utf-8");before=path.read_bytes()
    loaded=load_project(path)
    assert path.read_bytes()==before and loaded.effect_resource_layers[0].particle_settings.death_sub_emitter==Event()
    collect(loaded,loaded.effect_resource_layers[0],6)


@pytest.mark.parametrize("cyclic",[False,True])
def test_combined_visual_exact_boundary_and_one_over(cyclic):
    project,parent,target=setup("birth",cyclic,lifetime_min=1,lifetime_max=1,particle_count_min=4095,particle_count_max=4095)
    parent.particle_settings.trail=Trail(False);parent.particle_settings.lifetime_min=parent.particle_settings.lifetime_max=1
    parent.particle_settings.emission_period_frames=1
    by_id={item.id:item for item in project.effect_resource_layers}
    assert contribution_bounds(parent.particle_settings,by_id,parent.id)[0]==4096
    target.particle_settings.particle_count_min=target.particle_settings.particle_count_max=4096
    with pytest.raises(ValueError,match="4096"):contribution_bounds(parent.particle_settings,by_id,parent.id)


def test_combined_trail_exact_boundary_and_one_over():
    project,parent,target=setup("birth",child_trail=True,particle_count_min=2730,particle_count_max=2730)
    parent.particle_settings.trail=Trail(True,3,1,.75);target.particle_settings.trail=Trail(True,4,1,.75)
    by_id={item.id:item for item in project.effect_resource_layers}
    visual,stamps,_=contribution_bounds(parent.particle_settings,by_id,parent.id)
    assert visual==2731 and stamps==8192
    parent.particle_settings.trail.duration_frames=4
    with pytest.raises(ValueError,match="8192"):contribution_bounds(parent.particle_settings,by_id,parent.id)


def test_over_time_horizon_and_no_silent_drop():
    project,parent,target=setup("birth",True,True,particle_count_min=3,particle_count_max=3,
        emission_mode="over_time",emission_duration=3,start_delay_min=2,start_delay_max=2)
    parent.particle_settings.particle_count_min=parent.particle_settings.particle_count_max=2
    _,_,detail=contribution_bounds(parent.particle_settings,{i.id:i for i in project.effect_resource_layers},parent.id)
    assert detail==( ("birth",14,18,54), )
    _,values=collect(project,parent,5)
    assert len({v.generation_order for v in children(values)})==12
