from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.services.layer_parenting_service import effect_local_affine, resource_local_affine, resolve_world_affines
from app.services.multi_transform_service import (
    apply_effect_multi_transform,
    apply_resource_multi_transform,
    build_effect_multi_transform_context,
    build_resource_multi_transform_context,
    get_selected_transform_roots,
)


def _resource_layer(name, position=(0.0, 0.0)):
    layer = CompositionLayer(name, "source_asset", name, 0, 12)
    layer.add_property("position").default_value = list(position)
    return layer


def _resource_origins(composition, frame=0):
    worlds = resolve_world_affines(
        composition.layers, frame, lambda layer, value: resource_local_affine(layer, value, composition)
    )
    point = np.array((composition.width / 2, composition.height / 2, 1.0))
    return {identifier: tuple((matrix @ point)[:2]) for identifier, matrix in worlds.items()}


def _effect_origins(project, frame=0):
    worlds = resolve_world_affines(
        project.effect_resource_layers, frame, lambda layer, value: effect_local_affine(layer, value, project)
    )
    result = {}
    for layer in project.effect_resource_layers:
        transform = layer.layer_transform.evaluated(frame)
        point = np.array((project.width / 2 + transform.pivot_x, project.height / 2 + transform.pivot_y, 1.0))
        result[layer.id] = tuple((worlds[layer.id] @ point)[:2])
    return result


def test_transform_roots_exclude_every_selected_descendant():
    a, b, c, free = (_resource_layer(name) for name in ("a", "b", "c", "free"))
    b.parent_id = a.id
    c.parent_id = b.id
    assert get_selected_transform_roots([a, b, c, free], {a.id, b.id, c.id, free.id}) == [a.id, free.id]
    assert get_selected_transform_roots([a, b, c, free], {b.id, c.id}) == [b.id]


def test_resource_selection_pivot_uses_all_selected_world_origins_and_is_frozen():
    a, b = _resource_layer("a", (0, 0)), _resource_layer("b", (100, 40))
    composition = ResourceComposition("R", 64, 64, layers=[a, b])
    context = build_resource_multi_transform_context(composition, {a.id, b.id}, 0)
    assert context.pivot == pytest.approx((82, 52))
    apply_resource_multi_transform(composition, context, "move", (25, -10), 0)
    assert context.pivot == pytest.approx((82, 52))


def test_resource_world_move_handles_rotated_parent_and_keeps_parent_relation():
    parent, child, free = _resource_layer("parent"), _resource_layer("child", (20, 0)), _resource_layer("free", (-10, 5))
    parent.add_property("rotation").default_value = 90
    child.parent_id = parent.id
    composition = ResourceComposition("R", 64, 64, layers=[parent, child, free])
    before = _resource_origins(composition)
    relation = (child.parent_id, child.parent_offset)
    context = build_resource_multi_transform_context(composition, {child.id, free.id}, 0)
    assert apply_resource_multi_transform(composition, context, "move", (50, -7), 0)
    after = _resource_origins(composition)
    for identifier in (child.id, free.id):
        assert np.subtract(after[identifier], before[identifier]) == pytest.approx((50, -7))
    assert (child.parent_id, child.parent_offset) == relation


@pytest.mark.parametrize("operation,value", [("move", (20, 10)), ("rotate", 90), ("scale", (2, 2))])
def test_resource_parent_child_selection_mutates_only_parent_root(operation, value):
    parent, child = _resource_layer("parent", (-20, 0)), _resource_layer("child", (40, 0))
    child.parent_id = parent.id
    composition = ResourceComposition("R", 64, 64, layers=[parent, child])
    child_before = deepcopy(child.tracks)
    context = build_resource_multi_transform_context(composition, {parent.id, child.id}, 0)
    assert context.transform_root_ids == (parent.id,)
    apply_resource_multi_transform(composition, context, operation, value, 0)
    assert child.tracks == child_before


def test_effect_multi_rotate_and_scale_preserve_surface_and_non_xy_fields():
    project = Project.create_default(width=64, height=64)
    a = EffectResourceLayer("a", "resource", end_frame=12)
    b = EffectResourceLayer("b", "resource", end_frame=12)
    a.layer_transform.position_x = -50
    b.layer_transform.position_x = 50
    a.layer_transform.position_z = 9
    b.layer_transform.rotation_x = 17
    a.surface_transform.position_x = 33
    project.effect_resource_layers = [a, b]
    surface = deepcopy(a.surface_transform)
    context = build_effect_multi_transform_context(project, {a.id, b.id}, 0)
    apply_effect_multi_transform(project, context, "rotate", 90, 0)
    origins = _effect_origins(project)
    assert origins[a.id] == pytest.approx((32, -18))
    assert origins[b.id] == pytest.approx((32, 82))
    assert a.layer_transform.rotation_z == pytest.approx(90)
    assert b.layer_transform.rotation_z == pytest.approx(90)
    assert a.layer_transform.position_z == 9 and b.layer_transform.rotation_x == 17
    assert a.surface_transform == surface
    scale_context = build_effect_multi_transform_context(project, {a.id, b.id}, 0)
    apply_effect_multi_transform(project, scale_context, "scale", (2, 2), 0)
    assert a.layer_transform.scale_x == pytest.approx(2) and b.layer_transform.scale_y == pytest.approx(2)
