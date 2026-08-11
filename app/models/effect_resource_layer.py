"""Unified Resource Layer model for Effect Composition format v6."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from typing import Any
from uuid import uuid4

from .effect_composition_layer import EffectCompositionLayer
from .particle_emitter import ParticleEmitter, ParticleEmitterSettings
from .resource_composition import AnimationTrack

PLACEMENT_SINGLE = "single"
PLACEMENT_PARTICLE = "particle"
PLACEMENT_MODES = {PLACEMENT_SINGLE, PLACEMENT_PARTICLE}

TRANSFORM_TRACK_PROPERTIES = (
    "position_x", "position_y", "position_z", "rotation_x", "rotation_y",
    "rotation_z", "scale_x", "scale_y", "opacity", "perspective_strength",
)


@dataclass
class EffectLayerTransform3D:
    """Animatable flat-plane transform shared by both placement modes."""

    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    opacity: float = 1.0
    pivot_x: float = 0.0
    pivot_y: float = 0.0
    perspective_strength: float = 0.0
    tracks: dict[str, AnimationTrack] = field(default_factory=dict)
    revision: int = 0

    def __post_init__(self) -> None:
        for name in TRANSFORM_TRACK_PROPERTIES:
            setattr(self, name, float(getattr(self, name)))
        self.pivot_x = float(self.pivot_x); self.pivot_y = float(self.pivot_y)
        numeric_values = [
            *(getattr(self, name) for name in TRANSFORM_TRACK_PROPERTIES),
            self.pivot_x,
            self.pivot_y,
        ]
        if not all(isfinite(value) for value in numeric_values):
            raise ValueError("Resource Layer transform values must be finite")
        self.opacity = max(0.0, min(1.0, self.opacity))
        self.perspective_strength = max(0.0, min(1.0, self.perspective_strength))
        self.scale_x = max(0.01, self.scale_x); self.scale_y = max(0.01, self.scale_y)
        for name, track in self.tracks.items():
            if name not in TRANSFORM_TRACK_PROPERTIES or track.property_id != name:
                raise ValueError("unsupported Resource Layer transform track")

    def value(self, property_id: str, frame: int) -> float:
        if property_id not in TRANSFORM_TRACK_PROPERTIES:
            raise ValueError("unsupported Resource Layer transform property")
        track = self.tracks.get(property_id)
        return float(track.evaluate(frame)) if track and track.keyframes else float(getattr(self, property_id))

    def add_track(self, property_id: str) -> AnimationTrack:
        if property_id not in TRANSFORM_TRACK_PROPERTIES:
            raise ValueError("unsupported Resource Layer transform property")
        return self.tracks.setdefault(property_id, AnimationTrack(property_id, float(getattr(self, property_id))))

    def set_keyframe(self, property_id: str, frame: int, value: float, easing: str = "Linear"):
        keyframe = self.add_track(property_id).set_keyframe(frame, float(value), easing)
        self.revision += 1
        return keyframe

    def reset_base(self) -> None:
        for name in TRANSFORM_TRACK_PROPERTIES:
            setattr(self, name, 1.0 if name in {"scale_x", "scale_y", "opacity"} else 0.0)
        self.pivot_x = self.pivot_y = 0.0
        self.revision += 1

    def evaluated(self, frame: int) -> "EffectLayerTransform3D":
        values = {name: self.value(name, frame) for name in TRANSFORM_TRACK_PROPERTIES}
        return EffectLayerTransform3D(**values, pivot_x=self.pivot_x, pivot_y=self.pivot_y)

    def is_identity(self, frame: int | None = None) -> bool:
        value = self if frame is None else self.evaluated(frame)
        return (
            value.position_x == value.position_y == value.position_z == 0.0
            and value.rotation_x == value.rotation_y == value.rotation_z == 0.0
            and value.scale_x == value.scale_y == value.opacity == 1.0
            and value.perspective_strength == 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": [self.position_x, self.position_y, self.position_z],
            "rotation": [self.rotation_x, self.rotation_y, self.rotation_z],
            "scale": [self.scale_x, self.scale_y], "opacity": self.opacity,
            "pivot": [self.pivot_x, self.pivot_y],
            "perspective_strength": self.perspective_strength,
            "tracks": {name: track.to_dict() for name, track in self.tracks.items() if track.keyframes},
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EffectLayerTransform3D":
        if not data:
            return cls()
        position = data.get("position", (0.0, 0.0, 0.0)); rotation = data.get("rotation", (0.0, 0.0, 0.0))
        scale = data.get("scale", (1.0, 1.0)); pivot = data.get("pivot", (0.0, 0.0))
        return cls(
            position_x=float(position[0]), position_y=float(position[1]), position_z=float(position[2]),
            rotation_x=float(rotation[0]), rotation_y=float(rotation[1]), rotation_z=float(rotation[2]),
            scale_x=float(scale[0]), scale_y=float(scale[1]), opacity=float(data.get("opacity", 1.0)),
            pivot_x=float(pivot[0]), pivot_y=float(pivot[1]),
            perspective_strength=float(data.get("perspective_strength", 0.0)),
            tracks={name: AnimationTrack.from_dict(track) for name, track in data.get("tracks", {}).items()},
            revision=int(data.get("revision", 0)),
        )


@dataclass
class EffectResourceLayer:
    """One Resource Composition with two preserved placement configurations."""

    name: str
    resource_composition_id: str
    placement_mode: str = PLACEMENT_SINGLE
    visible: bool = True
    start_frame: int = 0
    end_frame: int = 0
    resource_start_frame: int = 0
    playback_mode: str = "loop"
    playback_speed: float = 1.0
    generated_layer_id: str | None = None
    single_settings: EffectCompositionLayer | None = None
    particle_settings: ParticleEmitterSettings | None = None
    layer_transform: EffectLayerTransform3D = field(default_factory=EffectLayerTransform3D)
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if self.placement_mode not in PLACEMENT_MODES:
            raise ValueError("unsupported Resource Layer placement mode")
        self.playback_speed = float(self.playback_speed)
        if (
            self.start_frame < 0
            or self.end_frame < self.start_frame
            or self.resource_start_frame < 0
        ):
            raise ValueError("invalid Resource Layer frame range")
        if self.playback_mode not in {"loop", "hold", "once"}:
            raise ValueError("unsupported Resource Layer playback mode")
        if not isfinite(self.playback_speed) or self.playback_speed <= 0.0:
            raise ValueError("Resource Layer playback speed must be finite and positive")
        if self.single_settings is None:
            self.single_settings = EffectCompositionLayer(
                self.name, self.resource_composition_id,
                start_frame=self.start_frame, end_frame=self.end_frame,
                generated_layer_id=self.generated_layer_id, id=self.id,
            )
        if self.particle_settings is None:
            self.particle_settings = ParticleEmitterSettings(
                self.resource_composition_id,
                resource_type="resource_composition",
                start_frame=self.resource_start_frame,
            )
        self.sync_active_adapter()

    def sync_active_adapter(self) -> None:
        """Keep compatibility adapters aligned without discarding inactive data."""
        assert self.single_settings is not None
        self.single_settings.id = self.id
        self.single_settings.name = self.name
        self.single_settings.resource_composition_id = self.resource_composition_id
        self.single_settings.start_frame = self.start_frame
        self.single_settings.end_frame = self.end_frame
        self.single_settings.generated_layer_id = self.generated_layer_id

    def as_composition_layer(self) -> EffectCompositionLayer:
        self.sync_active_adapter()
        assert self.single_settings is not None
        return self.single_settings

    def as_particle_emitter(self) -> ParticleEmitter:
        assert self.particle_settings is not None
        return ParticleEmitter(
            name=self.name, settings=self.particle_settings,
            generated_layer_id=self.generated_layer_id, id=self.id,
        )

    def set_placement_mode(self, mode: str) -> None:
        if mode not in PLACEMENT_MODES:
            raise ValueError("unsupported Resource Layer placement mode")
        self.placement_mode = mode

    # Compatibility accessors keep existing renderer/gizmo integrations thin.
    @property
    def layer_type(self): return "resource_layer"
    @property
    def generator_type(self): return "resource_layer"
    @property
    def settings(self): return self.particle_settings
    @settings.setter
    def settings(self, value): self.particle_settings = value
    @property
    def start_x(self): return self.single_settings.start_x
    @start_x.setter
    def start_x(self, value): self.single_settings.start_x = value
    @property
    def start_y(self): return self.single_settings.start_y
    @start_y.setter
    def start_y(self, value): self.single_settings.start_y = value
    @property
    def end_x(self): return self.single_settings.end_x
    @end_x.setter
    def end_x(self, value): self.single_settings.end_x = value
    @property
    def end_y(self): return self.single_settings.end_y
    @end_y.setter
    def end_y(self, value): self.single_settings.end_y = value

    def to_dict(self) -> dict[str, Any]:
        self.sync_active_adapter()
        return {
            "id": self.id, "name": self.name, "visible": self.visible,
            "resource_composition_id": self.resource_composition_id,
            "start_frame": self.start_frame, "end_frame": self.end_frame,
            "resource_start_frame": self.resource_start_frame,
            "playback_mode": self.playback_mode, "playback_speed": self.playback_speed,
            "placement_mode": self.placement_mode,
            "generated_layer_id": self.generated_layer_id,
            "single_settings": self.single_settings.to_dict(),
            "particle_settings": self.particle_settings.to_dict(),
            "layer_transform": self.layer_transform.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EffectResourceLayer":
        single_data = data.get("single_settings")
        particle_data = data.get("particle_settings")
        return cls(
            id=str(data["id"]), name=str(data.get("name", "Resource Layer")),
            visible=bool(data.get("visible", True)),
            resource_composition_id=str(data.get("resource_composition_id", "")),
            start_frame=int(data.get("start_frame", 0)), end_frame=int(data.get("end_frame", 0)),
            resource_start_frame=int(data.get("resource_start_frame", 0)),
            playback_mode=str(data.get("playback_mode", "loop")),
            playback_speed=float(data.get("playback_speed", 1.0)),
            placement_mode=str(data.get("placement_mode", PLACEMENT_SINGLE)),
            generated_layer_id=None if data.get("generated_layer_id") is None else str(data["generated_layer_id"]),
            single_settings=None if not single_data else (
                EffectCompositionLayer.from_dict(single_data)
                if single_data.get("resource_composition_id") else EffectCompositionLayer(**single_data)
            ),
            particle_settings=None if not particle_data else ParticleEmitterSettings.from_dict(particle_data),
            layer_transform=EffectLayerTransform3D.from_dict(data.get("layer_transform")),
        )

    @classmethod
    def from_composition_layer(cls, value: EffectCompositionLayer, visible: bool = True) -> "EffectResourceLayer":
        return cls(
            id=value.id, name=value.name, visible=visible,
            resource_composition_id=value.resource_composition_id,
            start_frame=value.start_frame, end_frame=value.end_frame,
            generated_layer_id=value.generated_layer_id,
            placement_mode=PLACEMENT_SINGLE, single_settings=deepcopy(value),
        )

    @classmethod
    def from_particle_emitter(cls, value: ParticleEmitter, visible: bool = True) -> "EffectResourceLayer":
        resource_id = value.settings.resource_id if value.settings.resource_type == "resource_composition" else ""
        single = EffectCompositionLayer(
            value.name, resource_id, start_frame=value.settings.start_frame,
            end_frame=value.settings.start_frame + value.settings.output_frame_count - 1,
            generated_layer_id=value.generated_layer_id, id=value.id,
        )
        return cls(
            id=value.id, name=value.name, visible=visible,
            resource_composition_id=resource_id,
            start_frame=value.settings.start_frame,
            end_frame=value.settings.start_frame + value.settings.output_frame_count - 1,
            resource_start_frame=value.settings.start_frame,
            generated_layer_id=value.generated_layer_id,
            placement_mode=PLACEMENT_PARTICLE,
            single_settings=single, particle_settings=deepcopy(value.settings),
        )
