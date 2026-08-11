"""Layer model."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from uuid import uuid4


@dataclass(slots=True)
class Layer:
    """A named compositing layer shared by every animation frame."""

    name: str
    visible: bool = True
    opacity: float = 1.0
    id: str = field(default_factory=lambda: uuid4().hex)
    kind: str = "normal"
    generator_id: str | None = None

    def __post_init__(self) -> None:
        self.opacity = float(self.opacity)
        if not isfinite(self.opacity) or not 0.0 <= self.opacity <= 1.0:
            raise ValueError("layer opacity must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "kind": self.kind,
            "generator_id": self.generator_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Layer":
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "Layer")),
            visible=bool(data.get("visible", True)),
            opacity=float(data.get("opacity", 1.0)),
            kind=str(data.get("kind", "normal")),
            generator_id=(
                None if data.get("generator_id") is None else str(data["generator_id"])
            ),
        )
