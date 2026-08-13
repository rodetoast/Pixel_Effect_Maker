from __future__ import annotations

from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectLayerTransform3D, EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_playback_service import playback_relevant_revision, render_exact_playback_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.preview_export_service import export_preview_sequence
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def _project():
    project=Project.create_default(width=24,height=24,fps=12,frame_count=3);pixels=np.zeros((7,7,4),dtype=np.uint8);pixels[1:6,1:6]=[240,80,20,220];asset=SourceAsset("sprite",pixels,pivot_x=3,pivot_y=3);composition=ResourceComposition("sprite",7,7,12,3,True);composition.layers.append(CompositionLayer("sprite","source_asset",asset.id,0,2,pivot_x=3,pivot_y=3));project.source_assets.append(asset);project.resource_compositions.append(composition);layer=EffectResourceLayer("effect",composition.id,end_frame=2);layer.single_settings.start_x=layer.single_settings.end_x=12;layer.single_settings.start_y=layer.single_settings.end_y=12;return project,composition,layer


def test_advanced_off_bypasses_system_and_surface_and_on_restores_exact():
    project,_,layer=_project();layer.layer_transform.position_x=5;layer.layer_transform.rotation_y=35;layer.surface_transform.rotation_z=25;layer.surface_transform.perspective_strength=.2
    enabled=render_effect_resource_layer_current_frame(project,layer,0);stored=(deepcopy(layer.layer_transform),deepcopy(layer.surface_transform));layer.advanced_transform_enabled=False;disabled=render_effect_resource_layer_current_frame(project,layer,0)
    identity=deepcopy(layer);identity.layer_transform=EffectLayerTransform3D();identity.surface_transform=EffectLayerTransform3D();identity.advanced_transform_enabled=True
    assert np.array_equal(disabled,render_effect_resource_layer_current_frame(project,identity,0)) and not np.array_equal(enabled,disabled)
    assert layer.layer_transform==stored[0] and layer.surface_transform==stored[1]
    layer.advanced_transform_enabled=True;assert np.array_equal(render_effect_resource_layer_current_frame(project,layer,0),enabled)


def test_advanced_off_preserves_tracks_and_legacy_defaults_enabled():
    project,_,layer=_project();layer.layer_transform.set_keyframe("rotation_z",0,0);layer.layer_transform.set_keyframe("rotation_z",2,720);layer.surface_transform.set_keyframe("opacity",1,.5);layer.advanced_transform_enabled=False;data=project.to_dict();data["effect_resource_layers"]=[layer.to_dict()];loaded=Project.from_dict(data).effect_resource_layers[0]
    assert not loaded.advanced_transform_enabled and loaded.layer_transform.tracks["rotation_z"].keyframe_at(2).value==720 and loaded.surface_transform.tracks["opacity"].keyframe_at(1).value==.5
    legacy=layer.to_dict();legacy.pop("advanced_transform_enabled");assert EffectResourceLayer.from_dict(legacy).advanced_transform_enabled and FORMAT_VERSION==9


def test_advanced_state_is_independent_and_particle_motion_remains_enabled():
    project,composition,a=_project();b=EffectResourceLayer("particle",composition.id,placement_mode=PLACEMENT_PARTICLE,end_frame=2);b.particle_settings.motion.mode="orbit";b.particle_settings.motion.radius_end=9;c=deepcopy(a);c.id="third";a.advanced_transform_enabled=True;b.advanced_transform_enabled=False;c.advanced_transform_enabled=True
    assert [item.advanced_transform_enabled for item in (a,b,c)]==[True,False,True] and b.particle_settings.motion.mode=="orbit" and b.particle_settings.motion.radius_end==9


def test_advanced_flag_participates_in_playback_revision():
    project,_,layer=_project();project.effect_resource_layers.append(layer);before=playback_relevant_revision(project);layer.advanced_transform_enabled=False
    assert playback_relevant_revision(project)!=before


def test_advanced_toggle_is_one_undo_dirty_invalidates_and_disables_gizmo(tmp_path,monkeypatch):
    project,composition,_=_project();window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"advanced.ini"),QSettings.Format.IniFormat)),initial_project=project);layer=window.create_resource_layer_from_resource(composition.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False;calls=[];real=window._invalidate_playback_cache;monkeypatch.setattr(window,"_invalidate_playback_cache",lambda *args,**kwargs:calls.append(1) or real(*args,**kwargs));before=window.application_undo_stack.count()
    window.composition_layer_properties.transform_panel.setChecked(False);APP.processEvents()
    assert not layer.advanced_transform_enabled and window.application_undo_stack.count()==before+1 and window.dirty and calls and window.canvas.resource_transform is None
    assert not window.composition_layer_properties.transform_panel.system_group.isEnabled() and layer.layer_transform==EffectLayerTransform3D()
    window.application_undo_stack.undo();assert layer.advanced_transform_enabled and window.canvas.resource_transform is not None
    window.application_undo_stack.redo();assert not layer.advanced_transform_enabled and window.canvas.resource_transform is None
    window.dirty=False;window.close()


def test_advanced_off_motion_guide_uses_identity_system_space(tmp_path):
    project,composition,_=_project();window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"guide.ini"),QSettings.Format.IniFormat)),initial_project=project);layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);layer.layer_transform.position_x=100;window.select_resource_layer(layer.id);assert window.canvas.resource_transform is not None
    window.set_resource_layer_advanced_enabled(layer.id,False);assert window.canvas.resource_transform is None and window.canvas.effect_guide_id==layer.id
    window.dirty=False;window.close()


def test_advanced_off_direct_playback_bake_png_and_sequence_are_identical(tmp_path):
    project,_,layer=_project();layer.layer_transform.rotation_z=720;layer.surface_transform.position_x=5;layer.advanced_transform_enabled=False;project.effect_resource_layers.append(layer);apply_effect_resource_layer(project,layer)
    direct=render_effect_resource_layer_current_frame(project,layer,0);playback,_=render_exact_playback_frame(project,0);baked=project.compose_frame(0)
    png=export_png_frames(project,tmp_path/"png")[0];sequence=export_preview_sequence([playback],tmp_path/"sequence","Advanced Off")[0]
    assert np.array_equal(direct,playback) and np.array_equal(playback,baked)
    assert np.array_equal(np.array(Image.open(png).convert("RGBA")),playback) and np.array_equal(np.array(Image.open(sequence).convert("RGBA")),playback)
