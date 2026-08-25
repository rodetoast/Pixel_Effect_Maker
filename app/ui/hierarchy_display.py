"""Pure hierarchy display helpers shared by Resource and Effect editors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


DROP_BEFORE = "before"
DROP_AFTER = "after"
DROP_INTO = "into"
DROP_INVALID = "invalid"


@dataclass(frozen=True)
class HierarchyDisplayRow:
    identifier: str
    kind: str
    name: str
    group_id: str | None = None
    parent_id: str | None = None
    parent_label: str = ""
    visible: bool = True
    own_locked: bool = False
    inherited_locked: bool = False
    solo: bool = False
    expanded: bool = False
    child_count: int = 0
    selected: bool = False
    primary: bool = False

    @property
    def depth(self) -> int:
        return 1 if self.group_id else 0


def _group_membership(groups) -> dict[str, str]:
    return {str(child): str(group.id) for group in groups for child in group.children}


def layer_display_labels(layers, groups) -> dict[str, str]:
    """Return readable, stable disambiguated labels for parent candidate layers."""

    group_by_id = {str(group.id): group for group in groups}
    membership = _group_membership(groups)
    counts: dict[str, int] = {}
    for layer in layers:
        counts[layer.name] = counts.get(layer.name, 0) + 1
    provisional: dict[str, str] = {}
    for layer in layers:
        label = layer.name
        if counts.get(layer.name, 0) > 1:
            group = group_by_id.get(membership.get(str(layer.id), ""))
            if group is not None:
                label = f"{group.name} / {layer.name}"
        provisional[str(layer.id)] = label
    duplicate_labels: dict[str, int] = {}
    for label in provisional.values():
        duplicate_labels[label] = duplicate_labels.get(label, 0) + 1
    return {
        str(layer.id): f"{provisional[str(layer.id)]} · {str(layer.id)[:4]}" if duplicate_labels[provisional[str(layer.id)]] > 1 else provisional[str(layer.id)]
        for layer in layers
    }


def parent_display_labels(layers, groups) -> dict[str, str]:
    """Resolve readable parent labels while relations continue to use stable IDs."""

    by_id = {str(layer.id): layer for layer in layers}
    candidate_labels = layer_display_labels(layers, groups)
    result = {}
    for layer in layers:
        parent = by_id.get(str(layer.parent_id))
        if parent is not None:
            result[str(layer.id)] = candidate_labels[str(parent.id)]
    return result


def build_hierarchy_rows(
    layers,
    groups,
    root_order,
    expanded_ids: Iterable[str] = (),
    selected_ids: Iterable[str] = (),
    primary_id: str | None = None,
    *,
    visibility: Callable[[object], bool] | None = None,
    effective_locked: Callable[[object], bool] | None = None,
) -> list[HierarchyDisplayRow]:
    """Return top-to-bottom display rows without mutating model or selection state."""

    expanded = {str(value) for value in expanded_ids}
    selected = {str(value) for value in selected_ids}
    layers_by_id = {str(layer.id): layer for layer in layers}
    groups_by_id = {str(group.id): group for group in groups}
    labels = parent_display_labels(layers, groups)
    visible_of = visibility or (lambda value: bool(getattr(value, "visible", True)))
    locked_of = effective_locked or (lambda value: bool(getattr(value, "locked", False)))
    result: list[HierarchyDisplayRow] = []

    def leaf_row(layer, group_id=None):
        own_locked = bool(getattr(layer, "locked", False))
        result.append(HierarchyDisplayRow(
            str(layer.id), "leaf", layer.name, group_id, str(layer.parent_id) if layer.parent_id else None,
            labels.get(str(layer.id), ""), bool(visible_of(layer)), own_locked,
            bool(locked_of(layer)) and not own_locked, bool(getattr(layer, "solo", False)),
            selected=str(layer.id) in selected, primary=str(layer.id) == primary_id,
        ))

    for node in reversed(root_order):
        identifier = str(node.get("id"))
        if node.get("type") == "group" and identifier in groups_by_id:
            group = groups_by_id[identifier]
            result.append(HierarchyDisplayRow(
                identifier, "group", group.name, visible=bool(group.visible), own_locked=bool(group.locked),
                solo=bool(group.solo), expanded=identifier in expanded, child_count=len(group.children),
                selected=identifier in selected, primary=identifier == primary_id,
            ))
            if identifier in expanded:
                for child in reversed(group.children):
                    layer = layers_by_id.get(str(child))
                    if layer is not None:
                        leaf_row(layer, identifier)
        else:
            layer = layers_by_id.get(identifier)
            if layer is not None:
                leaf_row(layer)
    return result


def classify_drop_zone(kind: str, y: float, height: float) -> str:
    """Classify a row-relative pointer position as Before, After, or Into Group."""

    if height <= 0:
        return DROP_INVALID
    ratio = max(0.0, min(1.0, float(y) / float(height)))
    if kind == "group":
        if ratio < 0.25:
            return DROP_BEFORE
        if ratio > 0.75:
            return DROP_AFTER
        return DROP_INTO
    return DROP_BEFORE if ratio < 0.5 else DROP_AFTER


def resolve_drop_target(
    target_id: str,
    zone: str,
    node_kind: dict[str, str],
    node_parent: dict[str, str | None],
    sibling_order: dict[str | None, list[str]],
    selected_ids: Iterable[str],
) -> tuple[str | None, int] | None:
    if zone == DROP_INTO:
        return (target_id, 0) if node_kind.get(target_id) == "group" else None
    parent_id = node_parent.get(target_id)
    siblings = sibling_order.get(parent_id, [])
    if target_id not in siblings or zone not in {DROP_BEFORE, DROP_AFTER}:
        return None
    target = siblings.index(target_id) + (zone == DROP_AFTER)
    selected = set(selected_ids)
    target -= sum(1 for index, identifier in enumerate(siblings) if index < target and identifier in selected)
    return parent_id, max(0, target)


def drop_is_allowed(
    selected_ids: Iterable[str],
    target_id: str,
    zone: str,
    node_kind: dict[str, str],
    node_parent: dict[str, str | None],
    locked_ids: Iterable[str],
) -> bool:
    selected = {str(value) for value in selected_ids}
    locked = {str(value) for value in locked_ids}
    if not selected or target_id in selected or selected & locked:
        return False
    parents = {node_parent.get(value) for value in selected}
    if len(parents) != 1:
        return False
    if zone == DROP_INTO:
        return node_kind.get(target_id) == "group" and target_id not in locked and not any(node_kind.get(value) == "group" for value in selected)
    target_parent = node_parent.get(target_id)
    return target_parent not in locked


def context_action_states(kind: str, selection_count: int, locked: bool, parented: bool) -> dict[str, bool]:
    """View-only action availability; mutation entry points remain authoritative."""

    is_group = kind == "group"
    return {
        "duplicate": selection_count > 0,
        "delete": selection_count > 0 and not locked,
        "group": selection_count >= 2 and not is_group,
        "ungroup": selection_count == 1 and is_group and not locked,
        "set_parent": selection_count == 1 and not is_group and not locked,
        "clear_parent": selection_count == 1 and not is_group and parented and not locked,
        "state": selection_count > 0,
        "reorder": selection_count > 0 and not locked,
        "expand_all": True,
        "collapse_all": True,
    }


def elide_text(metrics, text: str, width: int) -> str:
    from PySide6.QtCore import Qt

    return metrics.elidedText(str(text), Qt.TextElideMode.ElideRight, max(24, int(width)))
