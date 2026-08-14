from __future__ import annotations

from copy import deepcopy
from time import perf_counter

from app.models.layer_group import LayerGroup,group_node,layer_node
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.services.multi_transform_service import apply_resource_multi_transform,build_resource_multi_transform_context


def test_100_layer_parented_multi_transform_smoke():
    layers=[CompositionLayer(f"L{index}","source_asset",f"A{index}",0,12) for index in range(100)]
    for index in range(1,51):layers[index].parent_id=layers[index-1].id
    groups=[LayerGroup(f"G{index}",children=[item.id for item in layers[index*5:index*5+5]]) for index in range(10)]
    roots=[group_node(group.id) for group in groups]+[layer_node(layer.id) for layer in layers[50:]]
    composition=ResourceComposition("Performance",600,600,12,13,layers=layers,groups=groups,root_order=roots)
    selected={layer.id for layer in layers};started=perf_counter();context=build_resource_multi_transform_context(composition,selected,6);pivot_ms=(perf_counter()-started)*1000
    timings={"pivot":pivot_ms}
    for operation,value in (("move",(5,-3)),("rotate",15),("scale",(1.01,.99))):
        before={layer.id:deepcopy(layer.tracks) for layer in layers if layer.id in context.transform_root_ids};started=perf_counter();apply_resource_multi_transform(composition,context,operation,value,6);timings[operation]=(perf_counter()-started)*1000
        after={layer.id:deepcopy(layer.tracks) for layer in layers if layer.id in context.transform_root_ids};started=perf_counter();_undo_payload=(before,after);timings["undo_commit"]=(perf_counter()-started)*1000
    assert len(context.selected_ids)==100 and len(groups)==10 and sum(layer.parent_id is not None for layer in layers)==50
    assert all(value>=0 for value in timings.values()) and _undo_payload
