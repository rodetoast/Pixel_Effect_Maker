"""Multi-Resource Effect production workflow and deterministic output coverage."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication,QMessageBox

from app.models.effect_resource_layer import EffectResourceLayer,PLACEMENT_PARTICLE,PLACEMENT_SINGLE
from app.models.project import FORMAT_VERSION,Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.preview_export_service import export_preview_sequence
from app.services.project_io import load_project,save_project
from app.services.resource_composition_render_service import render_composition_frame
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def _service(tmp_path):
    settings=QSettings(str(tmp_path/"effect-multi.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en");return ShortcutSettingsService(settings)


def _resource(project,name,color,size=12,alpha=255):
    pixels=np.zeros((size,size,4),dtype=np.uint8);pixels[2:-2,2:-2]=[*color,alpha]
    if name=="Spark":pixels[:size//2,2:4]=[*color,alpha]
    asset=SourceAsset(name,pixels);composition=ResourceComposition(name,size,size,12,4,True);composition.layers.append(CompositionLayer(name,"source_asset",asset.id,0,3,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y));project.source_assets.append(asset);project.resource_compositions.append(composition);return composition


def _window(tmp_path):
    window=MainWindow(_service(tmp_path));project=window.project
    resources=[_resource(project,"Slash",(255,60,20)),_resource(project,"Smoke",(80,170,100),alpha=170),_resource(project,"Spark",(30,80,255),8),_resource(project,"Glow",(255,220,40),alpha=120)]
    window.effect_library.refresh(project);return window,resources


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


def test_effect_can_hold_multiple_resources_and_same_resource_twice(tmp_path):
    window,resources=_window(tmp_path);a=window.create_resource_layer_from_resource(resources[0].id);b=window.create_resource_layer_from_resource(resources[1].id);duplicate=window.create_resource_layer_from_resource(resources[1].id)
    assert len(window.project.effect_resource_layers)==3
    assert [item.resource_composition_id for item in window.project.effect_resource_layers]==[resources[0].id,resources[1].id,resources[1].id]
    assert (a.name,b.name,duplicate.name)==("Slash","Smoke","Smoke (2)") and len({item.id for item in window.project.effect_resource_layers})==3
    _close(window)


def test_add_menu_uses_explicit_resource_and_list_shows_resource_mode_visibility(tmp_path):
    window,resources=_window(tmp_path);adds=[];window.effect_library.add_composition_requested.disconnect(window.create_resource_layer_from_resource);window.effect_library.add_composition_requested.connect(adds.append);window.effect_library.refresh(window.project)
    window.effect_library.composition_add_menu.actions()[2].trigger();assert adds==[resources[2].id]
    layer=window.create_resource_layer_from_resource(resources[1].id,PLACEMENT_PARTICLE);window.effect_library.refresh(window.project);text=window.effect_library.composition_list.item(0).text()
    assert layer.name in text and "Smoke" in text and "Particle" in text and text.startswith("●")
    _close(window)


def test_effect_layer_name_is_independent_unique_and_undoable(tmp_path):
    window,resources=_window(tmp_path);first=window.create_resource_layer_from_resource(resources[0].id);second=window.create_resource_layer_from_resource(resources[1].id);before=resources[0].name
    assert window.rename_resource_layer(first.id,"Hero") and window.rename_resource_layer(second.id,"Hero")
    assert first.name=="Hero" and second.name=="Hero (2)" and resources[0].name==before
    window.application_undo_stack.undo();assert second.name=="Smoke";window.application_undo_stack.redo();assert second.name=="Hero (2)"
    _close(window)


def test_add_resource_layer_undo_redo_restores_exact_id_and_reference(tmp_path):
    window,resources=_window(tmp_path);before=window.application_undo_stack.count();layer=window.create_resource_layer_from_resource(resources[0].id);identifier=layer.id
    assert window.application_undo_stack.count()==before+1
    window.application_undo_stack.undo();assert all(item.id!=identifier for item in window.project.effect_resource_layers) and resources[0] in window.project.resource_compositions
    window.application_undo_stack.redo();restored=next(item for item in window.project.effect_resource_layers if item.id==identifier);assert restored.resource_composition_id==resources[0].id
    _close(window)


def test_remove_preserves_resource_and_undo_restores_full_layer(tmp_path):
    window,resources=_window(tmp_path);layer=window.create_resource_layer_from_resource(resources[2].id,PLACEMENT_PARTICLE);layer.visible=False;layer.layer_transform.rotation_y=31;layer.particle_settings.motion.mode="orbit";layer.particle_settings.motion.radius_end=9;expected=deepcopy(layer.to_dict())
    assert window.remove_resource_layer(layer.id) and resources[2] in window.project.resource_compositions
    window.application_undo_stack.undo();restored=next(item for item in window.project.effect_resource_layers if item.id==layer.id);assert restored.to_dict()==expected
    window.application_undo_stack.redo();assert all(item.id!=layer.id for item in window.project.effect_resource_layers)
    _close(window)


def test_last_effect_resource_layer_can_be_removed(tmp_path):
    window,resources=_window(tmp_path);layer=window.create_resource_layer_from_resource(resources[0].id);assert window.remove_resource_layer(layer.id);assert not window.project.effect_resource_layers
    window.application_undo_stack.undo();assert any(item.id==layer.id for item in window.project.effect_resource_layers)
    _close(window)


def test_effect_list_top_is_canvas_front_and_reorder_is_one_undo(tmp_path):
    window,resources=_window(tmp_path);back=window.create_resource_layer_from_resource(resources[0].id);front=window.create_resource_layer_from_resource(resources[2].id);before,_=render_exact_playback_frame(window.project,0);before_count=window.application_undo_stack.count();window.effect_library.refresh(window.project)
    assert window.effect_library.composition_list.item(0).data(256)==front.id
    assert window.reorder_resource_layer(back.id,1) and window.application_undo_stack.count()==before_count+1;after,_=render_exact_playback_frame(window.project,0)
    assert not np.array_equal(before,after) and window._selected_resource_layer().id==back.id
    window.application_undo_stack.undo();assert [item.id for item in window.project.effect_resource_layers][-1]==front.id
    window.application_undo_stack.redo();assert [item.id for item in window.project.effect_resource_layers][-1]==back.id
    _close(window)


def test_visibility_and_single_inclusive_range_are_layer_local(tmp_path):
    window,resources=_window(tmp_path);a=window.create_resource_layer_from_resource(resources[0].id);b=window.create_resource_layer_from_resource(resources[1].id);after=deepcopy(b);after.start_frame=1;after.end_frame=2;after.single_settings.start_frame=1;after.single_settings.end_frame=2;window.application_undo_stack.push(__import__("app.ui.undo_commands",fromlist=["EditorValueCommand"]).EditorValueCommand(window,b.id,"resource_layer_settings",b,after,"Range"))
    generated_a=next(item for item in window.project.layers if item.id==a.generated_layer_id);window.set_layer_visibility(window.project.layers.index(generated_a),False)
    assert not a.visible and b.visible
    assert not render_effect_resource_layer_current_frame(window.project,b,0)[...,3].any() and render_effect_resource_layer_current_frame(window.project,b,1)[...,3].any()
    _close(window)


def test_single_linear_orbit_helix_coexist_with_independent_state(tmp_path):
    window,resources=_window(tmp_path);layers=[]
    for index,(mode,motion) in enumerate(((PLACEMENT_SINGLE,"linear"),(PLACEMENT_PARTICLE,"linear"),(PLACEMENT_PARTICLE,"orbit"),(PLACEMENT_PARTICLE,"helix"))):
        layer=window.create_resource_layer_from_resource(resources[index].id,mode);layer.particle_settings.motion.mode=motion;layer.particle_settings.seed=10+index;layer.particle_settings.particle_count_min=layer.particle_settings.particle_count_max=index+1;layers.append(layer)
    layers[0].layer_transform.position_x=-10;layers[1].layer_transform.rotation_y=30;layers[2].layer_transform.scale_x=layers[2].layer_transform.scale_y=1.5;layers[3].surface_transform.opacity=.5
    assert [item.placement_mode for item in layers]==["single","particle","particle","particle"]
    assert [item.particle_settings.motion.mode for item in layers]==["linear","linear","orbit","helix"]
    assert len({id(item.particle_settings) for item in layers})==4 and len({item.particle_settings.seed for item in layers})==4
    assert layers[0].layer_transform.position_x==-10 and layers[1].layer_transform.position_x==0 and layers[3].surface_transform.opacity==.5
    _close(window)


def test_effect_layer_transform_motion_tracks_and_timeline_markers_are_independent(tmp_path):
    window,resources=_window(tmp_path);a=window.create_resource_layer_from_resource(resources[0].id);b=window.create_resource_layer_from_resource(resources[1].id,PLACEMENT_PARTICLE);c=window.create_resource_layer_from_resource(resources[2].id,PLACEMENT_PARTICLE)
    a.layer_transform.set_keyframe("rotation_z",5,45);b.layer_transform.set_keyframe("opacity",10,.5);c.particle_settings.motion.mode="orbit";c.particle_settings.motion.set_keyframe("radius_end",5,12)
    window._refresh_all();rows={item.generated_layer_id:len(window.project.layers)-1-window.project.layers.index(next(layer for layer in window.project.layers if layer.id==item.generated_layer_id)) for item in (a,b,c)}
    assert window.timeline.table.item(rows[a.generated_layer_id],5+window.timeline.FRAME_COLUMN_OFFSET).text()=="◆"
    assert window.timeline.table.item(rows[b.generated_layer_id],10+window.timeline.FRAME_COLUMN_OFFSET).text()=="◆"
    assert not b.layer_transform.tracks["opacity"].has_keyframe(5) and c.particle_settings.motion.tracks["radius_end"].has_keyframe(5)
    _close(window)


def test_layer_selection_and_frame_scrub_do_not_mutate_or_invalidate(tmp_path,monkeypatch):
    window,resources=_window(tmp_path);layers=[window.create_resource_layer_from_resource(item.id) for item in resources[:3]];snapshots=[item.to_dict() for item in layers];count=window.application_undo_stack.count();revision=window._project_edit_revision;invalidations=[];monkeypatch.setattr(window,"_invalidate_playback_cache",lambda *args,**kwargs:invalidations.append(1))
    for layer in (layers[0],layers[1],layers[2],layers[0]):
        window.select_resource_layer(layer.id);assert window.effect_library.current_composition_id()==layer.id
    for frame in (0,2,1,3):window.select_frame(frame)
    assert [item.to_dict() for item in layers]==snapshots and window.application_undo_stack.count()==count and window._project_edit_revision==revision and invalidations==[]
    _close(window)


def test_cross_layer_undo_redo_is_reverse_order(tmp_path):
    window,resources=_window(tmp_path);layers=[window.create_resource_layer_from_resource(item.id) for item in resources[:3]];base=window.application_undo_stack.count()
    for layer,name,value in ((layers[0],"rotation_z",15),(layers[1],"position_x",8),(layers[2],"opacity",.4)):
        after=deepcopy(layer.layer_transform);after.set_property(name,value);window.update_resource_layer_transform(layer.id,after)
    assert window.application_undo_stack.count()==base+3
    window.application_undo_stack.undo();assert layers[2].layer_transform.opacity==1
    window.application_undo_stack.undo();assert layers[1].layer_transform.position_x==0
    window.application_undo_stack.undo();assert layers[0].layer_transform.rotation_z==0
    window.application_undo_stack.redo();window.application_undo_stack.redo();window.application_undo_stack.redo();assert layers[0].layer_transform.rotation_z==15 and layers[1].layer_transform.position_x==8 and layers[2].layer_transform.opacity==.4
    _close(window)


def test_resource_revision_updates_only_referencing_effect_layers_and_playback(tmp_path,monkeypatch):
    window,resources=_window(tmp_path);a=window.create_resource_layer_from_resource(resources[0].id);b1=window.create_resource_layer_from_resource(resources[1].id);b2=window.create_resource_layer_from_resource(resources[1].id);c=window.create_resource_layer_from_resource(resources[2].id);calls=[];invalidations=[]
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer",lambda project,layer:calls.append(layer.id));monkeypatch.setattr(window,"_invalidate_playback_cache",lambda *args,**kwargs:invalidations.append(1))
    resources[1].touch();window.resource_composition_changed(resources[1].id)
    assert calls==[b1.id,b2.id] and a.id not in calls and c.id not in calls and invalidations==[1]
    _close(window)


def test_multi_effect_round_trip_preserves_order_duplicate_refs_and_all_state(tmp_path):
    project=Project.create_default(width=32,height=32);resources=[_resource(project,"Slash",(255,0,0)),_resource(project,"Smoke",(0,255,0)),_resource(project,"Spark",(0,0,255))];layers=[]
    for index,resource in enumerate((resources[0],resources[1],resources[1],resources[2])):
        layer=EffectResourceLayer(resource.name if index!=2 else "Smoke Right",resource.id,placement_mode=PLACEMENT_SINGLE if index==0 else PLACEMENT_PARTICLE,end_frame=3);layer.layer_transform.position_x=index*3;layer.surface_transform.rotation_z=index*5;layer.particle_settings.seed=index;layer.particle_settings.motion.mode=("linear","orbit","helix","linear")[index];layer.layer_transform.set_keyframe("rotation_z",index,index*20);layers.append(layer)
    project.effect_resource_layers=layers;data=project.to_dict();loaded=Project.from_dict(data)
    assert loaded.to_dict()==data and [item.id for item in loaded.effect_resource_layers]==[item.id for item in layers]
    assert loaded.effect_resource_layers[1].resource_composition_id==loaded.effect_resource_layers[2].resource_composition_id and loaded.effect_resource_layers[1].id!=loaded.effect_resource_layers[2].id
    assert FORMAT_VERSION==10


def test_multi_effect_direct_playback_bake_png_and_sequence_parity(tmp_path):
    window,resources=_window(tmp_path);layers=[window.create_resource_layer_from_resource(resources[0].id),window.create_resource_layer_from_resource(resources[1].id),window.create_resource_layer_from_resource(resources[2].id)]
    for layer in layers:apply_effect_resource_layer(window.project,layer)
    direct,_=render_exact_playback_frame(window.project,0);baked=window.project.compose_frame(0);assert np.array_equal(direct,baked)
    pngs=export_png_frames(window.project,tmp_path/"png");sequence=export_preview_sequence([direct],tmp_path/"sequence","Multi Effect")
    assert np.array_equal(np.array(Image.open(pngs[0]).convert("RGBA")),direct) and np.array_equal(np.array(Image.open(sequence[0]).convert("RGBA")),direct)
    _close(window)


def test_resource_used_by_effect_layer_cannot_be_deleted_then_can_after_remove(tmp_path,monkeypatch):
    window,resources=_window(tmp_path);layer=window.create_resource_layer_from_resource(resources[0].id);warnings=[];monkeypatch.setattr(QMessageBox,"warning",lambda *args,**kwargs:warnings.append(args));window.resource_editor.project=window.project;window.resource_editor.localization=window.localization
    window.resource_editor._delete_composition(resources[0].id);assert resources[0] in window.project.resource_compositions and warnings
    window.remove_resource_layer(layer.id);window.resource_editor._confirm=lambda *args:True;window.resource_editor._delete_composition(resources[0].id);assert resources[0] not in window.project.resource_compositions
    _close(window)
