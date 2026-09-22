from copy import deepcopy

import numpy as np

from app.models.layer_group import LayerGroup, group_node, layer_node
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.resource_composition_render_service import render_composition_frame


def _resource_project(count=3):
    project=Project.create_default(width=4,height=4,frame_count=2)
    composition=ResourceComposition("Grouped",4,4,12,2)
    for index in range(count):
        pixels=np.zeros((1,1,4),dtype=np.uint8);pixels[0,0]=[40+index*50,0,0,255]
        asset=SourceAsset(f"Asset {index}",pixels);project.source_assets.append(asset)
        layer=CompositionLayer(asset.name,"source_asset",asset.id,0,1);layer.add_property("position").default_value=[index,0];composition.layers.append(layer)
    composition.repair_hierarchy();project.resource_compositions=[composition]
    return project,composition


def test_v11_group_roundtrip_retains_flat_leaf_objects_and_order():
    project,composition=_resource_project();ids=[item.id for item in composition.layers]
    group=LayerGroup("Pair",children=ids[:2]);composition.groups=[group]
    composition.root_order=[group_node(group.id),layer_node(ids[2])];composition.sync_flat_order()
    data=project.to_dict();loaded=Project.from_dict(deepcopy(data));result=loaded.resource_compositions[0]
    assert FORMAT_VERSION==17 and data["format_version"]==17
    assert [item.id for item in result.layers]==ids
    assert result.groups[0].children==ids[:2] and result.root_order==composition.root_order


def test_group_visibility_and_solo_are_render_neutral_metadata():
    project,composition=_resource_project(2);ids=[item.id for item in composition.layers]
    group=LayerGroup("All",children=ids);composition.groups=[group];composition.root_order=[group_node(group.id)];composition.sync_flat_order()
    visible=render_composition_frame(project,composition,0);assert visible[...,3].any()
    group.visible=False;composition.touch();assert not render_composition_frame(project,composition,0)[...,3].any()
    group.visible=True;group.solo=True;composition.touch();assert render_composition_frame(project,composition,0)[...,3].any()


def test_corrupt_hierarchy_repair_preserves_every_leaf_once():
    _,composition=_resource_project();ids=[item.id for item in composition.layers]
    composition.groups=[LayerGroup("Broken",id="g",children=[ids[0],"missing",ids[0]])]
    composition.root_order=[group_node("missing-group"),layer_node(ids[1]),layer_node(ids[1])]
    composition.repair_hierarchy()
    assert sorted(composition.flatten_layer_ids())==sorted(ids)
    assert len(composition.flatten_layer_ids())==len(set(composition.flatten_layer_ids()))
