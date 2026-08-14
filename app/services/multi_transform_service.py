"""Runtime-only world-space multi-transform calculations.

The editor keeps one canonical transform system per layer.  This module only
coordinates the existing local tracks: canvas gestures operate in world space,
while inspector edits continue to write absolute local values.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable

import numpy as np

from app.services.layer_parenting_service import (
    effect_local_affine,
    resource_local_affine,
    resolve_world_affines,
)


SUPPORTED_RESOURCE_PROPERTIES = ("position", "rotation", "scale")
SUPPORTED_EFFECT_PROPERTIES = (
    "position_x", "position_y", "rotation_z", "scale_x", "scale_y"
)
MIXED_TOLERANCE = 1e-6


@dataclass(frozen=True)
class TransformRootSnapshot:
    identifier: str
    world_origin: tuple[float, float]
    parent_inverse: np.ndarray
    local_origin: tuple[float, float]
    position: tuple[float, float]
    rotation_z: float
    scale: tuple[float, float]


@dataclass(frozen=True)
class MultiTransformContext:
    """Frozen selection/pivot data captured once at gesture begin."""

    selected_ids: tuple[str, ...]
    transform_root_ids: tuple[str, ...]
    pivot: tuple[float, float]
    origins: tuple[tuple[str, tuple[float, float]], ...]
    roots: tuple[TransformRootSnapshot, ...]


def get_selected_transform_roots(layers, selected_leaf_ids: Iterable[str]) -> list[str]:
    """Return selected leaves that have no selected ancestor, in model order."""

    selected = {str(value) for value in selected_leaf_ids}
    by_id = {layer.id: layer for layer in layers}
    result = []
    for layer in layers:
        if layer.id not in selected:
            continue
        parent_id = layer.parent_id
        seen = set()
        has_selected_ancestor = False
        while parent_id in by_id and parent_id not in seen:
            if parent_id in selected:
                has_selected_ancestor = True
                break
            seen.add(parent_id)
            parent_id = by_id[parent_id].parent_id
        if not has_selected_ancestor:
            result.append(layer.id)
    return result


def validate_multi_transform_selection(
    layers,
    selected_ids: Iterable[str],
    *,
    group_ids: Iterable[str] = (),
    effectively_locked: Callable[[object], bool] | None = None,
) -> tuple[list[object], str | None]:
    """Validate an atomic multi-edit selection without mutating anything."""

    selected = {str(value) for value in selected_ids}
    if selected & {str(value) for value in group_ids}:
        return [], "group"
    leaves = [layer for layer in layers if layer.id in selected]
    if len(leaves) < 2 or len(leaves) != len(selected):
        return [], "selection"
    locked = effectively_locked or (lambda layer: bool(getattr(layer, "locked", False)))
    if any(locked(layer) for layer in leaves):
        return [], "locked"
    return leaves, None


def mixed_numeric_value(values: Iterable[float], tolerance: float = MIXED_TOLERANCE):
    values = [float(value) for value in values]
    if not values:
        return None
    first = values[0]
    return first if all(math.isclose(first, value, rel_tol=0.0, abs_tol=tolerance) for value in values[1:]) else None


def _point(matrix, point) -> np.ndarray:
    value = np.asarray((float(point[0]), float(point[1]), 1.0), dtype=np.float64)
    return (np.asarray(matrix, dtype=np.float64) @ value)[:2]


def _build_context(layers, selected_ids, frame, local_builder, local_origin_builder, value_builder):
    selected = {str(value) for value in selected_ids}
    ordered_selected = [layer.id for layer in layers if layer.id in selected]
    worlds = resolve_world_affines(layers, frame, local_builder)
    by_id = {layer.id: layer for layer in layers}
    origins = {}
    for identifier in ordered_selected:
        layer = by_id[identifier]
        origins[identifier] = _point(worlds[identifier], local_origin_builder(layer))
    if not origins:
        raise ValueError("multi-transform selection is empty")
    xs = [value[0] for value in origins.values()]
    ys = [value[1] for value in origins.values()]
    pivot = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
    root_ids = get_selected_transform_roots(layers, selected)
    roots = []
    identity = np.eye(3, dtype=np.float64)
    for identifier in root_ids:
        layer = by_id[identifier]
        local = local_builder(layer, frame)
        try:
            parent_prefix = worlds[identifier] @ np.linalg.inv(local)
            parent_inverse = np.linalg.inv(parent_prefix)
        except np.linalg.LinAlgError as exc:
            raise ValueError("non-invertible parent transform") from exc
        position, rotation_z, scale = value_builder(layer)
        roots.append(
            TransformRootSnapshot(
                identifier,
                (float(origins[identifier][0]), float(origins[identifier][1])),
                parent_inverse if layer.parent_id is not None or not np.allclose(parent_prefix, identity) else identity,
                tuple(map(float, local_origin_builder(layer))),
                tuple(map(float, position)),
                float(rotation_z),
                tuple(map(float, scale)),
            )
        )
    frozen_origins=tuple((identifier,(float(origins[identifier][0]),float(origins[identifier][1]))) for identifier in ordered_selected)
    return MultiTransformContext(tuple(ordered_selected), tuple(root_ids), tuple(map(float, pivot)), frozen_origins, tuple(roots))


def build_resource_multi_transform_context(composition, selected_ids, frame: int) -> MultiTransformContext:
    def values(layer):
        return layer.value("position", frame), layer.value("rotation", frame), layer.value("scale", frame)

    return _build_context(
        composition.layers,
        selected_ids,
        int(frame),
        lambda layer, value: resource_local_affine(layer, value, composition),
        lambda _layer: (composition.width / 2.0, composition.height / 2.0),
        values,
    )


def build_effect_multi_transform_context(project, selected_ids, frame: int) -> MultiTransformContext:
    def values(layer):
        transform = layer.layer_space_transform
        return (
            (transform.value("position_x", frame), transform.value("position_y", frame)),
            transform.value("rotation_z", frame),
            (transform.value("scale_x", frame), transform.value("scale_y", frame)),
        )

    def origin(layer):
        value = layer.layer_space_transform.evaluated(frame)
        return (project.width / 2.0 + value.pivot_x, project.height / 2.0 + value.pivot_y)

    return _build_context(
        project.effect_resource_layers,
        selected_ids,
        int(frame),
        lambda layer, value: effect_local_affine(layer, value, project),
        origin,
        values,
    )


def _target_values(context, operation, value):
    cx, cy = context.pivot
    if operation == "move":
        dx, dy = map(float, value)
        world_targets = [(root.world_origin[0] + dx, root.world_origin[1] + dy) for root in context.roots]
        rotations = [root.rotation_z for root in context.roots]
        scales = [root.scale for root in context.roots]
    elif operation == "rotate":
        delta = float(value)
        angle = math.radians(delta)
        cosine, sine = math.cos(angle), math.sin(angle)
        world_targets = []
        for root in context.roots:
            x, y = root.world_origin[0] - cx, root.world_origin[1] - cy
            world_targets.append((cx + cosine * x - sine * y, cy + sine * x + cosine * y))
        rotations = [root.rotation_z + delta for root in context.roots]
        scales = [root.scale for root in context.roots]
    elif operation == "scale":
        factor_x, factor_y = map(float, value)
        if not math.isfinite(factor_x) or not math.isfinite(factor_y) or factor_x <= 0.0 or factor_y <= 0.0:
            raise ValueError("invalid multi-scale factor")
        scales = [(root.scale[0] * factor_x, root.scale[1] * factor_y) for root in context.roots]
        if any(x < 0.01 or y < 0.01 or not math.isfinite(x) or not math.isfinite(y) for x, y in scales):
            raise ValueError("multi-scale result is outside the supported range")
        world_targets = [
            (cx + (root.world_origin[0] - cx) * factor_x, cy + (root.world_origin[1] - cy) * factor_y)
            for root in context.roots
        ]
        rotations = [root.rotation_z for root in context.roots]
    else:
        raise ValueError("unsupported multi-transform operation")
    result = []
    for root, world, rotation, scale in zip(context.roots, world_targets, rotations, scales):
        local_world = _point(root.parent_inverse, world)
        position = (
            root.position[0] + local_world[0] - (root.local_origin[0] + root.position[0]),
            root.position[1] + local_world[1] - (root.local_origin[1] + root.position[1]),
        )
        result.append((root.identifier, tuple(map(float, position)), float(rotation), tuple(map(float, scale))))
    return result


def _set_resource_track_value(layer, property_id, frame, value) -> bool:
    current = layer.value(property_id, frame)
    if isinstance(current, (list, tuple)):
        if all(math.isclose(float(a), float(b), abs_tol=1e-12) for a, b in zip(current, value)):
            return False
    elif math.isclose(float(current), float(value), abs_tol=1e-12):
        return False
    track = layer.add_property(property_id)
    key = track.keyframe_at(frame)
    if key is not None:
        key.value = list(value) if isinstance(value, tuple) else value
    elif track.keyframes:
        track.set_keyframe(frame, list(value) if isinstance(value, tuple) else value, "Linear")
    else:
        track.default_value = list(value) if isinstance(value, tuple) else value
    return True


def set_resource_local_component(layer, property_id, component: int, frame: int, value: float) -> bool:
    if property_id not in SUPPORTED_RESOURCE_PROPERTIES:
        raise ValueError("unsupported Resource multi-edit property")
    if property_id == "rotation":
        return _set_resource_track_value(layer, property_id, frame, float(value))
    current = list(layer.value(property_id, frame))
    current[int(component)] = float(value)
    return _set_resource_track_value(layer, property_id, frame, tuple(current))


def _set_effect_value(layer, property_id, frame, value) -> bool:
    transform = layer.layer_space_transform
    current = transform.value(property_id, frame)
    if math.isclose(current, float(value), abs_tol=1e-12):
        return False
    track = transform.tracks.get(property_id)
    key = track.keyframe_at(frame) if track else None
    if key is not None:
        key.value = float(value)
        transform.revision += 1
    elif track and track.keyframes:
        transform.set_keyframe(property_id, frame, float(value), "Linear")
    else:
        transform.set_property(property_id, float(value))
    return True


def set_effect_local_property(layer, property_id, frame: int, value: float) -> bool:
    if property_id not in SUPPORTED_EFFECT_PROPERTIES:
        raise ValueError("unsupported Effect multi-edit property")
    return _set_effect_value(layer, property_id, int(frame), float(value))


def apply_resource_multi_transform(composition, context, operation, value, frame: int) -> bool:
    by_id = {layer.id: layer for layer in composition.layers}
    changed = False
    for identifier, position, rotation, scale in _target_values(context, operation, value):
        layer = by_id[identifier]
        changed = _set_resource_track_value(layer, "position", frame, position) or changed
        if operation == "rotate":
            changed = _set_resource_track_value(layer, "rotation", frame, rotation) or changed
        elif operation == "scale":
            changed = _set_resource_track_value(layer, "scale", frame, scale) or changed
    return changed


def apply_effect_multi_transform(project, context, operation, value, frame: int) -> bool:
    by_id = {layer.id: layer for layer in project.effect_resource_layers}
    changed = False
    for identifier, position, rotation, scale in _target_values(context, operation, value):
        layer = by_id[identifier]
        changed = _set_effect_value(layer, "position_x", frame, position[0]) or changed
        changed = _set_effect_value(layer, "position_y", frame, position[1]) or changed
        if operation == "rotate":
            changed = _set_effect_value(layer, "rotation_z", frame, rotation) or changed
        elif operation == "scale":
            changed = _set_effect_value(layer, "scale_x", frame, scale[0]) or changed
            changed = _set_effect_value(layer, "scale_y", frame, scale[1]) or changed
    return changed
