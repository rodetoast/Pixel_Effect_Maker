"""End-to-end v9 asset, Resource, Effect, particle, and export workflows."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
from PIL import Image

from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer,PLACEMENT_PARTICLE,PLACEMENT_SINGLE
from app.models.particle_emitter import ParticleEmitterSettings,ParticleMotionSettings
from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer,render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.particle_render_service import render_particle_frame
from app.services.project_io import load_project,save_project
from app.services.resource_composition_render_service import composition_as_clip,invalidate_composition_cache,render_composition_frame
from app.services.source_import_service import import_source_asset


def asymmetric_pixels(frame=0):
    pixels=np.zeros((28,28,4),dtype=np.uint8)
    pixels[3:24,4:8]=[240,40+frame*7,30,255]
    pixels[18:23,8:25]=[20,140,240-frame*5,255]
    pixels[6+frame%8,18]=[250,230,40,255]
    return pixels


def production_project(tmp_path,mode="orbit",animated=False):
    project=Project.create_default("Integrated v9",72,72,12,True,12)
    source_path=tmp_path/f"source-{mode}.png";Image.fromarray(asymmetric_pixels(),"RGBA").save(source_path)
    asset=import_source_asset(source_path);project.source_assets.append(asset)
    if animated:
        frames=[asymmetric_pixels(frame) for frame in range(12)]
        clip=AnimationClipAsset("animated",frames,fps=12,frame_durations_ms=[83]*12,playback_mode="loop")
        project.animation_clips.append(clip);source_type,source_id="animation_clip",clip.id
    else:source_type,source_id="source_asset",asset.id
    composition=ResourceComposition("Resource",28,28,12,12,True)
    resource_layer=CompositionLayer("Sprite",source_type,source_id,0,11,pivot_x=14,pivot_y=14)
    composition.layers.append(resource_layer);project.resource_compositions.append(composition)
    motion=ParticleMotionSettings(mode="linear" if mode=="single" else mode,center_x=2,center_y=-1,center_z=3,radius_start=4,radius_end=10,
        ellipse_scale_x=1.2,ellipse_scale_y=.8,start_angle_degrees=25,turns=1.5,direction="clockwise",
        phase_spread_degrees=20,helix_axis="z",axis_start=-4,axis_end=7,perspective_strength=.25)
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",output_frame_count=12,
        particle_count_min=3,particle_count_max=3,lifetime_min=12,lifetime_max=12,speed_min=1,speed_max=1,
        direction_degrees=0,direction_spread_degrees=0,origin_x=31,origin_y=36,seed=91,motion=motion)
    placement=PLACEMENT_SINGLE if mode=="single" else PLACEMENT_PARTICLE
    effect=EffectResourceLayer(f"{mode} layer",composition.id,placement_mode=placement,end_frame=11,particle_settings=settings)
    project.effect_resource_layers.append(effect);apply_effect_resource_layer(project,effect)
    return project,asset,composition,resource_layer,effect


def diagnostics(project,effect):
    values=[]
    for frame in range(12):
        items=[];render_particle_frame(project,effect.as_particle_emitter(),frame,diagnostic_collector=items,
            layer_space_transform=effect.layer_space_transform)
        values.append([(item.spawn_frame,item.age,item.local_x,item.local_y,item.local_z,item.x,item.y,item.z,item.source_frame,item.depth_key) for item in items])
    return values


def test_asset_to_resource_to_effect_round_trip(tmp_path):
    project,asset,composition,resource_layer,effect=production_project(tmp_path,"single")
    identity=render_composition_frame(project,composition,0)
    assert np.array_equal(asset.pixels,asymmetric_pixels())
    assert np.array_equal(identity,asset.pixels)
    assert np.array_equal(composition_as_clip(project,composition).frames[0],asset.pixels)
    resource_layer.add_property("rotation_x").set_keyframe(0,28);resource_layer.add_property("rotation_y").set_keyframe(0,-19)
    resource_layer.add_property("rotation").set_keyframe(0,12);resource_layer.add_property("perspective_strength").set_keyframe(0,.45)
    composition.touch();invalidate_composition_cache(composition.id)
    effect.layer_space_transform.position_x=8;effect.layer_space_transform.rotation_y=15;effect.layer_space_transform.revision+=1
    effect.surface_transform.rotation_z=-7;effect.surface_transform.opacity=.8;effect.surface_transform.revision+=1
    before=[render_effect_resource_layer_current_frame(project,effect,frame) for frame in range(12)]
    loaded=load_project(save_project(project,tmp_path/"integrated"));loaded_effect=loaded.effect_resource_layers[0]
    after=[render_effect_resource_layer_current_frame(loaded,loaded_effect,frame) for frame in range(12)]
    assert loaded.format_version==FORMAT_VERSION==19
    assert all(np.array_equal(a,b) for a,b in zip(before,after,strict=True))
    assert loaded_effect.layer_space_transform.rotation_y==15 and loaded_effect.surface_transform.rotation_z==-7


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_resource_2_5d_particle_coordinates_remain_independent(tmp_path,mode):
    project,_,composition,resource_layer,effect=production_project(tmp_path,mode,animated=True)
    before=diagnostics(project,effect)
    resource_layer.add_property("rotation_x").set_keyframe(0,52);resource_layer.add_property("rotation_y").set_keyframe(0,31)
    resource_layer.add_property("rotation").set_keyframe(0,18);resource_layer.add_property("rotation").set_keyframe(11,126)
    resource_layer.add_property("perspective_strength").set_keyframe(0,.6);composition.touch();invalidate_composition_cache(composition.id)
    after=diagnostics(project,effect)
    assert before==after
    assert not np.array_equal(render_effect_resource_layer_current_frame(project,effect,0),asymmetric_pixels())


def test_resource_system_surface_pipeline_round_trip(tmp_path):
    project,_,_,_,effect=production_project(tmp_path,"orbit",animated=True)
    local=diagnostics(project,effect)
    effect.layer_space_transform.position_x=9;effect.layer_space_transform.position_z=6
    effect.layer_space_transform.rotation_x=21;effect.layer_space_transform.rotation_y=-17
    effect.layer_space_transform.perspective_strength=.35;effect.layer_space_transform.revision+=1
    projected=diagnostics(project,effect)
    assert [[item[:5] for item in frame] for frame in local]==[[item[:5] for item in frame] for frame in projected]
    assert any(a[5:8]!=b[5:8] for left,right in zip(local,projected) for a,b in zip(left,right))
    effect.surface_transform.position_y=4;effect.surface_transform.rotation_z=11;effect.surface_transform.opacity=.75;effect.surface_transform.revision+=1
    expected=[render_effect_resource_layer_current_frame(project,effect,frame) for frame in range(12)]
    loaded=load_project(save_project(project,tmp_path/"pipeline"));actual=[render_effect_resource_layer_current_frame(loaded,loaded.effect_resource_layers[0],frame) for frame in range(12)]
    assert all(np.array_equal(a,b) for a,b in zip(expected,actual,strict=True))


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_particle_full_workflow_is_frame_order_independent(tmp_path,mode):
    project,_,_,_,effect=production_project(tmp_path,mode,animated=True)
    full=render_effect_resource_layer(project,effect)
    orders=(range(12),reversed(range(12)),(7,2,10,3,7,0,11))
    for order in orders:
        for frame in order:assert np.array_equal(render_effect_resource_layer_current_frame(project,effect,frame),full[frame])


def test_export_sequence_matches_reloaded_project(tmp_path):
    project,_,composition,resource_layer,effect=production_project(tmp_path,"helix",animated=True)
    resource_layer.add_property("rotation_y").set_keyframe(0,35);resource_layer.add_property("rotation_y").set_keyframe(11,-25)
    composition.touch();invalidate_composition_cache(composition.id)
    effect.layer_space_transform.rotation_x=18;effect.layer_space_transform.position_z=5;effect.layer_space_transform.revision+=1
    exact=[render_exact_playback_frame(project,frame)[0] for frame in range(12)]
    loaded=load_project(save_project(project,tmp_path/"export-source"));loaded_effect=loaded.effect_resource_layers[0]
    baked=deepcopy(loaded);baked_effect=baked.effect_resource_layers[0];apply_effect_resource_layer(baked,baked_effect)
    written=export_png_frames(baked,tmp_path/"sequence")
    assert len(written)==12
    for frame,path in enumerate(written):
        direct=render_effect_resource_layer_current_frame(loaded,loaded_effect,frame)
        playback=render_exact_playback_frame(loaded,frame)[0]
        decoded=np.asarray(Image.open(path).convert("RGBA"))
        assert np.array_equal(direct,render_effect_resource_layer(loaded,loaded_effect)[frame])
        assert np.array_equal(playback,exact[frame])
        assert np.array_equal(decoded,baked.compose_frame(frame))
        assert np.array_equal(decoded,playback)
