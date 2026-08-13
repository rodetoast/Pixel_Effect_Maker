from __future__ import annotations

import numpy as np
import pytest

from app.models.animation_clip import AnimationClipAsset
from app.models.particle_emitter import ParticleEmitterSettings
from app.models.property_registry import NUMERIC_PROPERTY_SPECS
from app.services.particle_render_service import build_particle_instances, particle_clip_frame_index


def _clip() -> AnimationClipAsset:
    frames=[np.full((1,1,4),index,dtype=np.uint8) for index in range(8)]
    return AnimationClipAsset("Frames",frames,fps=12,source_format="composition")


def test_playback_speed_numeric_policy_supports_fractional_2x_and_3x():
    spec=NUMERIC_PROPERTY_SPECS["particle.clip_playback_speed"]
    assert (spec.minimum,spec.maximum,spec.step,spec.decimals)==(0.01,16.0,0.1,3)
    assert all(spec.minimum<=value<=spec.maximum for value in (0.5,1.5,2.0,2.5,3.0))


def test_invalid_direct_and_legacy_playback_speed_pairs_normalize_safely():
    direct=ParticleEmitterSettings("clip",clip_speed_min=3,clip_speed_max=1)
    legacy=ParticleEmitterSettings.from_dict({"clip_asset_id":"clip","clip_speed_min":2,"clip_speed_max":1})
    assert (direct.clip_speed_min,direct.clip_speed_max)==(3,3)
    assert (legacy.clip_speed_min,legacy.clip_speed_max)==(2,2)
    assert direct.to_dict()["clip_speed_min"]<=direct.to_dict()["clip_speed_max"]


@pytest.mark.parametrize(("speed","age","expected"),[(1,1,1),(2,1,2),(3,1,3),(3,7,5),(2.5,2,5)])
def test_fixed_resource_playback_speed_advances_source_frame(speed,age,expected):
    settings=ParticleEmitterSettings("clip",clip_speed_min=speed,clip_speed_max=speed)
    particle=build_particle_instances(settings,8)[0]
    assert particle.clip_playback_speed==pytest.approx(speed)
    assert particle_clip_frame_index(_clip(),particle,age,effect_fps=12)==expected


def test_random_resource_playback_speed_is_deterministic_and_in_range():
    settings=ParticleEmitterSettings("clip",particle_count_min=64,particle_count_max=64,clip_speed_min=1,clip_speed_max=3,seed=917)
    first=build_particle_instances(settings,8);second=build_particle_instances(settings,8)
    assert first==second
    assert all(1<=particle.clip_playback_speed<=3 for particle in first)
    assert len({particle.clip_playback_speed for particle in first})>1
