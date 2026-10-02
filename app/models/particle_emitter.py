"""Deterministic animation-clip particle emitter models."""

from __future__ import annotations

from dataclasses import InitVar, asdict, dataclass, field, replace
import math
from typing import Any
from uuid import uuid4

from .resource_composition import AnimationTrack, EASINGS
from .blend_mode import BLEND_NORMAL, validate_blend_mode


LIFETIME_SCALE_MAX = 16.0
GRAVITY_STRENGTH_MAX = 1024.0
DRAG_STRENGTH_MAX = 10.0
NOISE_STRENGTH_MAX = 4096.0
NOISE_FREQUENCY_MAX = 1.0
EMISSION_ONE_SHOT = "one_shot"
EMISSION_CYCLIC_STEADY = "cyclic_steady"
EMISSION_PERIOD_MAX = 512
CYCLIC_ACTIVE_COPY_LIMIT = 4096
RGB_MIN = 0
RGB_MAX = 255
LIFETIME_POINT_MAX = 8
TRAIL_DURATION_MAX = 240
TRAIL_STAMP_LIMIT = 8192


@dataclass
class ParticleTrailSettings:
    """History-free local sprite afterimages, not ribbon/world-history data."""
    enabled: bool = False
    duration_frames: int = 12
    sample_interval_frames: int = 2
    opacity: float = .75

    def validate(self):
        if not isinstance(self.enabled, bool): raise ValueError("trail enabled must be a boolean")
        if type(self.duration_frames) is not int or not 2 <= self.duration_frames <= TRAIL_DURATION_MAX:
            raise ValueError("trail duration must be an integer in 2..240")
        if type(self.sample_interval_frames) is not int or not 1 <= self.sample_interval_frames < self.duration_frames:
            raise ValueError("trail interval must be an integer in 1..duration-1")
        if isinstance(self.opacity, bool) or not isinstance(self.opacity, (float, int)) or not math.isfinite(self.opacity) or not 0 <= self.opacity <= 1:
            raise ValueError("trail opacity must be finite in 0..1")

    @property
    def sample_count(self): return (self.duration_frames-1)//self.sample_interval_frames
    @property
    def delta_max(self): return self.sample_count*self.sample_interval_frames if self.enabled else 0

    def to_dict(self):
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if data is None:return cls()
        if not isinstance(data, dict):raise ValueError("trail settings must be an object")
        try:value=cls(**data)
        except TypeError as error:raise ValueError("invalid trail settings") from error
        value.validate();return value


@dataclass(frozen=True)
class LifetimeScalarPoint:
    time: float
    value: float
    easing_to_next: str = "Linear"


@dataclass(frozen=True)
class LifetimeColorPoint:
    time: float
    rgb: tuple[int, int, int]
    easing_to_next: str = "Linear"

    def __post_init__(self):
        if isinstance(self.rgb, list): object.__setattr__(self, "rgb", tuple(self.rgb))


def validate_lifetime_points(points) -> None:
    if not isinstance(points, (tuple, list)) or not 2 <= len(points) <= LIFETIME_POINT_MAX:
        raise ValueError("lifetime curve requires 2..8 points")
    previous = -1.0
    for point in points:
        if not isinstance(point, (LifetimeScalarPoint, LifetimeColorPoint)):
            raise ValueError("invalid lifetime point type")
        if isinstance(point.time, bool) or not isinstance(point.time, (int, float)) or not math.isfinite(point.time):
            raise ValueError("lifetime point time must be finite")
        if not 0 <= point.time <= 1 or point.time <= previous:
            raise ValueError("lifetime point times must be strictly increasing in 0..1")
        if not isinstance(point.easing_to_next, str) or point.easing_to_next not in EASINGS:
            raise ValueError("unsupported lifetime segment easing")
        previous = point.time
    if points[0].time != 0 or points[-1].time != 1:
        raise ValueError("lifetime curve requires endpoints at 0 and 1")


@dataclass(init=False)
class LifetimeScalarModulation:
    """Canonical bounded points; legacy accessors edit those same points."""

    enabled: bool = False
    points: tuple[LifetimeScalarPoint, ...] = ()

    def __init__(self, enabled=False, start=1.0, end=1.0, easing="Linear", *, points=None):
        self.enabled = enabled
        self.points = tuple(points) if points is not None else (LifetimeScalarPoint(0.0, start, easing), LifetimeScalarPoint(1.0, end))

    @property
    def start(self): return self.points[0].value
    @start.setter
    def start(self, value): self.points = (replace(self.points[0], value=value), *self.points[1:])
    @property
    def end(self): return self.points[-1].value
    @end.setter
    def end(self, value): self.points = (*self.points[:-1], replace(self.points[-1], value=value))
    @property
    def easing(self): return self.points[0].easing_to_next
    @easing.setter
    def easing(self, value): self.points = (replace(self.points[0], easing_to_next=value), *self.points[1:])

    def validate(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("lifetime scalar enabled must be a boolean")
        validate_lifetime_points(self.points)
        for point in self.points:
            if not isinstance(point, LifetimeScalarPoint) or isinstance(point.value, bool) or not isinstance(point.value, (int, float)) or not math.isfinite(point.value) or not 0 <= point.value <= LIFETIME_SCALE_MAX:
                raise ValueError(f"lifetime scalar values must be finite in 0..{LIFETIME_SCALE_MAX:g}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"enabled": self.enabled, "points": [asdict(point) for point in self.points]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "LifetimeScalarModulation":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("lifetime scalar modulation must be an object")
        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("lifetime scalar enabled must be a boolean")
        if "points" in data:
            if any(key in data for key in ("start", "end", "easing")):
                raise ValueError("ambiguous lifetime scalar representation")
            raw = data["points"]
            if not isinstance(raw, list): raise ValueError("lifetime points must be an array")
            try: value = cls(enabled, points=tuple(LifetimeScalarPoint(**point) for point in raw))
            except (TypeError, KeyError) as error: raise ValueError("invalid scalar point") from error
            value.validate()
            return value
        value = cls(
            enabled=enabled,
            start=float(data.get("start", 1.0)),
            end=float(data.get("end", 1.0)),
            easing=str(data.get("easing", "Linear")),
        )
        value.validate()
        return value


@dataclass(init=False)
class LifetimeColorModulation:
    """Bounded encoded-sRGB tint points, never containing alpha."""

    enabled: bool = False
    points: tuple[LifetimeColorPoint, ...] = ()

    def __init__(self, enabled=False, start_rgb=(255,255,255), end_rgb=(255,255,255), easing="Linear", *, points=None):
        self.enabled = enabled
        self.points = tuple(points) if points is not None else (LifetimeColorPoint(0.0, start_rgb, easing), LifetimeColorPoint(1.0, end_rgb))

    @property
    def start_rgb(self): return self.points[0].rgb
    @start_rgb.setter
    def start_rgb(self, value): self.points = (replace(self.points[0], rgb=value), *self.points[1:])
    @property
    def end_rgb(self): return self.points[-1].rgb
    @end_rgb.setter
    def end_rgb(self, value): self.points = (*self.points[:-1], replace(self.points[-1], rgb=value))
    @property
    def easing(self): return self.points[0].easing_to_next
    @easing.setter
    def easing(self, value): self.points = (replace(self.points[0], easing_to_next=value), *self.points[1:])

    def validate(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("lifetime color enabled must be a boolean")
        validate_lifetime_points(self.points)
        for point in self.points:
            if not isinstance(point, LifetimeColorPoint): raise ValueError("invalid lifetime color point")
            name, color = "point", point.rgb
            if not isinstance(color, (tuple, list)) or len(color) != 3:
                raise ValueError(f"lifetime color {name} must contain exactly three RGB channels")
            if any(isinstance(channel, bool) or not isinstance(channel, int) or not RGB_MIN <= channel <= RGB_MAX for channel in color):
                raise ValueError(f"lifetime color {name} channels must be integers from {RGB_MIN} to {RGB_MAX}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "enabled": self.enabled,
            "points": [{"time": p.time, "rgb": list(p.rgb), "easing_to_next": p.easing_to_next} for p in self.points],
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
        if "points" in data:
            if any(key in data for key in ("start_rgb", "end_rgb", "easing")):
                raise ValueError("ambiguous lifetime color representation")
            raw = data["points"]
            if not isinstance(raw, list): raise ValueError("lifetime points must be an array")
            try:
                value = cls(enabled, points=tuple(LifetimeColorPoint(p["time"], tuple(p["rgb"]), p.get("easing_to_next", "Linear")) for p in raw))
                if any(set(p) - {"time", "rgb", "easing_to_next"} for p in raw): raise ValueError("RGB points cannot contain alpha or unknown fields")
            except (TypeError, KeyError) as error: raise ValueError("invalid RGB point") from error
            value.validate()
            return value
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
    opacity_start: InitVar[float] = 1.0
    opacity_end: InitVar[float] = 0.0
    easing: InitVar[str] = "Linear"
    blend_mode: str = BLEND_NORMAL
    gravity_enabled: bool = False
    gravity_strength: float = 0.0
    drag_enabled: bool = False
    drag_strength: float = 0.0
    noise_enabled: bool = False
    noise_strength: float = 1.0
    noise_frequency: float = 0.1
    seed: int = 0
    scale_over_lifetime: LifetimeScalarModulation = field(default_factory=LifetimeScalarModulation)
    color_over_lifetime: LifetimeColorModulation = field(default_factory=LifetimeColorModulation)
    motion: ParticleMotionSettings = field(default_factory=ParticleMotionSettings)
    emission_cycle_mode: str = EMISSION_ONE_SHOT
    emission_period_frames: int = 24
    opacity_over_lifetime: LifetimeScalarModulation | None = None
    trail: ParticleTrailSettings = field(default_factory=ParticleTrailSettings)

    def __post_init__(self, opacity_start, opacity_end, easing) -> None:
        if self.opacity_over_lifetime is None:
            self.opacity_over_lifetime = LifetimeScalarModulation(True, opacity_start, opacity_end, easing)
        self._normalize_clip_speed_range()

    def _normalize_clip_speed_range(self) -> None:
        """Keep legacy/direct inputs valid, preferring the supplied minimum."""
        if self.clip_speed_min > self.clip_speed_max:
            self.clip_speed_max = self.clip_speed_min

    def validate(self) -> None:
        self._normalize_clip_speed_range()
        self.trail.validate()
        if not isinstance(self.emission_cycle_mode, str) or self.emission_cycle_mode not in {EMISSION_ONE_SHOT, EMISSION_CYCLIC_STEADY}:
            raise ValueError("unsupported emission cycle mode")
        if type(self.emission_period_frames) is not int or not 1 <= self.emission_period_frames <= EMISSION_PERIOD_MAX:
            raise ValueError("emission period must be an integer in 1..512")
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
        self.opacity_over_lifetime.validate()
        if not self.opacity_over_lifetime.enabled or any(p.value > 1 for p in self.opacity_over_lifetime.points): raise ValueError("opacity curve must be enabled with values in 0..1")
        self.blend_mode = validate_blend_mode(self.blend_mode)
        if not isinstance(self.gravity_enabled, bool): raise ValueError("particle gravity enabled must be a boolean")
        if not math.isfinite(float(self.gravity_strength)): raise ValueError("particle gravity strength must be finite")
        if abs(float(self.gravity_strength)) > GRAVITY_STRENGTH_MAX: raise ValueError(f"particle gravity strength must be -{GRAVITY_STRENGTH_MAX:g}..{GRAVITY_STRENGTH_MAX:g}")
        if not isinstance(self.drag_enabled, bool): raise ValueError("particle drag enabled must be a boolean")
        if not math.isfinite(float(self.drag_strength)) or not 0.0 <= float(self.drag_strength) <= DRAG_STRENGTH_MAX: raise ValueError(f"particle drag strength must be 0..{DRAG_STRENGTH_MAX:g}")
        if not isinstance(self.noise_enabled, bool): raise ValueError("particle noise enabled must be a boolean")
        if not math.isfinite(float(self.noise_strength)) or not 0.0 <= float(self.noise_strength) <= NOISE_STRENGTH_MAX: raise ValueError(f"particle noise strength must be 0..{NOISE_STRENGTH_MAX:g}")
        if not math.isfinite(float(self.noise_frequency)) or not 0.0 <= float(self.noise_frequency) <= NOISE_FREQUENCY_MAX: raise ValueError(f"particle noise frequency must be 0..{NOISE_FREQUENCY_MAX:g}")
        self.scale_over_lifetime.validate()
        self.color_over_lifetime.validate()
        self.motion.validate()
        if self.emission_cycle_mode == EMISSION_CYCLIC_STEADY:
            for name in ("start_frame", "emission_duration", "particle_count_min", "particle_count_max", "lifetime_min", "lifetime_max", "start_delay_min", "start_delay_max"):
                if type(getattr(self, name)) is not int:
                    raise ValueError("cyclic timing and counts must be integers")
            if self.start_frame < 0 or self.emission_duration < 1:
                raise ValueError("invalid cyclic start or duration")
            spread = max(0, self.emission_duration - 1) if self.emission_mode == "over_time" and self.particle_count_max > 1 else 0
            if self.particle_count_max and spread + self.start_delay_max >= self.emission_period_frames:
                raise ValueError("cyclic birth offset must be inside the period; increase period or reduce duration/delay")
            if self.cyclic_active_copy_bound() > CYCLIC_ACTIVE_COPY_LIMIT:
                raise ValueError("cyclic configuration exceeds 4096 active particles; increase period or reduce count/lifetime")
        if self.trail.enabled and self.trail_stamp_bound() > TRAIL_STAMP_LIMIT:
            raise ValueError("trail configuration exceeds 8192 trail samples; increase interval or reduce duration/count/lifetime/cyclic overlap")

    def cyclic_active_copy_bound(self) -> int:
        """Worst-case copies: each integer lifetime spans at most ceil(L/P) births."""
        lifetime = self.lifetime_max + self.trail.delta_max
        return self.particle_count_max * ((lifetime + self.emission_period_frames - 1) // self.emission_period_frames)

    def trail_stamp_bound(self) -> int:
        copies = self.cyclic_active_copy_bound() if self.emission_cycle_mode == EMISSION_CYCLIC_STEADY else self.particle_count_max
        return copies*self.trail.sample_count if self.trail.enabled else 0

    def to_dict(self) -> dict[str, Any]:
        self._normalize_clip_speed_range()
        self.trail.validate()
        value=asdict(self); value["scale_over_lifetime"]=self.scale_over_lifetime.to_dict(); value["color_over_lifetime"]=self.color_over_lifetime.to_dict(); value["opacity_over_lifetime"]=self.opacity_over_lifetime.to_dict(); value["motion"]=self.motion.to_dict(); return value

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
        values["trail"] = ParticleTrailSettings.from_dict(values.get("trail"))
        if "opacity_over_lifetime" in values:
            if any(key in values for key in ("opacity_start", "opacity_end", "easing")): raise ValueError("ambiguous opacity representation")
            values["opacity_over_lifetime"] = LifetimeScalarModulation.from_dict(values["opacity_over_lifetime"])
        value = cls(**values); value.validate(); return value


# InitVars preserve constructor compatibility without adding persistent state.
def _opacity_adapter(name):
    return property(lambda self: getattr(self.opacity_over_lifetime, name),
                    lambda self, value: setattr(self.opacity_over_lifetime, name, value))


ParticleEmitterSettings.opacity_start = _opacity_adapter("start")
ParticleEmitterSettings.opacity_end = _opacity_adapter("end")
ParticleEmitterSettings.easing = _opacity_adapter("easing")


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
