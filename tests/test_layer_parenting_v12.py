from copy import deepcopy

import numpy as np

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.layer_parenting_service import (
    effect_local_affine,
    resolve_world_affines,
    resource_local_affine,
    set_parent_keep_world,
)
from app.services.resource_composition_render_service import render_composition_frame


def _resource_scene():
    project=Project.create_default(width=16,height=16,frame_count=2)
    pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[:]=[220,80,30,255]
    asset=SourceAsset("sprite",pixels);project.source_assets=[asset]
    parent=CompositionLayer("Parent","source_asset",asset.id,0,1);child=CompositionLayer("Child","source_asset",asset.id,0,1)
    parent.add_property("position").default_value=[3,1];parent.add_property("rotation").default_value=25
    child.add_property("position").default_value=[-2,2]
    composition=ResourceComposition("Scene",16,16,12,2,layers=[parent,child]);project.resource_compositions=[composition]
    return project,composition,parent,child


def test_v12_roundtrip_and_v11_migration_default_to_no_parent():
    project,composition,parent,child=_resource_scene();child.parent_id=parent.id
    data=project.to_dict();assert FORMAT_VERSION==20 and data["format_version"]==20
    loaded=Project.from_dict(deepcopy(data));assert loaded.resource_compositions[0].layers[1].parent_id==parent.id
    old=deepcopy(data);old["format_version"]=11
    for layer in old["resource_compositions"][0]["layers"]:layer.pop("parent_id",None);layer.pop("parent_offset",None)
    assert all(item.parent_id is None for item in Project.from_dict(old).resource_compositions[0].layers)


def test_set_clear_and_reparent_preserve_current_world_without_rewriting_tracks():
    project,composition,parent,child=_resource_scene();other=deepcopy(parent);other.id="other";other.name="Other";other.tracks["position"].default_value=[-4,-3];composition.layers.append(other)
    local_before=deepcopy(child.tracks);world=lambda:resolve_world_affines(composition.layers,0,lambda item,frame:resource_local_affine(item,frame,composition))[child.id]
    expected=world().copy()
    assert set_parent_keep_world(composition.layers,child.id,parent.id,0,lambda item,frame:resource_local_affine(item,frame,composition));assert np.allclose(world(),expected)
    assert set_parent_keep_world(composition.layers,child.id,other.id,0,lambda item,frame:resource_local_affine(item,frame,composition));assert np.allclose(world(),expected)
    assert set_parent_keep_world(composition.layers,child.id,None,0,lambda item,frame:resource_local_affine(item,frame,composition));assert np.allclose(world(),expected)
    assert child.tracks==local_before


def test_parent_animation_propagates_and_cycles_are_repaired_deterministically():
    project,composition,parent,child=_resource_scene();track=parent.tracks["position"];track.set_keyframe(0,[0,0]);track.set_keyframe(1,[5,0]);child.parent_id=parent.id
    worlds=resolve_world_affines(composition.layers,0,lambda item,frame:resource_local_affine(item,frame,composition));worlds2=resolve_world_affines(composition.layers,1,lambda item,frame:resource_local_affine(item,frame,composition))
    assert np.isclose(worlds2[child.id][0,2]-worlds[child.id][0,2],5)
    parent.parent_id=child.id;composition.repair_hierarchy();assert not (parent.parent_id==child.id and child.parent_id==parent.id)


def test_effect_chain_memoization_and_none_parent_render_equivalence():
    project,composition,parent,child=_resource_scene();before=render_composition_frame(project,composition,0).copy()
    assert np.array_equal(before,render_composition_frame(project,composition,0))
    effects=[EffectResourceLayer(str(index),composition.id) for index in range(10)]
    for index,item in enumerate(effects):
        item.layer_space_transform.position_x=index
        if index:item.parent_id=effects[index-1].id
    calls={item.id:0 for item in effects}
    def local(item,frame):calls[item.id]+=1;return effect_local_affine(item,frame,project)
    result=resolve_world_affines(effects,0,local)
    assert len(result)==10 and all(value==1 for value in calls.values())
