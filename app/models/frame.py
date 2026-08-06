"""Animation frame model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import numpy as np
from app.frame_payload_codec import DEFAULT_FRAME_PAYLOAD_CODEC


def empty_pixels(width: int, height: int) -> np.ndarray:
    """Return a transparent RGBA pixel buffer."""
    return np.zeros((height, width, 4), dtype=np.uint8)


@dataclass
class Frame:
    """One animation frame containing a pixel buffer per layer."""

    name: str
    layer_pixels: dict[str, np.ndarray] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layer_pixels": {
                layer_id: DEFAULT_FRAME_PAYLOAD_CODEC.encode(pixels,("project_frame",self.id,layer_id))
                for layer_id, pixels in self.layer_pixels.items()
            },
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], width: int, height: int
    ) -> "Frame":
        raw_layers = data.get("layer_pixels", {})
        if not isinstance(raw_layers, dict):
            raise ValueError("frame layer_pixels must be an object")
        layers: dict[str, np.ndarray] = {}
        for layer_id, raw_pixels in raw_layers.items():
            pixels=DEFAULT_FRAME_PAYLOAD_CODEC.decode(raw_pixels,width,height,("project_frame",str(data["id"]),str(layer_id)))
            layers[str(layer_id)] = pixels
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "Frame")),
            layer_pixels=layers,
        )
