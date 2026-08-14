from copy import deepcopy

from app.models.layer_parenting import surviving_parent_dependencies
from app.models.resource_composition import CompositionLayer


def test_duplicate_remap_policy_and_delete_dependency_detection():
    parent=CompositionLayer("p","source_asset","p",0,0);child=CompositionLayer("c","source_asset","c",0,0,parent_id=parent.id)
    assert surviving_parent_dependencies([parent,child],{parent.id})==[(child.id,parent.id)]
    assert surviving_parent_dependencies([parent,child],{parent.id,child.id})==[]
    parent_copy=deepcopy(parent);parent_copy.id="parent-copy";child_copy=deepcopy(child);child_copy.id="child-copy";remap={parent.id:parent_copy.id,child.id:child_copy.id};child_copy.parent_id=remap.get(child_copy.parent_id,child_copy.parent_id)
    assert child_copy.parent_id==parent_copy.id
