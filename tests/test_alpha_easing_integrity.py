from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings, ParticleMotionSettings
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.project_io import load_project, save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP = QApplication.instance() or QApplication([])
EASINGS = ("Linear", "Ease In", "Ease Out", "Ease In/Out")


def _project():
    from app.models.project import Project
    project=Project.create_default(width=16,height=16,frame_count=8)
    pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[1,1]=[255,255,255,255]
    asset=SourceAsset("spark",pixels,pivot_x=1,pivot_y=1)
    composition=ResourceComposition("spark",3,3,12,1,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,0,pivot_x=1,pivot_y=1))
    project.source_assets.append(asset);project.resource_compositions.append(composition)
    return project,composition


def _window(tmp_path):
    project,composition=_project()
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"alpha.ini"),QSettings.Format.IniFormat)),project)
    a=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    b=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False
    return window,a,b


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop()
    window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop()
    window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


@pytest.mark.parametrize("easing",EASINGS)
def test_alpha_easing_refresh_does_not_mutate_model(easing):
    project,composition=_project();settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",easing=easing)
    emitter=ParticleEmitter("alpha",settings);panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1))
    before=deepcopy(settings.to_dict())
    for _ in range(3):panel.set_emitter(emitter,project);panel.set_settings(settings)
    assert panel.alpha_easing.currentData()==easing
    assert panel.settings().easing==easing and settings.to_dict()==before and changes==[]
    panel.close()


def test_alpha_easing_selection_change_preserves_value_and_pushes_no_undo(tmp_path):
    window,a,b=_window(tmp_path);a.particle_settings.easing="Ease Out";b.particle_settings.easing="Ease In"
    window.particle_preview_manager.revert(a.as_particle_emitter());window.particle_preview_manager.revert(b.as_particle_emitter())
    before=[deepcopy(item.particle_settings.to_dict()) for item in (a,b)];count=window.application_undo_stack.count();revision=window._project_edit_revision
    window.select_resource_layer(a.id);window.select_resource_layer(b.id);window.select_resource_layer(a.id);APP.processEvents()
    assert [item.particle_settings.to_dict() for item in (a,b)]==before
    assert window.particle_properties.alpha_easing.currentData()=="Ease Out"
    assert window.application_undo_stack.count()==count and window._project_edit_revision==revision and not window.dirty
    _close(window)


@pytest.mark.parametrize("easing",EASINGS)
def test_alpha_easing_save_reload_and_inspector_refresh_preserve_exact(tmp_path,easing):
    project,composition=_project();settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",easing=easing)
    from app.models.effect_resource_layer import EffectResourceLayer
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("alpha",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    loaded=load_project(save_project(project,tmp_path/(easing.replace("/","-")+".peffect.json")))
    restored=loaded.effect_resource_layers[0].particle_settings;panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1));panel.set_emitter(loaded.effect_resource_layers[0].as_particle_emitter(),loaded)
    assert restored.easing==panel.alpha_easing.currentData()==panel.settings().easing==easing and changes==[]
    panel.close()


def test_alpha_easing_user_edit_is_one_undo_and_redo_exact(tmp_path):
    window,a,_=_window(tmp_path);window.select_resource_layer(a.id);panel=window.particle_properties
    panel.alpha_easing.setCurrentIndex(panel.alpha_easing.findData("Ease Out"));APP.processEvents()
    assert a.particle_settings.easing=="Ease Out" and window.application_undo_stack.count()==1
    window.application_undo_stack.undo();assert a.particle_settings.easing=="Linear"
    window.application_undo_stack.redo();assert a.particle_settings.easing=="Ease Out"
    _close(window)


def test_non_alpha_easing_controls_do_not_share_corruption_pattern():
    project,composition=_project();motion=ParticleMotionSettings(mode="helix",radius_easing="Ease In",angle_easing="Ease Out",axis_easing="Ease In/Out")
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",easing="Ease Out",motion=motion)
    panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1));panel.set_emitter(ParticleEmitter("motion",settings),project)
    for _ in range(3):panel.set_settings(settings)
    restored=panel.settings()
    assert (restored.motion.radius_easing,restored.motion.angle_easing,restored.motion.axis_easing)==("Ease In","Ease Out","Ease In/Out")
    assert restored.easing=="Ease Out" and changes==[]
    panel.close()
