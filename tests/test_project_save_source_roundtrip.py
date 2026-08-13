import json

import numpy as np
from PIL import Image
import pytest

from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.services.project_io import ProjectIOError,load_project,save_project
from app.services.resource_import_service import import_resource


def source_project(tmp_path):
    png=tmp_path/"spark.png";pixels=np.zeros((4,5,4),dtype=np.uint8);pixels[1:3,1:4]=[10,20,30,177];Image.fromarray(pixels,"RGBA").save(png)
    gif=tmp_path/"smoke.gif";frames=[Image.new("RGBA",(3,2),(255,0,0,255)),Image.new("RGBA",(3,2),(0,255,0,128))];frames[0].save(gif,save_all=True,append_images=frames[1:],duration=[40,120],loop=0)
    ase=tmp_path/"hero.aseprite";ase.write_bytes(b"fixture")
    static=import_resource(png);clip=import_resource(gif);ase_clip=AnimationClipAsset("hero.aseprite",[item.copy() for item in clip.frames],fps=clip.fps,frame_durations_ms=list(clip.frame_durations_ms),source_format="aseprite",source_path=str(ase),tags={"idle":[0,1]})
    project=Project.create_default("Sources",8,8);project.source_assets.append(static);project.animation_clips.extend((clip,ase_clip))
    for asset,source_type in ((static,"source_asset"),(clip,"animation_clip"),(ase_clip,"animation_clip")):
        composition=ResourceComposition(asset.name,8,8,12,2,True);composition.layers.append(CompositionLayer(asset.name,source_type,asset.id,0,1));project.resource_compositions.append(composition);project.effect_resource_layers.append(EffectResourceLayer(asset.name,composition.id))
    return project,(png,gif,ase)


def assert_references(project):
    assets={item.id for item in project.source_assets};clips={item.id for item in project.animation_clips};compositions={item.id for item in project.resource_compositions}
    for composition in project.resource_compositions:
        for layer in composition.layers:assert layer.source_id in (assets if layer.source_type=="source_asset" else clips)
    assert all(layer.resource_composition_id in compositions for layer in project.effect_resource_layers)


def test_png_source_asset_round_trip(tmp_path):
    project,_=source_project(tmp_path);before=project.source_assets[0];loaded=load_project(save_project(project,tmp_path/"project"));after=loaded.source_assets[0]
    assert (after.id,after.name,after.source_path,after.source_format,after.pivot_x,after.pivot_y)==(before.id,before.name,before.source_path,before.source_format,before.pivot_x,before.pivot_y)
    assert np.array_equal(after.pixels,before.pixels)


def test_gif_source_asset_round_trip(tmp_path):
    project,_=source_project(tmp_path);before=project.animation_clips[0];after=load_project(save_project(project,tmp_path/"project")).animation_clips[0]
    assert (after.id,after.source_path,after.source_format,after.frame_durations_ms,after.loop)==(before.id,before.source_path,"gif",[40,120],before.loop)
    assert all(np.array_equal(a,b) for a,b in zip(before.frames,after.frames,strict=True))


def test_aseprite_source_asset_round_trip(tmp_path):
    project,_=source_project(tmp_path);before=project.animation_clips[1];after=load_project(save_project(project,tmp_path/"project")).animation_clips[1]
    assert (after.id,after.source_path,after.source_format,after.tags)==(before.id,before.source_path,"aseprite",{"idle":[0,1]})
    assert all(np.array_equal(a,b) for a,b in zip(before.frames,after.frames,strict=True))


def test_saved_project_loads_after_all_originals_are_deleted(tmp_path):
    project,paths=source_project(tmp_path);saved=save_project(project,tmp_path/"project");[path.unlink() for path in paths];loaded=load_project(saved)
    assert len(loaded.source_assets)==1 and len(loaded.animation_clips)==2;assert_references(loaded)


def test_source_and_effect_reference_ids_round_trip(tmp_path):
    project,_=source_project(tmp_path);before_sources=[item.id for item in project.source_assets+project.animation_clips];before_compositions=[item.id for item in project.resource_compositions];before_effects=[item.id for item in project.effect_resource_layers]
    loaded=load_project(save_project(project,tmp_path/"project"));assert [item.id for item in loaded.source_assets+loaded.animation_clips]==before_sources;assert [item.id for item in loaded.resource_compositions]==before_compositions;assert [item.id for item in loaded.effect_resource_layers]==before_effects;assert_references(loaded)


def test_new_project_uses_compact_payload_and_no_ui_cache(tmp_path):
    project,_=source_project(tmp_path);data=json.loads(save_project(project,tmp_path/"project").read_text(encoding="utf-8"))
    assert data["format_version"]==FORMAT_VERSION==10 and isinstance(data["source_assets"][0]["pixels"],dict) and isinstance(data["animation_clips"][0]["frames"][0],dict)
    serialized=json.dumps(data);assert "interactive_transform_proxy" not in serialized and "prewarm" not in serialized and "QPixmap" not in serialized and "preview_frames" not in serialized


def test_v6_nested_list_project_loads_and_next_save_uses_v7_compact_payload(tmp_path):
    project,_=source_project(tmp_path);data=project.to_dict();data["format_version"]=6
    for frame,model in zip(data["frames"],project.frames,strict=True):
        frame["layer_pixels"]={key:value.tolist() for key,value in model.layer_pixels.items()}
    data["source_assets"][0]["pixels"]=project.source_assets[0].pixels.tolist()
    for clip_data,clip in zip(data["animation_clips"],project.animation_clips,strict=True):clip_data["frames"]=[frame.tolist() for frame in clip.frames]
    legacy=tmp_path/"legacy-v6.peffect.json";legacy.write_text(json.dumps(data),encoding="utf-8");loaded=load_project(legacy);new_data=json.loads(save_project(loaded,tmp_path/"upgraded").read_text(encoding="utf-8"))
    assert loaded.format_version==10 and new_data["format_version"]==10 and isinstance(new_data["source_assets"][0]["pixels"],dict);assert_references(loaded)


def test_corrupt_embedded_source_fails_load_instead_of_dropping_pixels(tmp_path):
    project,_=source_project(tmp_path);path=save_project(project,tmp_path/"project");data=json.loads(path.read_text(encoding="utf-8"));data["source_assets"][0]["pixels"]["checksum"]="0"*64;path.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ProjectIOError) as failure:load_project(path)
    assert failure.value.code=="load_payload" and "checksum" in str(failure.value)
