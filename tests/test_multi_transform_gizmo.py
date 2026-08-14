from __future__ import annotations

from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.services.multi_transform_service import build_resource_multi_transform_context


def test_selection_pivot_includes_hidden_leaf_and_context_is_runtime_only():
    a=CompositionLayer("a","source_asset","a",0,1);b=CompositionLayer("b","source_asset","b",0,1,visible=False)
    a.add_property("position").default_value=[-20,0];b.add_property("position").default_value=[40,10]
    composition=ResourceComposition("R",64,64,layers=[a,b]);before=composition.to_dict();context=build_resource_multi_transform_context(composition,{a.id,b.id},0)
    assert context.pivot==(42,37) and dict(context.origins)[b.id]==(72,42) and composition.to_dict()==before


def test_selection_context_has_all_selected_origins_but_only_direct_roots():
    parent=CompositionLayer("parent","source_asset","a",0,1);child=CompositionLayer("child","source_asset","b",0,1,parent_id=parent.id);free=CompositionLayer("free","source_asset","c",0,1)
    composition=ResourceComposition("R",64,64,layers=[parent,child,free]);context=build_resource_multi_transform_context(composition,{parent.id,child.id,free.id},0)
    assert {identifier for identifier,_origin in context.origins}=={parent.id,child.id,free.id}
    assert context.transform_root_ids==(parent.id,free.id)
