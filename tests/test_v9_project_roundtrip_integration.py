"""v9 metadata save, migration, validation, and cache round-trip integration."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import numpy as np
import pytest

from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.project import FORMAT_VERSION,Project
from app.services import effect_resource_layer_render_service as resource_renderer
from app.services.effect_layer_transform_3d_render_service import transform_rgba_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer_current_frame
from app.services.particle_render_service import PARTICLE_RENDER_STATS,render_particle_frame
from app.services.project_io import ProjectIOError,SavePerformanceCollector,load_project,save_project
from tests.test_v9_integrated_workflow import production_project


def test_metadata_save_reload_preserves_particle_current_frame(tmp_path):
    project,_,_,_,effect=production_project(tmp_path,"orbit",animated=True)
    effect.particle_settings.motion.radius_end=2;effect.particle_settings.motion.revision+=1
    apply_effect_resource_layer(project,effect)
    effect.particle_settings.motion.radius_end=13;effect.particle_settings.motion.revision+=1
    full_before=PARTICLE_RENDER_STATS["full_sequence_renders"];current_before=PARTICLE_RENDER_STATS["current_frame_renders"]
    collector=SavePerformanceCollector();path=save_project(project,tmp_path/"metadata",collector)
    assert PARTICLE_RENDER_STATS["full_sequence_renders"]==full_before
    assert PARTICLE_RENDER_STATS["current_frame_renders"]==current_before
    assert collector.calls["project_to_dict"]==1 and collector.calls["atomic_replace"]==1
    loaded=load_project(path);loaded_effect=loaded.effect_resource_layers[0]
    stale=[loaded.compose_frame(frame) for frame in range(12)]
    direct={frame:render_effect_resource_layer_current_frame(loaded,loaded_effect,frame) for frame in (7,2,10,3,7,0,11)}
    assert any(not np.array_equal(stale[frame],direct[frame]) for frame in direct)
    assert np.array_equal(direct[7],render_effect_resource_layer_current_frame(loaded,loaded_effect,7))


def test_save_reload_preserves_resource_system_and_surface_transforms(tmp_path):
    project,_,composition,resource_layer,effect=production_project(tmp_path,"helix",animated=True)
    resource_layer.add_property("rotation_x").set_keyframe(0,15);resource_layer.tracks["rotation_x"].set_keyframe(11,55)
    resource_layer.add_property("rotation_y").set_keyframe(0,-25);resource_layer.add_property("perspective_strength").set_keyframe(0,.4);composition.touch()
    effect.layer_space_transform.set_keyframe("rotation_z",0,5);effect.layer_space_transform.set_keyframe("rotation_z",11,85)
    effect.layer_space_transform.position_z=9;effect.surface_transform.rotation_y=-12;effect.surface_transform.opacity=.7
    expected=[render_effect_resource_layer_current_frame(project,effect,frame) for frame in range(12)]
    loaded=load_project(save_project(project,tmp_path/"all-transforms"));actual_layer=loaded.effect_resource_layers[0]
    actual=[render_effect_resource_layer_current_frame(loaded,actual_layer,frame) for frame in reversed(range(12))]
    assert all(np.array_equal(expected[frame],actual[11-frame]) for frame in range(12))
    assert actual_layer.layer_space_transform.value("rotation_z",11)==85
    assert actual_layer.surface_transform.rotation_y==-12 and actual_layer.surface_transform.opacity==.7


def test_v8_to_v9_save_as_round_trip_preserves_original_hash_and_rgba(tmp_path):
    project,_,_,_,effect=production_project(tmp_path,"orbit")
    legacy=EffectLayerTransform3D(position_x=3,position_y=-2,rotation_z=17,opacity=.65,perspective_strength=.2)
    local=[render_particle_frame(project,effect.as_particle_emitter(),frame,layer_space_transform=EffectLayerTransform3D()) for frame in range(12)]
    expected=[transform_rgba_frame(frame,legacy,index) for index,frame in enumerate(local)]
    data=deepcopy(project.to_dict());data["format_version"]=8;item=data["effect_resource_layers"][0]
    item["layer_transform"]=legacy.to_dict();item.pop("layer_space_transform");item.pop("surface_transform")
    original=tmp_path/"legacy-v8.peffect.json";original.write_text(json.dumps(data,separators=(",",":")),encoding="utf-8")
    before=sha256(original.read_bytes()).hexdigest();migrated=load_project(original);layer=migrated.effect_resource_layers[0]
    assert FORMAT_VERSION==14 and migrated.format_version==14 and layer.layer_space_transform.is_identity()
    assert layer.surface_transform.to_dict()==legacy.to_dict()
    assert all(np.array_equal(expected[frame],render_effect_resource_layer_current_frame(migrated,layer,frame)) for frame in range(12))
    reloaded=load_project(save_project(migrated,tmp_path/"migrated-v9"));reloaded_layer=reloaded.effect_resource_layers[0]
    assert all(np.array_equal(expected[frame],render_effect_resource_layer_current_frame(reloaded,reloaded_layer,frame)) for frame in range(12))
    assert sha256(original.read_bytes()).hexdigest()==before


@pytest.mark.parametrize("payload",[
    "not json",
    "[]",
    '{"format_version":99}',
    '{"format_version":9,"name":"bad","width":NaN}',
])
def test_integrated_corrupt_and_future_projects_are_rejected(tmp_path,payload):
    path=tmp_path/"invalid.peffect.json";path.write_text(payload,encoding="utf-8")
    with pytest.raises(ProjectIOError):load_project(path)


def test_transform_cache_byte_accounting_survives_resource_revision(tmp_path):
    resource_renderer.invalidate_effect_resource_layer_base()
    project,_,composition,_,effect=production_project(tmp_path,"single")
    resource_renderer.render_effect_resource_layer(project,effect)
    assert resource_renderer._TRANSFORM_CACHE_BYTES==sum(frame.nbytes for frame in resource_renderer._TRANSFORM_CACHE.values())
    composition.touch()
    resource_renderer.render_effect_resource_layer(project,effect)
    assert resource_renderer._TRANSFORM_CACHE_BYTES==sum(frame.nbytes for frame in resource_renderer._TRANSFORM_CACHE.values())
    assert resource_renderer._TRANSFORM_CACHE_BYTES<=resource_renderer._MAX_TRANSFORM_CACHE_BYTES
