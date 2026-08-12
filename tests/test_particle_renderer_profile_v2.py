"""Exact regressions for the second measured Particle CPU optimization pass."""

from __future__ import annotations

from copy import deepcopy
import numpy as np

from app.models.source_asset import SourceAsset
from app.services.effect_render_service import (
    EFFECT_RASTER_STATS,
    _render_projective_source,
    render_transformed_source,
    reset_effect_raster_stats,
)
from app.services.particle_render_service import render_particle_frame,render_particle_frames
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer_current_frame
from tests.test_v9_integrated_workflow import production_project


def render_reference(asset,canvas_shape,*,x,y,rotation,scale_x,scale_y,opacity):
    output=np.zeros(canvas_shape,dtype=np.uint8)
    _render_projective_source(output,asset,x,y,rotation,scale_x,scale_y,0.0,0.0,0.0,opacity)
    return output


def test_particle_identity_transform_fast_path_matches_source_exactly():
    pixels=np.zeros((7,9,4),dtype=np.uint8);pixels[...,0:3]=[19,37,73];pixels[1:6,2:8]=[230,70,20,255]
    asset=SourceAsset("identity",pixels,pivot_x=4,pivot_y=3);output=np.zeros((20,24,4),dtype=np.uint8)
    render_transformed_source(output,asset,position_x=12,position_y=10,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=1)
    assert np.array_equal(output[7:14,8:17],pixels)


def test_particle_integer_and_fractional_translation_paths_match_exact_semantics():
    pixels=np.zeros((5,6,4),dtype=np.uint8);pixels[1:5,1:4]=[220,80,30,190];asset=SourceAsset("translation",pixels,pivot_x=2,pivot_y=2)
    integer=np.zeros((16,18,4),dtype=np.uint8);render_transformed_source(integer,asset,position_x=7,position_y=8,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=1)
    assert np.array_equal(integer[6:11,5:11],pixels)
    for x,y,opacity in ((7.25,8.75,1.0),(-1.4,3.2,.6),(17.2,15.1,.25)):
        actual=np.zeros((16,18,4),dtype=np.uint8);render_transformed_source(actual,asset,position_x=x,position_y=y,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=opacity)
        assert np.array_equal(actual,render_reference(asset,actual.shape,x=x,y=y,rotation=0,scale_x=1,scale_y=1,opacity=opacity))


def test_particle_affine_sampler_matches_projective_reference_for_1000_random_cases():
    rng=np.random.default_rng(90117)
    for index in range(1000):
        height=int(rng.integers(1,35));width=int(rng.integers(1,35));pixels=rng.integers(0,256,(height,width,4),dtype=np.uint8)
        pixels[...,3]=rng.choice(np.array([0,80,160,255],dtype=np.uint8),(height,width))
        asset=SourceAsset("random",pixels,pivot_x=float(rng.uniform(-2,width+2)),pivot_y=float(rng.uniform(-2,height+2)))
        x=float(rng.uniform(-30,94));y=float(rng.uniform(-30,94));rotation=float(rng.choice([0,0,0,rng.uniform(-180,180)]))
        scale_x=1.0 if index%3==0 else float(rng.uniform(.15,3));scale_y=1.0 if index%3==0 else float(rng.uniform(.15,3));opacity=float(rng.choice([1,1,.25,.6]))
        actual=np.zeros((64,64,4),dtype=np.uint8);render_transformed_source(actual,asset,position_x=x,position_y=y,rotation=rotation,scale_x=scale_x,scale_y=scale_y,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=opacity)
        expected=render_reference(asset,actual.shape,x=x,y=y,rotation=rotation,scale_x=scale_x,scale_y=scale_y,opacity=opacity)
        assert np.array_equal(actual,expected),index


def test_particle_offscreen_culling_preserves_partial_visibility():
    pixels=np.full((9,9,4),[30,170,240,210],dtype=np.uint8);asset=SourceAsset("edge",pixels,pivot_x=4.5,pivot_y=4.5)
    for x,y,rotation in ((-1.0,5.0,0),(20.0,5.0,37),(5.0,-1.0,-51),(5.0,20.0,93)):
        actual=np.zeros((20,20,4),dtype=np.uint8);render_transformed_source(actual,asset,position_x=x,position_y=y,rotation=rotation,scale_x=1.3,scale_y=.7,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=.65)
        expected=render_reference(asset,actual.shape,x=x,y=y,rotation=rotation,scale_x=1.3,scale_y=.7,opacity=.65)
        assert np.array_equal(actual,expected) and np.any(actual[...,3])


def test_particle_hot_paths_avoid_projective_solve_when_safe():
    pixels=np.full((5,7,4),[220,80,30,200],dtype=np.uint8);asset=SourceAsset("calls",pixels,pivot_x=3.5,pivot_y=2.5);canvas=np.zeros((32,32,4),dtype=np.uint8)
    reset_effect_raster_stats()
    render_transformed_source(canvas,asset,position_x=16.25,position_y=15.75,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=1)
    render_transformed_source(canvas,asset,position_x=16,position_y=16,rotation=37,scale_x=1.2,scale_y=.8,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=.7)
    assert EFFECT_RASTER_STATS["translation_blits"]==1 and EFFECT_RASTER_STATS["affine_blits"]==1


def test_animated_resource_linear_orbit_helix_current_full_and_playback_parity(tmp_path):
    for mode in ("linear","orbit","helix"):
        case_path=tmp_path/mode;case_path.mkdir()
        project,_,composition,resource_layer,effect=production_project(case_path,mode,animated=True)
        resource_layer.add_property("rotation_x").set_keyframe(0,31);resource_layer.add_property("rotation_y").set_keyframe(0,-23)
        resource_layer.add_property("rotation").set_keyframe(0,17);resource_layer.add_property("perspective_strength").set_keyframe(0,.45);composition.touch()
        full=render_particle_frames(project,effect.as_particle_emitter(),layer_space_transform=effect.layer_space_transform)
        for frame in range(12):
            direct=render_particle_frame(project,effect.as_particle_emitter(),frame,layer_space_transform=effect.layer_space_transform)
            playback,_=render_exact_playback_frame(project,frame)
            assert np.array_equal(direct,full[frame])
            expected=deepcopy(project);expected_effect=expected.effect_resource_layers[0]
            apply_effect_resource_layer_current_frame(expected,expected_effect,frame)
            assert np.array_equal(playback,expected.compose_frame(frame))
