"""One-level, render-neutral layer hierarchy metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class LayerGroup:
    name: str = "Group"
    visible: bool = True
    locked: bool = False
    solo: bool = False
    children: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "solo": self.solo,
            "children": list(self.children),
        }

    @classmethod
    def from_dict(cls, data) -> "LayerGroup":
        if not isinstance(data, dict):
            raise ValueError("layer group must be an object")
        children = data.get("children", [])
        if not isinstance(children, list):
            children = []
        return cls(
            id=str(data.get("id") or uuid4().hex),
            name=str(data.get("name") or "Group"),
            visible=bool(data.get("visible", True)),
            locked=bool(data.get("locked", False)),
            solo=bool(data.get("solo", False)),
            children=[str(value) for value in children],
        )


def layer_node(identifier: str) -> dict[str, str]:
    return {"type": "layer", "id": str(identifier)}


def group_node(identifier: str) -> dict[str, str]:
    return {"type": "group", "id": str(identifier)}


def repair_hierarchy(leaf_ids, groups, root_order):
    """Repair references without ever discarding a real leaf object."""
    leaf_ids = [str(value) for value in leaf_ids]
    valid_leaves = set(leaf_ids)
    clean_groups = []
    group_ids = set()
    claimed_leaves = set()
    for value in groups or []:
        group = value if isinstance(value, LayerGroup) else LayerGroup.from_dict(value)
        if group.id in group_ids:
            continue
        group_ids.add(group.id)
        children = []
        for identifier in group.children:
            if identifier in valid_leaves and identifier not in claimed_leaves:
                children.append(identifier)
                claimed_leaves.add(identifier)
        group.children = children
        clean_groups.append(group)
    group_by_id = {group.id: group for group in clean_groups}
    clean_root = []
    used_groups = set()
    used_root_leaves = set()
    for value in root_order or []:
        if not isinstance(value, dict):
            continue
        kind, identifier = value.get("type"), str(value.get("id", ""))
        if kind == "group" and identifier in group_by_id and identifier not in used_groups:
            clean_root.append(group_node(identifier));used_groups.add(identifier)
        elif kind == "layer" and identifier in valid_leaves and identifier not in claimed_leaves and identifier not in used_root_leaves:
            clean_root.append(layer_node(identifier));used_root_leaves.add(identifier)
    # Retain valid group metadata omitted by corrupt root_order, then preserve all
    # otherwise orphaned leaves in their original flat model order.
    for group in clean_groups:
        if group.id not in used_groups:
            clean_root.append(group_node(group.id));used_groups.add(group.id)
    present = claimed_leaves | used_root_leaves
    for identifier in leaf_ids:
        if identifier not in present:
            clean_root.append(layer_node(identifier));present.add(identifier)
    return clean_groups, clean_root


def flatten_hierarchy(groups, root_order) -> list[str]:
    group_by_id = {group.id: group for group in groups}
    result = []
    for node in root_order:
        if node.get("type") == "layer":
            result.append(node.get("id"))
        elif node.get("type") == "group" and node.get("id") in group_by_id:
            result.extend(group_by_id[node["id"]].children)
    return [value for value in result if value]


def parent_group(groups, leaf_id):
    return next((group for group in groups if leaf_id in group.children), None)
