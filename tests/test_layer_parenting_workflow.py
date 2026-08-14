import numpy as np

from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.services.layer_parenting_service import resolve_world_affines, resource_local_affine, set_parent_keep_world


def test_parent_workflow_rejects_self_and_keeps_world_on_set_clear():
    composition=ResourceComposition("c",32,32,12,1,layers=[CompositionLayer("a","source_asset","a",0,0),CompositionLayer("b","source_asset","b",0,0)])
    parent,child=composition.layers;parent.add_property("position").default_value=[7,3];child.add_property("position").default_value=[2,1]
    local=lambda item,frame:resource_local_affine(item,frame,composition)
    assert not set_parent_keep_world(composition.layers,child.id,child.id,0,local)
    before=local(child,0);assert set_parent_keep_world(composition.layers,child.id,parent.id,0,local)
    assert np.allclose(before,resolve_world_affines(composition.layers,0,local)[child.id])
    assert set_parent_keep_world(composition.layers,child.id,None,0,local)
