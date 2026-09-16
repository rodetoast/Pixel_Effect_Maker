"""Core project model and frame/layer operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.project_defaults import (
    DEFAULT_PROJECT_FPS,
    DEFAULT_PROJECT_FRAME_COUNT,
    DEFAULT_PROJECT_HEIGHT,
    DEFAULT_PROJECT_WIDTH,
)

from .frame import Frame, empty_pixels
from .layer import Layer
from .source_asset import SourceAsset
from .effect_generator import TransformEmitter
from .animation_clip import AnimationClipAsset
from .particle_emitter import ParticleEmitter
from .resource_composition import ResourceComposition
from .effect_composition_layer import EffectCompositionLayer
from .effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from .layer_group import LayerGroup,flatten_hierarchy,layer_node,parent_group,repair_hierarchy
from .layer_parenting import repair_parent_links

FORMAT_VERSION = 15
MAX_COMPACT_PROJECT_PIXEL_BYTES = 512 * 1024 * 1024


class ProjectError(ValueError):
    """Raised when project data is invalid or unsupported."""


@dataclass
class Project:
    """UI-independent pixel animation project."""

    name: str = "Untitled"
    width: int = DEFAULT_PROJECT_WIDTH
    height: int = DEFAULT_PROJECT_HEIGHT
    fps: int = DEFAULT_PROJECT_FPS
    loop: bool = True
    layers: list[Layer] = field(default_factory=list)
    frames: list[Frame] = field(default_factory=list)
    source_assets: list[SourceAsset] = field(default_factory=list)
    generators: list[TransformEmitter] = field(default_factory=list)
    animation_clips: list[AnimationClipAsset] = field(default_factory=list)
    particle_emitters: list[ParticleEmitter] = field(default_factory=list)
    resource_compositions: list[ResourceComposition] = field(default_factory=list)
    effect_composition_layers: list[EffectCompositionLayer] = field(default_factory=list)
    effect_resource_layers: list[EffectResourceLayer] = field(default_factory=list)
    effect_layer_groups: list[LayerGroup] = field(default_factory=list)
    effect_root_order: list[dict[str, str]] = field(default_factory=list)
    format_version: int = FORMAT_VERSION

    def __post_init__(self) -> None:
        self._validate_dimensions()
        self.repair_effect_hierarchy()

    def repair_effect_hierarchy(self) -> None:
        leaf_ids=[item.id for item in self.effect_resource_layers]
        if not self.effect_layer_groups:self.effect_root_order=[layer_node(value) for value in leaf_ids]
        self.effect_layer_groups,self.effect_root_order=repair_hierarchy(leaf_ids,self.effect_layer_groups,self.effect_root_order)
        repair_parent_links(self.effect_resource_layers)
        self.sync_effect_flat_order()

    def sync_effect_flat_order(self) -> None:
        by_id={item.id:item for item in self.effect_resource_layers};ordered=flatten_hierarchy(self.effect_layer_groups,self.effect_root_order)
        self.effect_resource_layers=[by_id[value] for value in ordered if value in by_id]
        generated_ids=[item.generated_layer_id for item in self.effect_resource_layers if item.generated_layer_id]
        positions=[index for index,item in enumerate(self.layers) if item.id in set(generated_ids)]
        layer_by_id={item.id:item for item in self.layers}
        for position,identifier in zip(positions,generated_ids):
            if identifier in layer_by_id:self.layers[position]=layer_by_id[identifier]

    def effect_flatten_layer_ids(self):return flatten_hierarchy(self.effect_layer_groups,self.effect_root_order)
    def effect_group_by_id(self,identifier):return next((group for group in self.effect_layer_groups if group.id==identifier),None)
    def effect_parent_group(self,leaf_id):return parent_group(self.effect_layer_groups,leaf_id)
    def effect_effective_visible(self,leaf):
        group=self.effect_parent_group(leaf.id);return leaf.visible and (group is None or group.visible)
    def effect_effective_locked(self,leaf):
        group=self.effect_parent_group(leaf.id);return leaf.locked or bool(group and group.locked)
    def effect_preview_solo_active(self):return any(item.solo for item in self.effect_resource_layers) or any(group.solo for group in self.effect_layer_groups)
    def effect_preview_soloed(self,leaf):
        group=self.effect_parent_group(leaf.id);return leaf.solo or bool(group and group.solo)

    @classmethod
    def create_default(
        cls,
        name: str = "Untitled",
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        loop: bool = True,
        frame_count: int | None = None,
    ) -> "Project":
        default_geometry = width is None and height is None and fps is None
        width = DEFAULT_PROJECT_WIDTH if width is None else int(width)
        height = DEFAULT_PROJECT_HEIGHT if height is None else int(height)
        fps = DEFAULT_PROJECT_FPS if fps is None else int(fps)
        if frame_count is None:
            frame_count = DEFAULT_PROJECT_FRAME_COUNT if default_geometry else 1
        frame_count = int(frame_count)
        if frame_count < 1:
            raise ProjectError("frame count must be positive")
        project = cls(name=name, width=width, height=height, fps=fps, loop=loop)
        project.add_layer("Layer 1")
        for _ in range(frame_count):
            project.add_frame()
        return project

    def _validate_dimensions(self) -> None:
        if not (1 <= int(self.width) <= 1024 and 1 <= int(self.height) <= 1024):
            raise ProjectError("canvas dimensions must be between 1 and 1024 pixels")
        if not (1 <= int(self.fps) <= 120):
            raise ProjectError("FPS must be between 1 and 120")

    def add_layer(self, name: str | None = None) -> Layer:
        layer = Layer(name=name or self.next_layer_name())
        self.layers.append(layer)
        for frame in self.frames:
            frame.layer_pixels[layer.id] = empty_pixels(self.width, self.height)
        return layer

    def next_layer_name(self) -> str:
        """Return the first available default layer name."""
        existing = {layer.name for layer in self.layers}
        number = 1
        while f"Layer {number}" in existing:
            number += 1
        return f"Layer {number}"

    def delete_layer(self, index: int) -> None:
        if len(self.layers) <= 1:
            raise ProjectError("a project must contain at least one layer")
        layer = self.layers.pop(index)
        for generator in self.generators:
            if generator.generated_layer_id == layer.id:
                generator.generated_layer_id = None
        for emitter in self.particle_emitters:
            if emitter.generated_layer_id == layer.id:
                emitter.generated_layer_id = None
        for composition_layer in self.effect_composition_layers:
            if composition_layer.generated_layer_id == layer.id:
                composition_layer.generated_layer_id = None
        for resource_layer in self.effect_resource_layers:
            if resource_layer.generated_layer_id == layer.id:
                resource_layer.generated_layer_id = None
        for frame in self.frames:
            frame.layer_pixels.pop(layer.id, None)

    def add_frame(self) -> Frame:
        frame = Frame(name=f"Frame {len(self.frames) + 1}")
        frame.layer_pixels = {
            layer.id: empty_pixels(self.width, self.height) for layer in self.layers
        }
        self.frames.append(frame)
        return frame

    def insert_empty_frame(self, index: int) -> Frame:
        """Insert a transparent frame immediately after the given frame."""
        frame = Frame(name=f"Frame {len(self.frames) + 1}")
        frame.layer_pixels = {
            layer.id: empty_pixels(self.width, self.height) for layer in self.layers
        }
        self.frames.insert(index + 1, frame)
        return frame

    def duplicate_frame(self, index: int) -> Frame:
        source = self.frames[index]
        duplicate = Frame(
            # Keep the compatibility field without accumulating display suffixes.
            # Timeline labels are derived from the current list position.
            name=source.name,
            layer_pixels={key: value.copy() for key, value in source.layer_pixels.items()},
        )
        self.frames.insert(index + 1, duplicate)
        return duplicate

    def delete_frame(self, index: int) -> None:
        if len(self.frames) <= 1:
            raise ProjectError("a project must contain at least one frame")
        self.frames.pop(index)

    def compose_frame(self, index: int, *, solo_preview: bool = False) -> np.ndarray:
        """Alpha-composite visible layers and return an RGBA buffer."""
        from app.models.blend_mode import project_layer_blend_mode
        from app.services.alpha_composite_service import composite_rgba8_over_float32
        output = np.zeros((self.height, self.width, 4), dtype=np.float32)
        frame = self.frames[index]
        resource_by_generated = {item.generated_layer_id: item for item in self.effect_resource_layers}
        has_solo = solo_preview and self.effect_preview_solo_active()
        resource_slots = [i for i, layer in enumerate(self.layers) if layer.id in resource_by_generated]
        ordered_layers = list(self.layers)
        # Stable ascending Z: farther layers first, nearer layers composite later.
        sorted_resources = sorted(
            (self.layers[i] for i in resource_slots),
            key=lambda layer: resource_by_generated[layer.id].layer_transform.value("position_z", index) if resource_by_generated[layer.id].advanced_transform_enabled else 0.0,
        )
        for slot, layer in zip(resource_slots, sorted_resources, strict=True):
            ordered_layers[slot] = layer
        for layer in ordered_layers:
            if not layer.visible:
                continue
            logical = resource_by_generated.get(layer.id)
            if logical is not None and not self.effect_effective_visible(logical):
                continue
            if has_solo and (logical is None or not self.effect_preview_soloed(logical)):
                continue
            source = frame.layer_pixels.get(layer.id)
            if source is None:
                continue
            composite_rgba8_over_float32(output, source, layer.opacity, project_layer_blend_mode(self, layer.id))
        return np.clip(output * 255.0, 0, 255).astype(np.uint8)

    def to_dict(self) -> dict[str, Any]:
        for composition in self.resource_compositions:composition.repair_hierarchy()
        self.repair_effect_hierarchy()
        return {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "canvas": {"width": self.width, "height": self.height},
            "animation": {"fps": self.fps, "loop": self.loop},
            "layers": [layer.to_dict() for layer in self.layers],
            "frames": [frame.to_dict() for frame in self.frames],
            "source_assets": [asset.to_dict() for asset in self.source_assets],
            "generators": [generator.to_dict() for generator in self.generators],
            "animation_clips": [clip.to_dict() for clip in self.animation_clips],
            "resource_compositions": [composition.to_dict() for composition in self.resource_compositions],
            "effect_resource_layers": [layer.to_dict() for layer in self.effect_resource_layers],
            "effect_layer_groups": [group.to_dict() for group in self.effect_layer_groups],
            "effect_root_order": self.effect_root_order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        if not isinstance(data, dict):
            raise ProjectError("project root must be a JSON object")
        version = data.get("format_version")
        if isinstance(version, int) and not isinstance(version, bool) and version > FORMAT_VERSION:
            raise ProjectError(
                f"unsupported format_version {version}: project requires a newer application version"
            )
        if version not in tuple(range(1, FORMAT_VERSION + 1)):
            raise ProjectError(f"unsupported format_version: {version!r}")
        if int(version) >= 7:
            compact_bytes = 0
            pending = [data]
            while pending:
                value = pending.pop()
                if isinstance(value, dict):
                    if value.get("encoding") == "rgba8-zlib-base64":
                        try:
                            compact_bytes += int(value["byte_length"])
                        except (KeyError, TypeError, ValueError) as exc:
                            raise ProjectError("invalid compact pixel payload metadata") from exc
                        if compact_bytes > MAX_COMPACT_PROJECT_PIXEL_BYTES:
                            raise ProjectError("project pixel payloads exceed the safe load limit")
                    else:
                        pending.extend(value.values())
                elif isinstance(value, list):
                    pending.extend(value)
        try:
            canvas = data["canvas"]
            animation = data["animation"]
            project = cls(
                format_version=FORMAT_VERSION,
                name=str(data.get("name", "Untitled")),
                width=int(canvas["width"]),
                height=int(canvas["height"]),
                fps=int(animation.get("fps", 12)),
                loop=bool(animation.get("loop", True)),
            )
            project.layers = [Layer.from_dict(item) for item in data.get("layers", [])]
            project.frames = [
                Frame.from_dict(item, project.width, project.height)
                for item in data.get("frames", [])
            ]
            if int(version) >= 2:
                project.source_assets = [
                    SourceAsset.from_dict(item)
                    for item in data.get("source_assets", [])
                ]
                project.generators = [
                    TransformEmitter.from_dict(item)
                    for item in data.get("generators", [])
                ]
            if int(version) >= 3:
                project.animation_clips = [AnimationClipAsset.from_dict(item) for item in data.get("animation_clips", [])]
                project.particle_emitters = [ParticleEmitter.from_dict(item) for item in data.get("particle_emitters", [])]
            if int(version) >= 5:
                project.resource_compositions = [ResourceComposition.from_dict(item) for item in data.get("resource_compositions", [])]
            if int(version) == 5:
                project.effect_composition_layers = [EffectCompositionLayer.from_dict(item) for item in data.get("effect_composition_layers", [])]
            if int(version) >= 6:
                project.effect_resource_layers = [
                    EffectResourceLayer.from_dict(item, source_version=int(version))
                    for item in data.get("effect_resource_layers", [])
                ]
                project.effect_composition_layers = [item.as_composition_layer() for item in project.effect_resource_layers if item.placement_mode != PLACEMENT_PARTICLE]
                project.particle_emitters = [item.as_particle_emitter() for item in project.effect_resource_layers if item.placement_mode == PLACEMENT_PARTICLE]
                if int(version)>=11:
                    project.effect_layer_groups=[LayerGroup.from_dict(item) for item in data.get("effect_layer_groups",[])]
                    project.effect_root_order=list(data.get("effect_root_order",[])) if isinstance(data.get("effect_root_order",[]),list) else []
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectError(f"invalid project data: {exc}") from exc
        if not project.layers or not project.frames:
            raise ProjectError("project must contain at least one layer and one frame")
        layer_ids = {layer.id for layer in project.layers}
        if len(layer_ids) != len(project.layers):
            raise ProjectError("layer IDs must be unique")
        if len({frame.id for frame in project.frames}) != len(project.frames):
            raise ProjectError("frame IDs must be unique")
        for frame in project.frames:
            unknown = set(frame.layer_pixels) - layer_ids
            if unknown:
                raise ProjectError("frame contains unknown layer IDs")
            missing = layer_ids - set(frame.layer_pixels)
            if missing and int(version) >= 8:
                raise ProjectError("frame is missing layer pixel payloads")
            for layer in project.layers:
                frame.layer_pixels.setdefault(
                    layer.id, empty_pixels(project.width, project.height)
                )
        asset_ids = {asset.id for asset in project.source_assets}
        if len(asset_ids) != len(project.source_assets):
            raise ProjectError("source asset IDs must be unique")
        generator_ids = {generator.id for generator in project.generators}
        if len(generator_ids) != len(project.generators):
            raise ProjectError("generator IDs must be unique")
        for generator in project.generators:
            if generator.settings.source_asset_id not in asset_ids:
                raise ProjectError("generator references an unknown source asset")
            if (
                generator.generated_layer_id is not None
                and generator.generated_layer_id not in layer_ids
            ):
                raise ProjectError("generator references an unknown generated layer")
        clip_ids = {clip.id for clip in project.animation_clips}
        if len(clip_ids) != len(project.animation_clips):
            raise ProjectError("animation clip IDs must be unique")
        emitter_ids = {emitter.id for emitter in project.particle_emitters}
        if len(emitter_ids) != len(project.particle_emitters):
            raise ProjectError("particle emitter IDs must be unique")
        composition_ids={composition.id for composition in project.resource_compositions}
        for emitter in project.particle_emitters:
            valid_ids = clip_ids if emitter.settings.resource_type == "animation_clip" else composition_ids if emitter.settings.resource_type == "resource_composition" else asset_ids
            if emitter.settings.clip_asset_id not in valid_ids:
                raise ProjectError("particle emitter references an unknown animation clip")
            if emitter.generated_layer_id is not None and emitter.generated_layer_id not in layer_ids:
                raise ProjectError("particle emitter references an unknown generated layer")
        if len({c.id for c in project.resource_compositions})!=len(project.resource_compositions):raise ProjectError("resource composition IDs must be unique")
        if len({item.id for item in project.effect_composition_layers}) != len(project.effect_composition_layers):
            raise ProjectError("Composition Layer IDs must be unique")
        for effect_layer in project.effect_composition_layers:
            if effect_layer.resource_composition_id not in composition_ids:
                raise ProjectError("Composition Layer references an unknown Resource Composition")
            if effect_layer.generated_layer_id is not None and effect_layer.generated_layer_id not in layer_ids:
                raise ProjectError("Composition Layer references an unknown generated layer")
        if len({item.id for item in project.effect_resource_layers}) != len(project.effect_resource_layers):
            raise ProjectError("Resource Layer IDs must be unique")
        for resource_layer in project.effect_resource_layers:
            if resource_layer.resource_composition_id and resource_layer.resource_composition_id not in composition_ids:
                raise ProjectError("Resource Layer references an unknown Resource Composition")
            if resource_layer.generated_layer_id is not None and resource_layer.generated_layer_id not in layer_ids:
                raise ProjectError("Resource Layer references an unknown generated layer")
        generated_ids = [
            item.generated_layer_id
            for item in project.effect_resource_layers
            if item.generated_layer_id is not None
        ]
        if len(set(generated_ids)) != len(generated_ids):
            raise ProjectError("Resource Layers must not share a generated layer")
        for composition in project.resource_compositions:
            if len({layer.id for layer in composition.layers}) != len(composition.layers):
                raise ProjectError("composition layer IDs must be unique")
            for layer in composition.layers:
                valid=asset_ids if layer.source_type=="source_asset" else clip_ids
                if layer.source_id not in valid:raise ProjectError("composition layer references an unknown asset")
                if layer.end_frame>=composition.frame_count or layer.source_start_frame<0:raise ProjectError("composition layer range is outside the composition")
                for property_id,track in layer.tracks.items():
                    if property_id!=track.property_id:raise ProjectError("composition track ID does not match its property")
                    if any(key.frame>=composition.frame_count for key in track.keyframes):raise ProjectError("composition keyframe is outside the composition")
        if int(version) <= 5:
            position = {layer.id: index for index, layer in enumerate(project.layers)}
            migrated = [
                EffectResourceLayer.from_composition_layer(
                    item,
                    next((layer.visible for layer in project.layers if layer.id == item.generated_layer_id), True),
                ) for item in project.effect_composition_layers
            ]
            migrated.extend(
                EffectResourceLayer.from_particle_emitter(
                    item,
                    next((layer.visible for layer in project.layers if layer.id == item.generated_layer_id), True),
                ) for item in project.particle_emitters
            )
            project.effect_resource_layers = sorted(
                migrated,
                key=lambda item: position.get(item.generated_layer_id, len(position)),
            )
        if len({item.id for item in project.effect_resource_layers}) != len(project.effect_resource_layers):
            raise ProjectError("Resource Layer IDs must be unique")
        if int(version) >= 6:
            by_id={layer.id:layer for layer in project.layers}
            for item in project.effect_resource_layers:
                if item.generated_layer_id in by_id:by_id[item.generated_layer_id].visible=item.visible
        project.repair_effect_hierarchy()
        return project
