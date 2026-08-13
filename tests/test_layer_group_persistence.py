from copy import deepcopy

from app.models.layer_group import LayerGroup, group_node, layer_node
from app.models.project import Project


def test_v10_migration_creates_flat_v11_root_order():
    project=Project.create_default(width=4,height=4,frame_count=2);data=project.to_dict();data["format_version"]=10;data.pop("effect_layer_groups",None);data.pop("effect_root_order",None)
    loaded=Project.from_dict(deepcopy(data));saved=loaded.to_dict()
    assert loaded.effect_layer_groups==[] and saved["format_version"]==11 and "effect_root_order" in saved


def test_duplicate_and_unknown_root_references_are_repaired():
    project=Project.create_default(width=4,height=4,frame_count=2)
    # Empty groups are legal and survive repair even when root metadata is damaged.
    group=LayerGroup("Empty",id="empty");project.effect_layer_groups=[group];project.effect_root_order=[group_node("missing"),group_node("empty"),group_node("empty"),layer_node("missing")];project.repair_effect_hierarchy()
    assert project.effect_root_order==[group_node("empty")] and project.effect_layer_groups[0].children==[]
