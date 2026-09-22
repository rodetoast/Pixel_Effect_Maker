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
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP=QApplication.instance() or QApplication([])


def _project(enabled=True,strength=1.375):
    project=Project.create_default(width=16,height=16,frame_count=6);clip=AnimationClipAsset("dot",[np.full((1,1,4),255,dtype=np.uint8)],pivot_x=0,pivot_y=0);project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=6,particle_count_min=1,particle_count_max=1,lifetime_min=6,lifetime_max=6,speed_min=0,speed_max=0,origin_x=4,origin_y=4,gravity_enabled=enabled,gravity_strength=strength)
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("gravity",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy();return project,layer


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_format15_defaults_gravity_disabled_and_preserves_old_render():
    project,layer=_project(False,0);before=render_effect_resource_layer(project,layer);payload=project.to_dict();payload["format_version"]=15
    for item in payload["effect_resource_layers"]:
        item["particle_settings"].pop("gravity_enabled");item["particle_settings"].pop("gravity_strength")
    loaded=Project.from_dict(payload);restored=loaded.effect_resource_layers[0]
    assert loaded.format_version==FORMAT_VERSION==16
    assert not restored.particle_settings.gravity_enabled and restored.particle_settings.gravity_strength==0
    assert all(np.array_equal(a,b) for a,b in zip(before,render_effect_resource_layer(loaded,restored),strict=True))


@pytest.mark.parametrize("strength",[1.375,-.625,0.0])
def test_format16_gravity_round_trip_is_exact(strength):
    project,_layer=_project(True,strength);loaded=Project.from_dict(project.to_dict());actual=loaded.effect_resource_layers[0].particle_settings
    assert loaded.to_dict()["format_version"]==16 and actual.gravity_enabled and actual.gravity_strength==strength


@pytest.mark.parametrize(("field","value"),[("gravity_enabled",1),("gravity_enabled","true"),("gravity_strength",float("nan")),("gravity_strength",float("inf")),("gravity_strength",1024.001),("gravity_strength",-1024.001)])
def test_corrupt_gravity_values_are_rejected(field,value):
    data=_project()[1].particle_settings.to_dict();data[field]=value
    with pytest.raises(ValueError):ParticleEmitterSettings.from_dict(data)


def test_gravity_inspector_refresh_and_selection_preserve_sentinels_without_changes():
    project,a=_project(True,1.375);b=deepcopy(a);b.id="layer-b";b.generated_layer_id=None;b.particle_settings.gravity_enabled=False;b.particle_settings.gravity_strength=-.625;project.effect_resource_layers.append(b);project.repair_effect_hierarchy()
    panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1))
    panel.set_resource_layer(a,project);assert panel.gravity_enabled.isChecked() and panel.gravity_strength.value()==1.375
    panel.set_resource_layer(b,project);assert not panel.gravity_enabled.isChecked() and panel.gravity_strength.value()==-.625 and not panel.gravity_strength.isEnabled()
    panel.set_resource_layer(a,project);assert panel.gravity_enabled.isChecked() and panel.gravity_strength.value()==1.375 and changes==[]
    assert a.particle_settings.gravity_strength==1.375 and b.particle_settings.gravity_strength==-.625
    panel.close()


def test_gravity_ui_contract_tooltips_and_numeric_policy(tmp_path):
    project,layer=_project(False,-.625);panel=ParticlePropertiesPanel();panel.set_resource_layer(layer,project)
    from app.services.localization_service import LocalizationService
    localization=LocalizationService(QSettings(str(tmp_path/"localization.ini"),QSettings.Format.IniFormat),system_locale="en_US")
    panel.retranslate_ui(localization);groups={title:group for title,group,_form,_records in panel._group_records}
    assert groups["Natural Motion"] is panel.natural_motion_group and panel.gravity_strength not in [widget for _name,widget in next(records for title,_group,_form,records in panel._group_records if title=="Over Lifetime")]
    assert (panel.gravity_strength.minimum(),panel.gravity_strength.maximum(),panel.gravity_strength.decimals(),panel.gravity_strength.singleStep())==(-1024,1024,3,.125)
    assert panel.gravity_strength.suffix()==" px/frame²" and "birth" in panel.gravity_enabled.toolTip().lower()
    localization.set_language("ko");panel.retranslate_ui(localization);assert panel.natural_motion_group.title()=="자연스러운 움직임" and "생성된 순간" in panel.gravity_enabled.toolTip()
    panel.close()


def test_gravity_toggle_and_strength_each_make_one_undo_noop_and_refresh_make_none(tmp_path):
    project,layer=_project(False,-.625);apply_effect_resource_layer(project,layer)
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"gravity.ini"),QSettings.Format.IniFormat)),project);window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False
    panel=window.particle_properties
    panel.set_resource_layer(layer,project);panel.set_settings(layer.particle_settings);assert window.application_undo_stack.count()==0
    panel.gravity_enabled.setChecked(True);APP.processEvents();assert window.application_undo_stack.count()==1 and layer.particle_settings.gravity_enabled
    panel.gravity_strength.setValue(1.375);APP.processEvents();assert window.application_undo_stack.count()==2 and layer.particle_settings.gravity_strength==1.375
    panel.gravity_strength.setValue(panel.gravity_strength.value());panel.set_settings(layer.particle_settings);APP.processEvents();assert window.application_undo_stack.count()==2 and layer.particle_settings.motion.tracks=={}
    window.application_undo_stack.undo();assert layer.particle_settings.gravity_strength==-.625
    window.application_undo_stack.undo();assert not layer.particle_settings.gravity_enabled
    window.application_undo_stack.redo();window.application_undo_stack.redo();assert layer.particle_settings.gravity_enabled and layer.particle_settings.gravity_strength==1.375
    _close(window)
