from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.models.effect_resource_layer import EffectResourceLayer,PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings,ParticleMotionSettings
from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.particle_render_service import render_particle_frame
from app.services.resource_composition_render_service import invalidate_composition_cache,render_composition_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer,render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.preview_export_service import export_preview_sequence


def context(mode="linear"):
    project=Project.create_default(width=40,height=40,frame_count=6,fps=12)
    pixels=np.zeros((7,9,4),dtype=np.uint8)
    pixels[1:6,1:3]=[255,60,20,255];pixels[4:6,3:8]=[40,180,255,220]
    asset=SourceAsset("asymmetric",pixels,pivot_x=2,pivot_y=4);project.source_assets.append(asset)
    composition=ResourceComposition("sprite",16,16,12,3,True)
    layer=CompositionLayer("asymmetric","source_asset",asset.id,0,2,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y)
    composition.layers.append(layer);project.resource_compositions.append(composition)
    motion=ParticleMotionSettings(mode=mode,center_x=1,center_y=-2,center_z=3,radius_start=3,radius_end=7,turns=1.25,axis_start=-2,axis_end=5,helix_axis="z")
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",output_frame_count=6,particle_count_min=1,particle_count_max=1,lifetime_min=6,lifetime_max=6,speed_min=0,speed_max=0,origin_x=15,origin_y=20,seed=17,motion=motion)
    effect=EffectResourceLayer("particle",composition.id,placement_mode=PLACEMENT_PARTICLE,end_frame=5,particle_settings=settings)
    project.effect_resource_layers.append(effect)
    return project,composition,layer,effect


def particle_sample(project,effect,frame=0):
    diagnostic=[];rgba=render_particle_frame(project,effect.as_particle_emitter(),frame,diagnostic_collector=diagnostic)
    assert len(diagnostic)==1
    item=diagnostic[0]
    return rgba,(item.local_x,item.local_y,item.local_z,item.x,item.y,item.z)


@pytest.mark.parametrize(("property_id","value"),(("rotation_x",70.0),("rotation_y",45.0)))
def test_resource_rotation_changes_sprite_rgba_not_particle_center(property_id,value):
    project,composition,layer,effect=context();before_sprite=render_composition_frame(project,composition,0);before_particle,before_position=particle_sample(project,effect)
    layer.add_property(property_id).set_keyframe(0,value);layer.add_property("perspective_strength").set_keyframe(0,.65);composition.touch();invalidate_composition_cache(composition.id)
    after_sprite=render_composition_frame(project,composition,0);after_particle,after_position=particle_sample(project,effect)
    assert before_position==after_position
    assert not np.array_equal(before_sprite,after_sprite)
    assert not np.array_equal(before_particle,after_particle)


def test_resource_rotation_z_preserves_particle_motion_coordinates_and_uses_canonical_track():
    project,composition,layer,effect=context();_,before=particle_sample(project,effect,2)
    layer.add_property("rotation").set_keyframe(0,55);composition.touch();invalidate_composition_cache(composition.id)
    _,after=particle_sample(project,effect,2)
    assert before==after and "rotation_z" not in layer.tracks and layer.value("rotation",0)==55


def test_resource_perspective_changes_sprite_not_spawn_position():
    project,composition,layer,effect=context();layer.add_property("rotation_y").set_keyframe(0,60);layer.add_property("perspective_strength").set_keyframe(0,0);composition.touch();invalidate_composition_cache(composition.id)
    low_sprite=render_composition_frame(project,composition,0);_,low_position=particle_sample(project,effect)
    layer.tracks["perspective_strength"].set_keyframe(0,1);composition.touch();invalidate_composition_cache(composition.id)
    high_sprite=render_composition_frame(project,composition,0);_,high_position=particle_sample(project,effect)
    assert low_position==high_position and not np.array_equal(low_sprite,high_sprite)


@pytest.mark.parametrize("mode",["orbit","helix"])
def test_resource_2_5d_does_not_change_motion_path_or_center(mode):
    project,composition,layer,effect=context(mode);before=[particle_sample(project,effect,frame)[1] for frame in range(6)]
    layer.add_property("rotation_x").set_keyframe(0,60);layer.add_property("rotation_y").set_keyframe(0,25);layer.add_property("rotation").set_keyframe(0,135);layer.add_property("perspective_strength").set_keyframe(0,.7);composition.touch();invalidate_composition_cache(composition.id)
    after=[particle_sample(project,effect,frame)[1] for frame in range(6)]
    assert before==after


def test_resource_2_5d_round_trip_without_format_bump():
    project,composition,layer,_=context();layer.add_property("rotation_x").set_keyframe(0,25,"Ease In");layer.add_property("rotation_y").set_keyframe(1,-35);layer.add_property("perspective_strength").set_keyframe(0,.5)
    loaded=Project.from_dict(project.to_dict());restored=loaded.resource_compositions[0].layers[0]
    assert loaded.format_version==FORMAT_VERSION==13
    assert restored.value("rotation_x",0)==25 and restored.value("rotation_y",1)==-35 and restored.value("perspective_strength",0)==.5


def test_resource_2_5d_current_full_bake_and_png_export_parity(tmp_path):
    project,composition,layer,effect=context("orbit");layer.add_property("rotation_x").set_keyframe(0,55);layer.add_property("rotation_y").set_keyframe(0,20);layer.add_property("perspective_strength").set_keyframe(0,.7);composition.touch();invalidate_composition_cache(composition.id)
    direct=[render_effect_resource_layer_current_frame(project,effect,frame) for frame in range(6)];full=render_effect_resource_layer(project,effect)
    assert all(np.array_equal(a,b) for a,b in zip(direct,full,strict=True))
    apply_effect_resource_layer(project,effect,full);baked=[project.compose_frame(frame) for frame in range(6)]
    previews=export_preview_sequence(full,tmp_path/"preview","resource_2_5d");exports=export_png_frames(project,tmp_path/"project")
    for exact,composed,preview_path,export_path in zip(full,baked,previews,exports,strict=True):
        assert np.array_equal(np.asarray(Image.open(preview_path).convert("RGBA")),exact)
        assert np.array_equal(np.asarray(Image.open(export_path).convert("RGBA")),composed)
