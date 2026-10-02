from copy import deepcopy

import numpy as np

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer
from app.services.resource_composition_render_service import render_composition_frame


def _rgba(color):
    value=np.zeros((2,2,4),dtype=np.uint8);value[:]=[*color,255];return value


def test_resource_solo_is_multi_select_visibility_aware_and_preview_only():
    project=Project.create_default(width=2,height=2,frame_count=1);red=SourceAsset("Red",_rgba((255,0,0)));blue=SourceAsset("Blue",_rgba((0,0,255)));project.source_assets=[red,blue]
    composition=ResourceComposition("Mix",2,2,12,1);a=CompositionLayer("A","source_asset",red.id,0,0);b=CompositionLayer("B","source_asset",blue.id,0,0);composition.layers=[a,b];project.resource_compositions=[composition]
    normal=render_composition_frame(project,composition,0);b.solo=True
    preview=render_composition_frame(project,composition,0,preview=True);final=render_composition_frame(project,composition,0)
    assert preview[...,2].max()==255 and preview[...,0].max()==0 and np.array_equal(final,normal)
    a.solo=True;b.visible=False
    isolated=render_composition_frame(project,composition,0,preview=True);assert isolated[...,0].max()==255 and isolated[...,2].max()==0
    a.solo=b.solo=False
    assert np.array_equal(render_composition_frame(project,composition,0,preview=True),render_composition_frame(project,composition,0))


def test_effect_solo_preview_does_not_change_final_composition_or_exact_export_path():
    project=Project.create_default(width=2,height=2,frame_count=1);project.layers[0].visible=False;red=SourceAsset("Red",_rgba((255,0,0)));blue=SourceAsset("Blue",_rgba((0,0,255)));project.source_assets=[red,blue];ca=ResourceComposition("A",2,2,12,1,layers=[CompositionLayer("A","source_asset",red.id,0,0)]);cb=ResourceComposition("B",2,2,12,1,layers=[CompositionLayer("B","source_asset",blue.id,0,0)]);project.resource_compositions=[ca,cb]
    a=EffectResourceLayer("A",ca.id,solo=True);b=EffectResourceLayer("B",cb.id)
    for layer in (a,b):layer.single_settings.start_x=layer.single_settings.end_x=1;layer.single_settings.start_y=layer.single_settings.end_y=1
    project.effect_resource_layers=[a,b];apply_effect_resource_layer(project,a);apply_effect_resource_layer(project,b)
    final=project.compose_frame(0);preview=project.compose_frame(0,solo_preview=True);exact_final,_=render_exact_playback_frame(project,0);exact_preview,_=render_exact_playback_frame(project,0,solo_preview=True)
    assert np.array_equal(final,exact_final) and np.array_equal(preview,exact_preview) and not np.array_equal(final,preview)
    b.solo=True;b.visible=False;next(item for item in project.layers if item.id==b.generated_layer_id).visible=False
    assert np.array_equal(project.compose_frame(0,solo_preview=True),project.frames[0].layer_pixels[a.generated_layer_id])


def test_v9_defaults_and_v10_round_trip_preserve_resource_and_effect_solo():
    project=Project.create_default(width=2,height=2,frame_count=1);asset=SourceAsset("A",_rgba((1,2,3)));composition=ResourceComposition("C",2,2,12,1,layers=[CompositionLayer("A","source_asset",asset.id,0,0,locked=True,solo=True)]);project.source_assets=[asset];project.resource_compositions=[composition]
    effect=EffectResourceLayer("E",composition.id,generated_layer_id=project.layers[0].id,locked=True,solo=True);project.effect_resource_layers=[effect]
    data=project.to_dict();assert data["format_version"]==FORMAT_VERSION==22
    loaded=Project.from_dict(deepcopy(data));assert loaded.resource_compositions[0].layers[0].locked and loaded.resource_compositions[0].layers[0].solo and loaded.effect_resource_layers[0].locked and loaded.effect_resource_layers[0].solo
    legacy=deepcopy(data);legacy["format_version"]=9
    for value in (legacy["resource_compositions"][0]["layers"][0],legacy["effect_resource_layers"][0]):value.pop("locked");value.pop("solo")
    migrated=Project.from_dict(legacy);assert not migrated.resource_compositions[0].layers[0].locked and not migrated.resource_compositions[0].layers[0].solo and not migrated.effect_resource_layers[0].locked and not migrated.effect_resource_layers[0].solo
