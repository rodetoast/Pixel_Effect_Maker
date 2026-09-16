"""Deterministic animation-clip particle emitter models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any
from uuid import uuid4

from .resource_composition import AnimationTrack, EASINGS
from .blend_mode import BLEND_NORMAL, validate_blend_mode


LIFETIME_SCALE_MAX = 16.0
RGB_MIN = 0
RGB_MAX = 255


@dataclass
class LifetimeScalarModulation:
    """Minimal reusable scalar channel evaluated over one particle lifetime."""

    enabled: bool = False
    start: float = 1.0
    end: float = 1.0
    easing: str = "Linear"

    def validate(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("lifetime scalar enabled must be a boolean")
        start = float(self.start)
        end = float(self.end)
        if not all(math.isfinite(value) for value in (start, end)):
            raise ValueError("lifetime scalar values must be finite")
        if not 0.0 <= start <= LIFETIME_SCALE_MAX or not 0.0 <= end <= LIFETIME_SCALE_MAX:
            raise ValueError(f"lifetime scalar values must be 0..{LIFETIME_SCALE_MAX:g}")
        if self.easing not in EASINGS:
            raise ValueError("unsupported lifetime scalar easing")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"enabled": bool(self.enabled), "start": float(self.start), "end": float(self.end), "easing": self.easing}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "LifetimeScalarModulation":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("lifetime scalar modulation must be an object")
        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("lifetime scalar enabled must be a boolean")
        value = cls(
            enabled=enabled,
            start=float(data.get("start", 1.0)),
            end=float(data.get("end", 1.0)),
            easing=str(data.get("easing", "Linear")),
        )
        value.validate()
        return value


@dataclass
class LifetimeColorModulation:
    """Two-point RGB-only tint modulation over one particle lifetime."""

    enabled: bool = False
    start_rgb: tuple[int, int, int] = (255, 255, 255)
    end_rgb: tuple[int, int, int] = (255, 255, 255)
    easing: str = "Linear"

    def validate(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("lifetime color enabled must be a boolean")
        for name, color in (("start", self.start_rgb), ("end", self.end_rgb)):
            if not isinstance(color, (tuple, list)) or len(color) != 3:
                raise ValueError(f"lifetime color {name} must contain exactly three RGB channels")
            if any(isinstance(channel, bool) or not isinstance(channel, int) or not RGB_MIN <= channel <= RGB_MAX for channel in color):
                raise ValueError(f"lifetime color {name} channels must be integers from {RGB_MIN} to {RGB_MAX}")
        if self.easing not in EASINGS:
            raise ValueError("unsupported lifetime color easing")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "enabled": self.enabled,
            "start_rgb": list(self.start_rgb),
            "end_rgb": list(self.end_rgb),
            "easing": self.easing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "LifetimeColorModulation":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("lifetime color modulation must be an object")
        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("lifetime color enabled must be a boolean")
        start = data.get("start_rgb", (255, 255, 255))
        end = data.get("end_rgb", (255, 255, 255))
        value = cls(enabled, tuple(start) if isinstance(start, (tuple, list)) else start, tuple(end) if isinstance(end, (tuple, list)) else end, str(data.get("easing", "Linear")))
        value.validate()
        return value


MOTION_TRACK_PROPERTIES = {
    "center_x": "motion_center_x", "center_y": "motion_center_y", "center_z": "motion_center_z",
    "radius_start": "motion_radius_start", "radius_end": "motion_radius_end",
    "ellipse_scale_x": "motion_ellipse_scale_x", "ellipse_scale_y": "motion_ellipse_scale_y",
    "start_angle_degrees": "motion_start_angle_degrees", "turns": "motion_turns",
    "phase_spread_degrees": "motion_phase_spread_degrees",
    "orbit_plane_rotation_degrees": "motion_orbit_plane_rotation_degrees",
    "axis_start": "motion_axis_start", "axis_end": "motion_axis_end",
    "perspective_strength": "motion_perspective_strength",
}


@dataclass
class ParticleMotionSettings:
    """Deterministic local particle motion; Resource Layer 2.5D is applied later."""

    mode: str = "linear"
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0
    radius_start: float = 0.0
    radius_end: float = 0.0
    ellipse_scale_x: float = 1.0
    ellipse_scale_y: float = 1.0
    start_angle_degrees: float = 0.0
    turns: float = 1.0
    direction: str = "counter_clockwise"
    phase_spread_degrees: float = 0.0
    orbit_plane_rotation_degrees: float = 0.0
    helix_axis: str = "z"
    axis_start: float = 0.0
    axis_end: float = 0.0
    perspective_strength: float = 0.0
    radius_easing: str = "Linear"
    angle_easing: str = "Linear"
    axis_easing: str = "Linear"
    tracks: dict[str, AnimationTrack] = field(default_factory=dict)
    revision: int = 0

    def validate(self) -> None:
        if self.mode not in {"linear", "orbit", "helix"}: raise ValueError("unsupported particle motion mode")
        if self.direction not in {"clockwise", "counter_clockwise"}: raise ValueError("unsupported particle motion direction")
        if self.helix_axis not in {"x", "y", "z"}: raise ValueError("unsupported helix axis")
        if self.radius_easing not in {"Linear", "Ease In", "Ease Out", "Ease In/Out"}: raise ValueError("unsupported radius easing")
        if self.angle_easing not in {"Linear", "Ease In", "Ease Out", "Ease In/Out"}: raise ValueError("unsupported angle easing")
        if self.axis_easing not in {"Linear", "Ease In", "Ease Out", "Ease In/Out"}: raise ValueError("unsupported axis easing")
        numeric = (
            self.center_x, self.center_y, self.center_z, self.radius_start, self.radius_end,
            self.ellipse_scale_x, self.ellipse_scale_y, self.start_angle_degrees, self.turns,
            self.phase_spread_degrees, self.orbit_plane_rotation_degrees, self.axis_start,
            self.axis_end, self.perspective_strength,
        )
        if not all(math.isfinite(float(value)) for value in numeric): raise ValueError("particle motion values must be finite")
        if self.radius_start < 0 or self.radius_end < 0: raise ValueError("particle motion radius must be non-negative")
        if self.ellipse_scale_x < 0 or self.ellipse_scale_y < 0: raise ValueError("particle motion ellipse scale must be non-negative")
        if not 0.0 <= self.perspective_strength <= 1.0: raise ValueError("particle local perspective must be 0..1")
        for name, track in self.tracks.items():
            expected = MOTION_TRACK_PROPERTIES.get(name)
            if expected is None or track.property_id != expected: raise ValueError("unsupported particle motion track")
            for keyframe in track.keyframes:
                try: number=float(keyframe.value)
                except (TypeError,ValueError) as exc: raise ValueError("particle motion keyframes must be numeric") from exc
                if not math.isfinite(number): raise ValueError("particle motion keyframes must be finite")
                if name in {"radius_start","radius_end","ellipse_scale_x","ellipse_scale_y"} and number<0: raise ValueError("particle motion keyframe must be non-negative")
                if name=="perspective_strength" and not 0<=number<=1: raise ValueError("particle local perspective keyframe must be 0..1")

    def value(self, property_id: str, frame: int) -> float:
        if property_id not in MOTION_TRACK_PROPERTIES: raise ValueError("unsupported particle motion property")
        track = self.tracks.get(property_id)
        return float(track.evaluate(frame)) if track and track.keyframes else float(getattr(self, property_id))

    def set_keyframe(self, property_id: str, frame: int, value: float, easing: str = "Linear"):
        if property_id not in MOTION_TRACK_PROPERTIES: raise ValueError("unsupported particle motion property")
        track = self.tracks.setdefault(property_id, AnimationTrack(MOTION_TRACK_PROPERTIES[property_id], float(getattr(self, property_id))))
        keyframe = track.set_keyframe(frame, float(value), easing); self.revision += 1; return keyframe

    def evaluated(self, frame: int) -> "ParticleMotionSettings":
        values = {name: self.value(name, frame) for name in MOTION_TRACK_PROPERTIES}
        return ParticleMotionSettings(**values, mode=self.mode, direction=self.direction, helix_axis=self.helix_axis,
            radius_easing=self.radius_easing, angle_easing=self.angle_easing, axis_easing=self.axis_easing)

    def reset_base(self) -> None:
        defaults = ParticleMotionSettings()
        for name in MOTION_TRACK_PROPERTIES: setattr(self, name, getattr(defaults, name))
        self.mode=defaults.mode; self.direction=defaults.direction; self.helix_axis=defaults.helix_axis
        self.radius_easing=defaults.radius_easing; self.angle_easing=defaults.angle_easing; self.axis_easing=defaults.axis_easing
        self.revision += 1

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "mode": self.mode, "center": [self.center_x, self.center_y, self.center_z],
            "radius_start": self.radius_start, "radius_end": self.radius_end,
            "ellipse_scale": [self.ellipse_scale_x, self.ellipse_scale_y],
            "start_angle_degrees": self.start_angle_degrees, "turns": self.turns,
            "direction": self.direction, "phase_spread_degrees": self.phase_spread_degrees,
            "orbit_plane_rotation_degrees": self.orbit_plane_rotation_degrees,
            "helix_axis": self.helix_axis, "axis_start": self.axis_start, "axis_end": self.axis_end,
            "perspective_strength": self.perspective_strength,
            "easing": {"radius": self.radius_easing, "angle": self.angle_easing, "axis": self.axis_easing},
            "tracks": {name: track.to_dict() for name, track in self.tracks.items() if track.keyframes},
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ParticleMotionSettings":
        if not data: return cls()
        center=data.get("center",(0.0,0.0,0.0)); ellipse=data.get("ellipse_scale",(1.0,1.0)); easing=data.get("easing",{})
        if not isinstance(center,(list,tuple)) or len(center)!=3: raise ValueError("particle motion center must contain three numbers")
        if not isinstance(ellipse,(list,tuple)) or len(ellipse)!=2: raise ValueError("particle ellipse scale must contain two numbers")
        if not isinstance(easing,dict): raise ValueError("particle motion easing must be an object")
        value=cls(mode=str(data.get("mode","linear")),center_x=float(center[0]),center_y=float(center[1]),center_z=float(center[2]),
            radius_start=float(data.get("radius_start",0)),radius_end=float(data.get("radius_end",0)),
            ellipse_scale_x=float(ellipse[0]),ellipse_scale_y=float(ellipse[1]),start_angle_degrees=float(data.get("start_angle_degrees",0)),
            turns=float(data.get("turns",1)),direction=str(data.get("direction","counter_clockwise")),
            phase_spread_degrees=float(data.get("phase_spread_degrees",0)),orbit_plane_rotation_degrees=float(data.get("orbit_plane_rotation_degrees",0)),
            helix_axis=str(data.get("helix_axis","z")),axis_start=float(data.get("axis_start",0)),axis_end=float(data.get("axis_end",0)),
            perspective_strength=float(data.get("perspective_strength",0)),radius_easing=str(easing.get("radius","Linear")),
            angle_easing=str(easing.get("angle","Linear")),axis_easing=str(easing.get("axis","Linear")),
            tracks={name:AnimationTrack.from_dict(track) for name,track in data.get("tracks",{}).items()},revision=int(data.get("revision",0)))
        value.validate(); return value


@dataclass
class ParticleEmitterSettings:
    clip_asset_id: str
    resource_type: str = "animation_clip"
    output_frame_count: int = 24
    start_frame: int = 0
    emission_mode: str = "burst"
    particle_count_min: int = 8
    particle_count_max: int = 8
    emission_duration: int = 12
    spawn_shape: str = "point"
    origin_x: float = 32.0
    origin_y: float = 32.0
    line_end_x: float = 48.0
    line_end_y: float = 32.0
    radius: float = 16.0
    start_angle: float = 0.0
    end_angle: float = 360.0
    box_width: float = 32.0
    box_height: float = 32.0
    direction_mode: str = "fixed"
    direction_degrees: float = -90.0
    direction_spread_degrees: float = 20.0
    speed_min: float = 1.0
    speed_max: float = 2.0
    lifetime_min: int = 12
    lifetime_max: int = 20
    scale_min: float = 1.0
    scale_max: float = 1.0
    rotation_min: float = 0.0
    rotation_max: float = 0.0
    angular_velocity_min: float = 0.0
    angular_velocity_max: float = 0.0
    start_delay_min: int = 0
    start_delay_max: int = 0
    clip_speed_min: float = 1.0
    clip_speed_max: float = 1.0
    random_start_frame: bool = False
    opacity_start: float = 1.0
    opacity_end: float = 0.0
    easing: str = "Linear"
    blend_mode: str = BLEND_NORMAL
    seed: int = 0
    scale_over_lifetime: LifetimeScalarModulation = field(default_factory=LifetimeScalarModulation)
    color_over_lifetime: LifetimeColorModulation = field(default_factory=LifetimeColorModulation)
    motion: ParticleMotionSettings = field(default_factory=ParticleMotionSettings)

    def __post_init__(self) -> None:
        self._normalize_clip_speed_range()

    def _normalize_clip_speed_range(self) -> None:
        """Keep legacy/direct inputs valid, preferring the supplied minimum."""
        if self.clip_speed_min > self.clip_speed_max:
            self.clip_speed_max = self.clip_speed_min

    def validate(self) -> None:
        self._normalize_clip_speed_range()
        if not self.clip_asset_id: raise ValueError("an animation clip is required")
        if self.resource_type not in {"animation_clip", "source_asset", "resource_composition"}: raise ValueError("unsupported particle resource type")
        if not 1 <= self.output_frame_count <= 512: raise ValueError("output frame count must be 1..512")
        if self.emission_mode not in {"burst", "over_time"}: raise ValueError("unsupported emission mode")
        if self.spawn_shape not in {"point", "line", "circle", "box"}: raise ValueError("unsupported spawn shape")
        if self.direction_mode not in {"fixed", "radial_outward"}: raise ValueError("unsupported direction mode")
        ranges = ((self.particle_count_min, self.particle_count_max), (self.speed_min, self.speed_max),
                  (self.lifetime_min, self.lifetime_max), (self.scale_min, self.scale_max),
                  (self.rotation_min, self.rotation_max), (self.angular_velocity_min, self.angular_velocity_max),
                  (self.start_delay_min, self.start_delay_max), (self.clip_speed_min, self.clip_speed_max))
        if any(low > high for low, high in ranges): raise ValueError("random range minimum must not exceed maximum")
        if self.particle_count_min < 0 or self.particle_count_max > 4096: raise ValueError("particle count must be 0..4096")
        if self.lifetime_min < 1 or self.start_delay_min < 0: raise ValueError("invalid lifetime or start delay")
        if self.scale_min <= 0 or self.clip_speed_min <= 0: raise ValueError("scale and clip speed must be positive")
        if not (0 <= self.opacity_start <= 1 and 0 <= self.opacity_end <= 1): raise ValueError("opacity must be 0..1")
        if self.easing not in EASINGS: raise ValueError("unsupported particle alpha easing")
        self.blend_mode = validate_blend_mode(self.blend_mode)
        self.scale_over_lifetime.validate()
        self.color_over_lifetime.validate()
        self.motion.validate()

    def to_dict(self) -> dict[str, Any]:
        self._normalize_clip_speed_range()
        value=asdict(self); value["scale_over_lifetime"]=self.scale_over_lifetime.to_dict(); value["color_over_lifetime"]=self.color_over_lifetime.to_dict(); value["motion"]=self.motion.to_dict(); return value

    @property
    def resource_id(self) -> str:
        return self.clip_asset_id

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParticleEmitterSettings":
        values = dict(data)
        if "resource_id" in values and "clip_asset_id" not in values:
            values["clip_asset_id"] = values.pop("resource_id")
        values["scale_over_lifetime"] = LifetimeScalarModulation.from_dict(values.get("scale_over_lifetime"))
        values["color_over_lifetime"] = LifetimeColorModulation.from_dict(values.get("color_over_lifetime"))
        values["motion"] = ParticleMotionSettings.from_dict(values.get("motion"))
        value = cls(**values); value.validate(); return value


@dataclass(frozen=True)
class ParticleInstance:
    birth_frame: int
    lifetime: int
    start_x: float
    start_y: float
    velocity_x: float
    velocity_y: float
    scale: float
    rotation: float
    angular_velocity: float
    clip_start_frame: int
    clip_playback_speed: float
    random_seed: int
    particle_id: int = 0
    motion_phase_degrees: float = 0.0
    motion_phase_unit: float = 0.0


@dataclass
class ParticleEmitter:
    name: str
    settings: ParticleEmitterSettings
    generated_layer_id: str | None = None
    id: str = field(default_factory=lambda: uuid4().hex)
    generator_type: str = "particle_emitter"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "generator_type": self.generator_type,
                "generated_layer_id": self.generated_layer_id, "settings": self.settings.to_dict()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParticleEmitter":
        if data.get("generator_type") != "particle_emitter": raise ValueError("unsupported particle emitter type")
        return cls(id=str(data["id"]), name=str(data.get("name", "Particle Emitter")),
                   generated_layer_id=None if data.get("generated_layer_id") is None else str(data["generated_layer_id"]),
                   settings=ParticleEmitterSettings.from_dict(data["settings"]))
