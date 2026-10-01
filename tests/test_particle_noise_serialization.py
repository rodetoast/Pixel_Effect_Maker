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
from app.models.project import FORMAT_VERSION, Project
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP=QApplication.instance() or QApplication([])


def _project(enabled=True,strength=3.125,frequency=.0375):
    project=Project.create_default(width=16,height=16,frame_count=6)
    clip=AnimationClipAsset("dot",[np.full((1,1,4),255,dtype=np.uint8)],pivot_x=0,pivot_y=0)
    project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=6,particle_count_min=1,
        particle_count_max=1,lifetime_min=6,lifetime_max=6,speed_min=2,speed_max=2,
        origin_x=4,origin_y=4,noise_enabled=enabled,noise_strength=strength,noise_frequency=frequency)
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("noise",settings))
    project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop()
    window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop()
    window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_format17_defaults_noise_disabled_and_preserves_render():
    project,layer=_project(False)
    before=render_effect_resource_layer(project,layer)
    payload=project.to_dict();payload["format_version"]=17
    for item in payload["effect_resource_layers"]:
        item["particle_settings"].pop("noise_enabled")
        item["particle_settings"].pop("noise_strength")
        item["particle_settings"].pop("noise_frequency")
    loaded=Project.from_dict(payload);restored=loaded.effect_resource_layers[0]
    assert loaded.format_version==FORMAT_VERSION==18
    assert not restored.particle_settings.noise_enabled
    assert restored.particle_settings.noise_strength==1 and restored.particle_settings.noise_frequency==.1
    assert all(np.array_equal(a,b) for a,b in zip(before,render_effect_resource_layer(loaded,restored),strict=True))


@pytest.mark.parametrize("strength,frequency",[(0,0),(.125,.01),(3.125,.0375),(4096,1)])
def test_format18_noise_roundtrip(strength,frequency):
    project,_=_project(True,strength,frequency)
    loaded=Project.from_dict(project.to_dict());settings=loaded.effect_resource_layers[0].particle_settings
    assert loaded.format_version==18 and settings.noise_enabled
    assert settings.noise_strength==strength and settings.noise_frequency==frequency


@pytest.mark.parametrize("name,value",[
    ("noise_enabled",1),("noise_enabled","true"),("noise_strength",-.01),
    ("noise_strength",4096.01),("noise_strength",float("inf")),
    ("noise_frequency",-.01),("noise_frequency",1.01),("noise_frequency",float("nan")),
])
def test_invalid_noise_payload_rejected(name,value):
    data=_project()[1].particle_settings.to_dict();data[name]=value
    with pytest.raises(ValueError):ParticleEmitterSettings.from_dict(data)


def test_noise_inspector_selection_refresh_preserves_sentinels_and_localization(tmp_path):
    project,a=_project(True,3.125,.0375)
    b=deepcopy(a);b.id="layer-b";b.generated_layer_id=None
    b.particle_settings.noise_enabled=False;b.particle_settings.noise_strength=8.75;b.particle_settings.noise_frequency=.2
    project.effect_resource_layers.append(b);project.repair_effect_hierarchy()
    panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1))
    panel.set_resource_layer(a,project)
    assert panel.noise_enabled.isChecked() and panel.noise_strength.value()==3.125 and panel.noise_frequency.value()==.0375
    panel.set_resource_layer(b,project)
    assert not panel.noise_enabled.isChecked() and panel.noise_strength.value()==8.75 and panel.noise_frequency.value()==.2
    assert not panel.noise_strength.isEnabled() and not panel.noise_frequency.isEnabled()
    panel.set_resource_layer(a,project)
    assert panel.noise_enabled.isChecked() and panel.noise_frequency.value()==.0375 and changes==[]
    assert a.particle_settings.noise_strength==3.125 and b.particle_settings.noise_strength==8.75
    localization=LocalizationService(QSettings(str(tmp_path/"language.ini"),QSettings.Format.IniFormat),system_locale="en_US")
    panel.retranslate_ui(localization)
    assert (panel.noise_strength.minimum(),panel.noise_strength.maximum(),panel.noise_strength.decimals(),panel.noise_strength.singleStep())==(0,4096,3,.25)
    assert (panel.noise_frequency.minimum(),panel.noise_frequency.maximum(),panel.noise_frequency.decimals(),panel.noise_frequency.singleStep())==(0,1,4,.01)
    assert "deterministic" not in panel.noise_enabled.toolTip().lower() or "seed" in panel.noise_enabled.toolTip().lower()
    localization.set_language("ko");panel.retranslate_ui(localization)
    assert "노이즈" in panel.natural_motion_group.layout().labelForField(panel.noise_enabled).text()
    panel.close()


def test_noise_toggle_strength_frequency_undo_noop_refresh(tmp_path):
    project,layer=_project(False,1,.1);apply_effect_resource_layer(project,layer)
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"noise.ini"),QSettings.Format.IniFormat)),project)
    window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False
    panel=window.particle_properties;panel.set_resource_layer(layer,project);panel.set_settings(layer.particle_settings)
    assert window.application_undo_stack.count()==0
    panel.noise_enabled.setChecked(True);APP.processEvents()
    assert window.application_undo_stack.count()==1 and layer.particle_settings.noise_enabled
    panel.noise_strength.setValue(3.125);APP.processEvents()
    assert window.application_undo_stack.count()==2 and layer.particle_settings.noise_strength==3.125
    panel.noise_frequency.setValue(.0375);APP.processEvents()
    assert window.application_undo_stack.count()==3 and layer.particle_settings.noise_frequency==.0375
    panel.noise_frequency.setValue(.0375);panel.set_settings(layer.particle_settings);APP.processEvents()
    assert window.application_undo_stack.count()==3 and layer.particle_settings.motion.tracks=={}
    window.application_undo_stack.undo();assert layer.particle_settings.noise_frequency==.1
    window.application_undo_stack.undo();assert layer.particle_settings.noise_strength==1
    window.application_undo_stack.undo();assert not layer.particle_settings.noise_enabled
    for _ in range(3):window.application_undo_stack.redo()
    assert layer.particle_settings.noise_enabled and layer.particle_settings.noise_strength==3.125 and layer.particle_settings.noise_frequency==.0375
    _close(window)
