import numpy as np

from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.services.layer_parenting_service import resolve_world_affines, resource_local_affine


def test_parent_rotation_and_scale_transform_child_offset():
    parent=CompositionLayer("p","source_asset","p",0,0);child=CompositionLayer("c","source_asset","c",0,0,parent_id=parent.id)
    parent.add_property("rotation").default_value=90;parent.add_property("scale").default_value=[2,2];child.add_property("position").default_value=[3,0]
    composition=ResourceComposition("c",20,20,12,1,layers=[parent,child]);world=resolve_world_affines(composition.layers,0,lambda item,frame:resource_local_affine(item,frame,composition))
    origin=np.array((10,10,1.0));point=world[child.id]@origin
    assert np.allclose(point[:2],[10,16],atol=1e-7)
