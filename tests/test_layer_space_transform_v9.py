from copy import deepcopy

import numpy as np
import pytest

from app.models.effect_resource_layer import EffectLayerTransform3D,EffectResourceLayer,PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings
from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame
from app.services.layer_space_transform_service import project_local_point,projected_local_axes
from app.services.particle_render_service import ParticleFrameDiagnostic,render_particle_frame
from app.services.particle_preview_service import ParticlePreviewSnapshot,render_particle_snapshot


def _particle_project():
    project=Project.create_default(width=32,height=32,frame_count=4)
    pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[:]=[255,255,255,255]
    asset=SourceAsset("dot",pixels);project.source_assets.append(asset)
    composition=ResourceComposition("particle",width=32,height=32,frame_count=1,layers=[CompositionLayer("dot","source_asset",asset.id,0,0)])
    project.resource_compositions.append(composition)
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",particle_count_min=1,particle_count_max=1,lifetime_min=4,lifetime_max=4,origin_x=8,origin_y=10,speed_min=0,speed_max=0,output_frame_count=4)
    layer=EffectResourceLayer("particles",composition.id,placement_mode=PLACEMENT_PARTICLE,particle_settings=settings)
    project.effect_resource_layers.append(layer)
    return project,layer


def test_v8_layer_transform_migrates_to_surface_with_identity_layer_space():
    project,layer=_particle_project();old=EffectLayerTransform3D(position_x=3,rotation_y=22,perspective_strength=.4)
    data=project.to_dict();data["format_version"]=8;item=data["effect_resource_layers"][0]
    item["layer_transform"]=old.to_dict();item.pop("layer_space_transform");item.pop("surface_transform")
    loaded=Project.from_dict(data);migrated=loaded.effect_resource_layers[0]
    assert FORMAT_VERSION==19 and migrated.layer_space_transform.is_identity()
    assert migrated.surface_transform.to_dict()==old.to_dict()


def test_v9_round_trip_uses_two_explicit_transform_fields():
    project,layer=_particle_project();layer.layer_space_transform.rotation_x=18;layer.surface_transform.position_y=5
    data=project.to_dict();item=data["effect_resource_layers"][0]
    assert data["format_version"]==FORMAT_VERSION and "layer_transform" not in item
    assert set(("layer_space_transform","surface_transform"))<=set(item)
    loaded=Project.from_dict(data).effect_resource_layers[0]
    assert loaded.layer_space_transform.rotation_x==18 and loaded.surface_transform.position_y==5


def test_particle_spawn_values_stay_local_while_projected_marker_changes():
    project,layer=_particle_project();before=[];after=[]
    render_particle_frame(project,layer.as_particle_emitter(),0,diagnostic_collector=before,layer_space_transform=layer.layer_space_transform)
    layer.layer_space_transform.position_x=7;layer.layer_space_transform.rotation_y=25;layer.layer_space_transform.revision+=1
    render_particle_frame(project,layer.as_particle_emitter(),0,diagnostic_collector=after,layer_space_transform=layer.layer_space_transform)
    assert len(before)==len(after)==1
    assert (before[0].local_x,before[0].local_y,before[0].local_z)==(after[0].local_x,after[0].local_y,after[0].local_z)
    assert (before[0].x,before[0].y)!=(after[0].x,after[0].y)


def test_shared_projected_axes_match_point_projection():
    transform=EffectLayerTransform3D(position_x=3,position_z=8,rotation_x=25,rotation_y=-17,perspective_strength=.5)
    axes,valid=projected_local_axes(transform,64,48,frame=0,length=12)
    pivot=np.array((32.0,24.0,0.0));expected=[]
    for point in (pivot,pivot+(12,0,0),pivot+(0,12,0),pivot+(0,0,12)):
        value=project_local_point(*point,transform,64,48);expected.append((value.x,value.y))
    assert valid.all() and np.allclose(axes,np.asarray(expected))


def test_v8_surface_migration_preserves_exact_rgba():
    project,layer=_particle_project();legacy=EffectLayerTransform3D(position_x=2,rotation_z=15,opacity=.75)
    # v8 renderer semantics: local particle RGBA followed by the legacy plane transform.
    from app.services.effect_layer_transform_3d_render_service import transform_rgba_frame
    local=render_particle_frame(project,layer.as_particle_emitter(),0)
    expected=transform_rgba_frame(local,legacy,0)
    data=deepcopy(project.to_dict());data["format_version"]=8;item=data["effect_resource_layers"][0]
    item["layer_transform"]=legacy.to_dict();item.pop("layer_space_transform");item.pop("surface_transform")
    migrated=Project.from_dict(data);actual=render_effect_resource_layer_current_frame(migrated,migrated.effect_resource_layers[0],0)
    assert np.array_equal(actual,expected)


def test_noncanonical_transform_property_is_rejected():
    with pytest.raises(ValueError):EffectLayerTransform3D().set_property("rotate_x",10)


def test_particle_preview_snapshot_includes_both_v9_transform_stages():
    project,layer=_particle_project();layer.layer_space_transform.position_x=4;layer.surface_transform.opacity=.5
    snapshot=ParticlePreviewSnapshot.from_project(project,layer.id,1,layer.particle_settings)
    preview=render_particle_snapshot(snapshot)
    assert np.array_equal(preview[0],render_effect_resource_layer_current_frame(project,layer,0))
