from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings
from app.models.project import FORMAT_VERSION,Project
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP=QApplication.instance() or QApplication([])


def _project(enabled=True,strength=.1375):
    project=Project.create_default(width=16,height=16,frame_count=6)
    clip=AnimationClipAsset("dot",[np.full((1,1,4),255,dtype=np.uint8)],pivot_x=0,pivot_y=0);project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=6,particle_count_min=1,particle_count_max=1,lifetime_min=6,lifetime_max=6,speed_min=2,speed_max=2,origin_x=4,origin_y=4,drag_enabled=enabled,drag_strength=strength)
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("drag",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_format16_defaults_drag_disabled_and_preserves_render():
    project,layer=_project(False,0);before=render_effect_resource_layer(project,layer);payload=project.to_dict();payload["format_version"]=16
    for item in payload["effect_resource_layers"]:
        item["particle_settings"].pop("drag_enabled");item["particle_settings"].pop("drag_strength")
    loaded=Project.from_dict(payload);restored=loaded.effect_resource_layers[0]
    assert loaded.format_version==FORMAT_VERSION==22 and not restored.particle_settings.drag_enabled and restored.particle_settings.drag_strength==0
    assert all(np.array_equal(a,b) for a,b in zip(before,render_effect_resource_layer(loaded,restored),strict=True))


@pytest.mark.parametrize("strength",[0,.03125,.1375,10])
def test_format17_drag_round_trip(strength):
    project,_=_project(True,strength);loaded=Project.from_dict(project.to_dict());settings=loaded.effect_resource_layers[0].particle_settings
    assert loaded.format_version==22 and settings.drag_enabled and settings.drag_strength==strength


@pytest.mark.parametrize(("name","value"),[("drag_enabled",1),("drag_enabled","true"),("drag_strength",-.01),("drag_strength",10.01),("drag_strength",float("inf")),("drag_strength",float("nan"))])
def test_invalid_drag_is_rejected(name,value):
    data=_project()[1].particle_settings.to_dict();data[name]=value
    with pytest.raises(ValueError):ParticleEmitterSettings.from_dict(data)


def test_drag_inspector_selection_refresh_preserves_sentinels(tmp_path):
    project,a=_project(True,.1375);b=deepcopy(a);b.id="layer-b";b.generated_layer_id=None;b.particle_settings.drag_enabled=False;b.particle_settings.drag_strength=.03125;project.effect_resource_layers.append(b);project.repair_effect_hierarchy()
    panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1))
    panel.set_resource_layer(a,project);assert panel.drag_enabled.isChecked() and panel.drag_strength.value()==.1375
    panel.set_resource_layer(b,project);assert not panel.drag_enabled.isChecked() and panel.drag_strength.value()==.03125 and not panel.drag_strength.isEnabled()
    panel.set_resource_layer(a,project);assert panel.drag_enabled.isChecked() and panel.drag_strength.value()==.1375 and changes==[]
    assert a.particle_settings.drag_strength==.1375 and b.particle_settings.drag_strength==.03125
    localization=LocalizationService(QSettings(str(tmp_path/"language.ini"),QSettings.Format.IniFormat),system_locale="en_US")
    panel.retranslate_ui(localization)
    assert (panel.drag_strength.minimum(),panel.drag_strength.maximum(),panel.drag_strength.decimals(),panel.drag_strength.singleStep())==(0,10,5,.01)
    assert "gravity" in panel.drag_enabled.toolTip().lower()
    localization.set_language("ko");panel.retranslate_ui(localization)
    assert "감쇠" in panel.natural_motion_group.layout().labelForField(panel.drag_enabled).text()
    panel.close()


def test_drag_toggle_strength_undo_noop_and_refresh(tmp_path):
    project,layer=_project(False,.03125);apply_effect_resource_layer(project,layer)
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"drag.ini"),QSettings.Format.IniFormat)),project);window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False
    panel=window.particle_properties;panel.set_resource_layer(layer,project);panel.set_settings(layer.particle_settings)
    assert window.application_undo_stack.count()==0
    panel.drag_enabled.setChecked(True);APP.processEvents();assert window.application_undo_stack.count()==1 and layer.particle_settings.drag_enabled
    panel.drag_strength.setValue(.1375);APP.processEvents();assert window.application_undo_stack.count()==2 and layer.particle_settings.drag_strength==.1375
    panel.drag_strength.setValue(.1375);panel.set_settings(layer.particle_settings);APP.processEvents();assert window.application_undo_stack.count()==2 and layer.particle_settings.motion.tracks=={}
    window.application_undo_stack.undo();assert layer.particle_settings.drag_strength==.03125
    window.application_undo_stack.undo();assert not layer.particle_settings.drag_enabled
    window.application_undo_stack.redo();window.application_undo_stack.redo();assert layer.particle_settings.drag_enabled and layer.particle_settings.drag_strength==.1375
    _close(window)
