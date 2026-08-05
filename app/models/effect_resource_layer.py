"""Unified Resource Layer model for Effect Composition format v6."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .effect_composition_layer import EffectCompositionLayer
from .particle_emitter import ParticleEmitter, ParticleEmitterSettings

PLACEMENT_SINGLE = "single"
PLACEMENT_PARTICLE = "particle"
PLACEMENT_MODES = {PLACEMENT_SINGLE, PLACEMENT_PARTICLE}


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
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        if self.placement_mode not in PLACEMENT_MODES:
            raise ValueError("unsupported Resource Layer placement mode")
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
