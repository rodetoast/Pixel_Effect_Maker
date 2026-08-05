"""A Resource Composition placed directly in the Effect Composition."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class EffectCompositionLayer:
    name: str
    resource_composition_id: str
    start_x: float = 32.0
    start_y: float = 32.0
    end_x: float = 32.0
    end_y: float = 32.0
    start_frame: int = 0
    end_frame: int = 0
    generated_layer_id: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)
    # Keep the legacy serialized discriminator while user-facing terminology
    # changes to Composition Layer.
    layer_type: str = "animation_clip"

    def validate(self) -> None:
        if not self.resource_composition_id:
            raise ValueError("a Resource Composition is required")
        if self.start_frame < 0 or self.end_frame < self.start_frame:
            raise ValueError("invalid Composition Layer frame range")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EffectCompositionLayer":
        values = dict(data)
        values.setdefault("layer_type", "animation_clip")
        value = cls(**values)
        if value.layer_type != "animation_clip":
            raise ValueError("unsupported Composition Layer type")
        value.validate()
        return value
