"""Production workflow coverage for multi-image Resource Compositions."""

from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication, QMessageBox

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame
from app.services.particle_render_service import _RESOURCE_CLIP_CACHE, PARTICLE_RENDER_STATS, render_particle_frame
from app.services.project_io import load_project, save_project
from app.services.resource_composition_render_service import _CACHE, composition_as_clip, render_composition_frame, render_composition_frames
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.resource_editor_v2.composition_timeline import CompositionTimeline
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget


APP = QApplication.instance() or QApplication([])


class _Localization:
    language = "en"

    @staticmethod
    def text(key):
        return key


def _source_over_independent(destination, source):
    source_f=source.astype(np.float64)/255.0;destination_f=destination.astype(np.float64)/255.0
    source_alpha=source_f[...,3:4];destination_alpha=destination_f[...,3:4]
    output_alpha=source_alpha+destination_alpha*(1-source_alpha);safe=np.where(output_alpha>0,output_alpha,1)
    rgb=(source_f[...,:3]*source_alpha+destination_f[...,:3]*destination_alpha*(1-source_alpha))/safe
    return np.clip(np.rint(np.concatenate((rgb,output_alpha),axis=2)*255),0,255).astype(np.uint8)


def _pixels(kind):
    pixels=np.zeros((32,32,4),dtype=np.uint8)
    if kind=="A":pixels[7:25,7:25]=[255,20,20,255]
    elif kind=="B":pixels[14:18,4:28]=[20,255,20,192];pixels[4:28,14:18]=[20,255,20,192]
    else:pixels[5:27,5:9]=[20,20,255,255];pixels[23:27,5:25]=[20,20,255,255]
    return pixels


def _project(layer_count=3,frames=12):
    project=Project.create_default(width=32,height=32);assets=[SourceAsset(name,_pixels(name)) for name in "ABC"];project.source_assets.extend(assets)
    composition=ResourceComposition("Three Images",32,32,12,frames,True)
    layers=[CompositionLayer(asset.name,"source_asset",asset.id,0,frames-1,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y) for asset in assets[:layer_count]]
    composition.layers.extend(layers);project.resource_compositions.append(composition);return project,composition,layers,assets


def _editor(tmp_path,project,composition,layer=None):
    editor=ResourceEditorWidget(QSettings(str(tmp_path/"multi.ini"),QSettings.Format.IniFormat));editor.retranslate_ui(_Localization());stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,(layer or composition.layers[-1]).id if composition.layers else None);return editor,stack


def test_resource_can_hold_three_distinct_image_layers_and_sources():
    project,composition,layers,assets=_project()
    assert len(composition.layers)==3
    assert [layer.source_id for layer in layers]==[asset.id for asset in assets]
    assert len({layer.name for layer in layers})==3
    assert FORMAT_VERSION==19 and project.to_dict()["format_version"]==19


def test_layer_visibility_range_transform_and_pivot_are_independent():
    _,composition,layers,assets=_project();a,b,c=layers
    a.visible=False;a.start_frame,a.end_frame=0,11;a.pivot_x=3;a.add_property("position").default_value=[-20,0]
    b.start_frame,b.end_frame=3,8;b.add_property("rotation").default_value=45;b.add_property("rotation_x").default_value=20
    c.start_frame,c.end_frame=6,11;c.add_property("scale").default_value=[1.5,1.5];c.add_property("opacity").default_value=.5;c.add_property("perspective_strength").default_value=.4
    assert not a.visible and b.visible and c.visible
    assert (a.start_frame,a.end_frame)!=(b.start_frame,b.end_frame)!=(c.start_frame,c.end_frame)
    assert a.value("position",0)==[-20,0] and b.value("position",0)==[0,0]
    assert b.value("rotation",0)==45 and c.value("rotation",0)==0
    assert c.value("scale",0)==[1.5,1.5] and a.value("scale",0)==[1,1]
    assert a.pivot_x==3 and b.pivot_x==assets[1].pivot_x and assets[0].pivot_x==16


def test_three_layer_composite_matches_independent_straight_alpha_expected():
    project,composition,_,assets=_project();expected=np.zeros((32,32,4),dtype=np.uint8)
    for asset in assets:expected=_source_over_independent(expected,asset.pixels)
    assert np.array_equal(render_composition_frame(project,composition,0),expected)


def test_hidden_layer_and_inclusive_frame_ranges_are_exact():
    project,composition,layers,assets=_project();a,b,c=layers;b.start_frame,b.end_frame=3,8;c.start_frame,c.end_frame=6,11
    expected={0:(assets[0],),4:(assets[0],assets[1]),7:tuple(assets),10:(assets[0],assets[2])}
    for frame,visible in expected.items():
        output=np.zeros((32,32,4),dtype=np.uint8)
        for asset in visible:output=_source_over_independent(output,asset.pixels)
        assert np.array_equal(render_composition_frame(project,composition,frame),output)
    b.visible=False
    output=_source_over_independent(np.zeros((32,32,4),dtype=np.uint8),assets[0].pixels);output=_source_over_independent(output,assets[2].pixels)
    assert np.array_equal(render_composition_frame(project,composition,7),output)


def test_layer_list_top_matches_front_and_reorder_changes_overlap_output():
    project,composition,layers,_=_project();timeline=CompositionTimeline();timeline.retranslate(_Localization());timeline.refresh(composition,layers[-1],0)
    assert [layer.name for layer,prop in timeline.rows if prop is None]==["C","B","A"]
    before=render_composition_frame(project,composition,0);composition.layers=[layers[0],layers[2],layers[1]];composition.touch();after=render_composition_frame(project,composition,0)
    assert tuple(before[24,15])!=tuple(after[24,15]) and tuple(before[24,15])==(20,20,255,255)
    timeline.close()


def test_layer_controls_choose_explicit_source_and_emit_single_reorder():
    project,composition,layers,assets=_project();timeline=CompositionTimeline();timeline.retranslate(_Localization());timeline.set_available_sources(project);timeline.refresh(composition,layers[1],0);adds=[];moves=[];removes=[]
    timeline.add_layer_requested.connect(lambda *parts:adds.append(parts));timeline.move_layer_requested.connect(lambda *parts:moves.append(parts));timeline.remove_layer_requested.connect(removes.append)
    timeline.add_layer_menu.actions()[1].trigger();timeline.move_up.click();timeline.remove_layer.click()
    assert adds==[("source_asset",assets[1].id)] and moves==[(layers[1].id,1)] and removes==[layers[1].id]
    timeline.close()


def test_add_layer_from_explicit_asset_undo_redo_and_unique_name(tmp_path):
    project,composition,layers,assets=_project(1);editor,stack=_editor(tmp_path,project,composition,layers[0]);before_revision=composition.revision
    added=editor.add_asset_layer("source_asset",assets[1].id);duplicate=editor.add_asset_layer("source_asset",assets[1].id)
    assert [layer.source_id for layer in composition.layers]==[assets[0].id,assets[1].id,assets[1].id]
    assert added.name=="B" and duplicate.name=="B (2)" and stack.count()==2 and composition.revision>before_revision
    stack.undo();assert [layer.name for layer in composition.layers]==["A","B"]
    stack.undo();assert [layer.name for layer in composition.layers]==["A"]
    stack.redo();stack.redo();assert [layer.name for layer in composition.layers]==["A","B","B (2)"]
    editor.close()


def test_remove_layer_preserves_asset_and_undo_restores_full_state(tmp_path):
    project,composition,layers,assets=_project();editor,stack=_editor(tmp_path,project,composition,layers[1]);target=layers[1];target.visible=False;target.start_frame=3;target.end_frame=8;target.add_property("rotation").set_keyframe(4,45);expected=deepcopy(target.to_dict())
    assert editor.remove_layer(target.id) and all(layer.id!=target.id for layer in composition.layers)
    assert any(asset.id==assets[1].id for asset in project.source_assets)
    stack.undo();restored=next(layer for layer in composition.layers if layer.id==target.id);assert restored.to_dict()==expected
    stack.redo();assert all(layer.id!=target.id for layer in composition.layers)
    editor.close()


def test_empty_resource_is_existing_last_layer_policy(tmp_path):
    project,composition,layers,_=_project(1);editor,stack=_editor(tmp_path,project,composition,layers[0])
    assert editor.remove_layer(layers[0].id) and composition.layers==[]
    stack.undo();assert len(composition.layers)==1
    editor.close()


def test_reorder_is_one_undo_and_redo_and_invalidates_cached_output(tmp_path):
    project,composition,layers,_=_project();editor,stack=_editor(tmp_path,project,composition,layers[-1]);before=render_composition_frames(project,composition)[0];old_revision=composition.revision
    assert any(key[0]==composition.id for key in _CACHE);assert editor.move_layer(layers[-1].id,-1);after=render_composition_frames(project,composition)[0]
    assert [layer.name for layer in composition.layers]==["A","C","B"] and not np.array_equal(before,after) and composition.revision>old_revision and stack.count()==1
    stack.undo();assert [layer.name for layer in composition.layers]==["A","B","C"] and np.array_equal(render_composition_frames(project,composition)[0],before)
    stack.redo();assert [layer.name for layer in composition.layers]==["A","C","B"]
    editor.close()


def test_selection_switch_restores_layer_specific_tracks_and_never_mutates(tmp_path):
    project,composition,layers,_=_project();a,b,c=layers;a.add_property("rotation").set_keyframe(0,10);b.add_property("position").set_keyframe(0,[3,4]);c.add_property("opacity").set_keyframe(0,.5);editor,stack=_editor(tmp_path,project,composition,a);revision=composition.revision
    for layer,property_id in ((a,"rotation"),(b,"position"),(c,"opacity"),(a,"rotation")):
        editor.controller.select_layer(layer.id);assert property_id in editor.layer_inspector.property_cards;assert editor.layer_inspector.property_cards[property_id]["keyframe"].text()=="◆"
    assert stack.count()==0 and composition.revision==revision
    assert {layer.id for layer,prop in editor.composition_timeline.rows if prop is None}=={a.id,b.id,c.id}
    editor.close()


def test_multilayer_conditional_auto_key_is_layer_local(tmp_path):
    project,composition,layers,_=_project();a,b,_=layers;a.add_property("rotation").set_keyframe(0,0);b.add_property("rotation").set_keyframe(0,90);editor,stack=_editor(tmp_path,project,composition,a);editor.set_frame(6);editor._property_value("rotation",120)
    assert composition.layers[0].tracks["rotation"].keyframe_at(6).value==120
    assert not composition.layers[1].tracks["rotation"].has_keyframe(6) and stack.count()==1
    stack.undo();assert not composition.layers[0].tracks["rotation"].has_keyframe(6)
    editor.close()


def test_three_layer_round_trip_preserves_order_sources_ranges_and_tracks(tmp_path):
    project,composition,layers,_=_project();layers[0].add_property("rotation").set_keyframe(1,25);layers[1].add_property("position").set_keyframe(4,[3,-2]);layers[2].add_property("opacity").set_keyframe(7,.4);layers[1].start_frame=3;layers[1].end_frame=8;layers[2].visible=False;before_frames=render_composition_frames(project,composition,use_cache=False)
    loaded=load_project(save_project(project,tmp_path/"multi.peffect.json"));loaded_composition=loaded.resource_compositions[0]
    assert loaded_composition.to_dict()==composition.to_dict()
    assert [layer.source_id for layer in loaded_composition.layers]==[layer.source_id for layer in layers]
    assert all(np.array_equal(a,b) for a,b in zip(before_frames,render_composition_frames(loaded,loaded_composition,use_cache=False)))


def test_composition_as_clip_and_single_effect_use_completed_resource():
    project,composition,_,_=_project();clip=composition_as_clip(project,composition);preview=render_composition_frames(project,composition)
    assert all(np.array_equal(a,b) for a,b in zip(clip.frames,preview))
    effect=EffectResourceLayer("Multi",composition.id,end_frame=11);effect.single_settings.start_x=effect.single_settings.end_x=16;effect.single_settings.start_y=effect.single_settings.end_y=16;project.effect_resource_layers.append(effect)
    assert np.array_equal(render_effect_resource_layer_current_frame(project,effect,0),preview[0])


def test_particle_uses_one_completed_resource_clip_and_internal_transform_keeps_path(monkeypatch):
    project,composition,layers,_=_project();effect=EffectResourceLayer("Multi Particle",composition.id,placement_mode=PLACEMENT_PARTICLE,end_frame=0);settings=effect.particle_settings;settings.output_frame_count=1;settings.particle_count_min=settings.particle_count_max=100;settings.speed_min=settings.speed_max=0;settings.lifetime_min=settings.lifetime_max=1;settings.opacity_end=1;settings.origin_x=settings.origin_y=16
    import app.services.particle_render_service as particle_service
    calls=[];real=particle_service.composition_as_clip;_RESOURCE_CLIP_CACHE.clear();monkeypatch.setattr(particle_service,"composition_as_clip",lambda *args:calls.append(1) or real(*args))
    first=[];render_particle_frame(project,effect.as_particle_emitter(),0,diagnostic_collector=first)
    layers[0].add_property("rotation").default_value=45;layers[1].add_property("position").default_value=[4,0];composition.touch();second=[];render_particle_frame(project,effect.as_particle_emitter(),0,diagnostic_collector=second)
    assert calls==[1,1] and len(first)==len(second)==100
    assert [(item.x,item.y,item.local_x,item.local_y,item.local_z) for item in first]==[(item.x,item.y,item.local_x,item.local_y,item.local_z) for item in second]


def test_asset_in_resource_layer_cannot_be_deleted(tmp_path,monkeypatch):
    project,_,_,assets=_project();settings=QSettings(str(tmp_path/"window.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");window=MainWindow(ShortcutSettingsService(settings));window.project=project;warnings=[];monkeypatch.setattr(QMessageBox,"warning",lambda *args,**kwargs:warnings.append(args))
    assert not window.delete_resource("source_asset",assets[0].id) and warnings and assets[0] in project.source_assets
    window.dirty=False;window.close()
