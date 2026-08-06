from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.models.effect_resource_layer import EffectResourceLayer, EffectLayerTransform3D, PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings, ParticleMotionSettings
from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_layer_transform_3d_render_service import transform_rgba_frame
from app.services.effect_resource_layer_render_service import (
    apply_effect_resource_layer,
    invalidate_effect_resource_layer_base,
    render_effect_resource_layer,
    render_effect_resource_layer_current_frame,
)
from app.services.export_service import export_png_frames
from app.services.particle_render_service import render_particle_frame, render_particle_frames
from app.services.preview_export_service import export_preview_sequence


def context(mode):
    project=Project.create_default(name=f"{mode}-motion",width=32,height=32,fps=12)
    pixels=np.zeros((5,5,4),dtype=np.uint8);pixels[1:4,1:4]=[230,70,20,210]
    asset=SourceAsset("spark",pixels,pivot_x=2.5,pivot_y=2.5)
    composition=ResourceComposition("resource",5,5,12,3,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,2,pivot_x=2.5,pivot_y=2.5))
    project.source_assets.append(asset);project.resource_compositions.append(composition)
    motion=ParticleMotionSettings(mode=mode,radius_start=3,radius_end=8,turns=1.5,direction="clockwise",phase_spread_degrees=180,
        helix_axis="z",axis_start=-4,axis_end=7,perspective_strength=.15)
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",output_frame_count=6,
        particle_count_min=4,particle_count_max=4,lifetime_min=6,lifetime_max=6,speed_min=0,speed_max=0,
        origin_x=16,origin_y=16,opacity_start=1,opacity_end=.4,seed=77,motion=motion)
    transform=EffectLayerTransform3D(position_x=2,position_y=-1,rotation_z=8,scale_x=1.1,scale_y=.9,opacity=.85)
    layer=EffectResourceLayer("motion",composition.id,placement_mode=PLACEMENT_PARTICLE,end_frame=5,particle_settings=settings,layer_transform=transform)
    project.effect_resource_layers.append(layer)
    return project,layer


@pytest.mark.parametrize("mode",["orbit","helix"])
def test_motion_direct_preview_bake_and_exports_match(mode,tmp_path):
    project,layer=context(mode);emitter=layer.as_particle_emitter();invalidate_effect_resource_layer_base()
    base=render_particle_frames(project,emitter)
    exact=[transform_rgba_frame(frame,layer.layer_transform,index) for index,frame in enumerate(base)]
    direct=[render_effect_resource_layer_current_frame(project,layer,index) for index in range(6)]
    full=render_effect_resource_layer(project,layer)
    assert all(np.array_equal(a,b) and np.array_equal(a,c) for a,b,c in zip(exact,direct,full,strict=True))
    generated=apply_effect_resource_layer(project,layer,full)
    assert generated.id==layer.generated_layer_id
    composed=[project.compose_frame(index) for index in range(6)]
    preview_paths=export_preview_sequence(full,tmp_path/"preview",mode)
    export_paths=export_png_frames(project,tmp_path/"project")
    for preview_expected,baked_expected,preview_path,export_path in zip(full,composed,preview_paths,export_paths,strict=True):
        assert np.array_equal(np.asarray(Image.open(preview_path).convert("RGBA")),preview_expected)
        assert np.array_equal(np.asarray(Image.open(export_path).convert("RGBA")),baked_expected)
    invalidate_effect_resource_layer_base()


@pytest.mark.parametrize("mode",["orbit","helix"])
def test_motion_playback_and_scrub_order_are_deterministic(mode):
    project,layer=context(mode);emitter=layer.as_particle_emitter()
    forward=render_particle_frames(project,emitter)
    order=(5,1,4,0,3,2)
    scrub={index:render_particle_frame(project,emitter,index) for index in order}
    reverse={index:render_particle_frame(project,emitter,index) for index in reversed(order)}
    assert all(np.array_equal(forward[index],scrub[index]) and np.array_equal(scrub[index],reverse[index]) for index in order)
