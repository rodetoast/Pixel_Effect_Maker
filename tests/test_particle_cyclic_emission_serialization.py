from __future__ import annotations
from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.project import FORMAT_VERSION,Project
from app.services.project_io import save_project,load_project
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from tests.test_particle_cyclic_emission import setup

APP=QApplication.instance() or QApplication([])


def fixture(**changes):
    project,emitter=setup(**changes)
    layer=EffectResourceLayer.from_particle_emitter(emitter)
    project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


@pytest.mark.parametrize("mode,period",[("one_shot",41),("cyclic_steady",6),("cyclic_steady",17),("cyclic_steady",512)])
def test_format19_roundtrip_regeneration(tmp_path,mode,period):
    project,layer=fixture(emission_cycle_mode=mode,emission_period_frames=period)
    expected=render_effect_resource_layer(project,layer)
    saved=save_project(project,tmp_path/"roundtrip.peffect.json")
    loaded=load_project(saved);actual=loaded.effect_resource_layers[0]
    assert FORMAT_VERSION==21 and loaded.format_version==21
    assert actual.particle_settings.emission_cycle_mode==mode and actual.particle_settings.emission_period_frames==period
    assert actual.particle_settings.to_dict()==layer.particle_settings.to_dict()
    assert all(np.array_equal(a,b) for a,b in zip(expected,render_effect_resource_layer(loaded,actual),strict=True))


def test_format18_defaults_one_shot_and_load_does_not_rewrite(tmp_path):
    import json
    project,layer=fixture(emission_cycle_mode="one_shot")
    expected=render_effect_resource_layer(project,layer)
    data=project.to_dict();data["format_version"]=18
    for item in data["effect_resource_layers"]:
        item["particle_settings"].pop("emission_cycle_mode");item["particle_settings"].pop("emission_period_frames")
    path=tmp_path/"legacy.json";path.write_text(json.dumps(data),encoding="utf-8")
    before=path.read_bytes();loaded=load_project(path);s=loaded.effect_resource_layers[0].particle_settings
    assert path.read_bytes()==before and loaded.format_version==21
    assert s.emission_cycle_mode=="one_shot" and s.emission_period_frames==24
    assert all(np.array_equal(a,b) for a,b in zip(expected,render_effect_resource_layer(loaded,loaded.effect_resource_layers[0]),strict=True))


def test_inspector_refresh_selection_and_localization(tmp_path):
    project,a=fixture(emission_period_frames=17)
    b=deepcopy(a);b.id="b";b.generated_layer_id=None
    b.particle_settings.emission_cycle_mode="one_shot";b.particle_settings.emission_period_frames=41
    project.effect_resource_layers.append(b);project.repair_effect_hierarchy()
    before=deepcopy(project.to_dict());panel=ParticlePropertiesPanel();events=[]
    panel.draft_changed.connect(lambda *_:events.append(1))
    for layer in (a,b,a):
        panel.set_resource_layer(layer,project)
        assert panel.settings().to_dict()==layer.particle_settings.to_dict()
        assert panel.emission_period_frames.isEnabled()==(layer is a)
    assert not events and project.to_dict()==before
    l=LocalizationService(QSettings(str(tmp_path/"l.ini"),QSettings.Format.IniFormat),system_locale="en_US")
    panel.retranslate_ui(l)
    assert panel.emission_cycle_mode.itemText(0)=="One Shot"
    assert panel.emission_cycle_mode.itemText(1)=="Cyclic Steady"
    assert "previous-cycle" in panel.emission_cycle_mode.toolTip()
    assert "parent" in panel.emission_period_frames.toolTip()
    assert "per second" in panel.count_max.toolTip()
    l.set_language("ko");panel.retranslate_ui(l)
    assert panel.emission_cycle_mode.itemText(0)=="한 번만" and panel.emission_cycle_mode.itemText(1)=="지속 반복"
    assert "부모" in panel.cycle_status.text() and "24" not in panel.cycle_status.text()
    assert project.to_dict()==before and not events
    panel.close()


def test_mode_period_undo_noop_refresh_and_invalid_revert(tmp_path):
    project,layer=fixture(emission_cycle_mode="one_shot",emission_period_frames=24,emission_mode="over_time",emission_duration=3)
    apply_effect_resource_layer(project,layer)
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"w.ini"),QSettings.Format.IniFormat)),project)
    try:
        window.select_resource_layer(layer.id)
        stack=window.application_undo_stack;stack.clear();stack.setClean();window.dirty=False;window._non_undo_dirty=False
        panel=window.particle_properties;panel.set_resource_layer(layer,project)
        panel.emission_cycle_mode.setCurrentIndex(panel.emission_cycle_mode.findData("cyclic_steady"));APP.processEvents()
        assert stack.count()==1 and layer.particle_settings.emission_cycle_mode=="cyclic_steady"
        panel.emission_period_frames.setValue(6);APP.processEvents()
        assert stack.count()==2 and layer.particle_settings.emission_period_frames==6
        panel.emission_period_frames.setValue(12);APP.processEvents()
        assert stack.count()==3 and layer.particle_settings.emission_period_frames==12
        revision=window._project_edit_revision;dirty=window.dirty
        panel.emission_period_frames.setValue(12);panel.set_resource_layer(layer,project)
        window.update_particle_draft(layer.id,deepcopy(layer.particle_settings));APP.processEvents()
        assert stack.count()==3 and window._project_edit_revision==revision and window.dirty==dirty
        snapshot=deepcopy(project.to_dict())
        panel.emission_period_frames.setValue(1);APP.processEvents()
        assert panel.emission_period_frames.value()==12 and layer.particle_settings.emission_period_frames==12
        assert stack.count()==3 and project.to_dict()==snapshot and panel.cycle_status.text()
        assert window._project_edit_revision==revision and window.dirty==dirty
        stack.undo();assert layer.particle_settings.emission_period_frames==6
        stack.undo();assert layer.particle_settings.emission_period_frames==24
        stack.undo();assert layer.particle_settings.emission_cycle_mode=="one_shot"
        assert not panel.emission_period_frames.isEnabled()
        for _ in range(3):stack.redo()
        assert layer.particle_settings.emission_cycle_mode=="cyclic_steady" and layer.particle_settings.emission_period_frames==12
    finally:
        window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop()
        window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop()
        window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()
