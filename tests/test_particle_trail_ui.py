from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from app.models.particle_emitter import ParticleTrailSettings as Trail
from app.models.effect_resource_layer import EffectResourceLayer
from app.services.settings_service import ShortcutSettingsService
from app.services.localization_service import LocalizationService
from app.ui.main_window import MainWindow
from tests.test_particle_trail import scene
from tests.test_particle_scale_over_lifetime import _close

APP=QApplication.instance() or QApplication([])


def window(tmp_path,trail=None):
    project,emitter=scene(trail=trail or Trail(True,17,3,.625))
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    win=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"trail.ini"),QSettings.Format.IniFormat)),project)
    win.select_resource_layer(layer.id);win.application_undo_stack.clear();win.application_undo_stack.setClean();win.dirty=False;win._non_undo_dirty=False
    return win,layer


@pytest.mark.parametrize("control,value",[("trail_enabled",False),("trail_duration",24),("trail_interval",4),("trail_opacity",.3125)])
def test_accepted_one_undo_exact_redo_and_no_autokey(tmp_path,control,value):
    win,layer=window(tmp_path);before=deepcopy(layer.particle_settings);widget=getattr(win.particle_properties,control)
    (widget.setChecked if control=="trail_enabled" else widget.setValue)(value)
    APP.processEvents();after=deepcopy(layer.particle_settings)
    assert after!=before and win.application_undo_stack.count()==1 and after.motion.tracks=={}
    win.application_undo_stack.undo();assert layer.particle_settings==before
    win.application_undo_stack.redo();assert layer.particle_settings==after
    _close(win)


@pytest.mark.parametrize("language",["ko","en"])
@pytest.mark.parametrize("width,font_factor",[(280,1.0),(300,1.5)])
def test_trail_compact_form_tooltips_and_large_font(tmp_path,language,width,font_factor):
    win,layer=window(tmp_path)
    panel=win.particle_properties
    localization=LocalizationService(QSettings(str(tmp_path/"layout.ini"),QSettings.Format.IniFormat))
    localization.set_language(language)
    panel.retranslate_ui(localization)
    group=panel.trail_group
    font=group.font();font.setPointSizeF(font.pointSizeF()*font_factor);group.setFont(font)
    group.setFixedWidth(width);group.show();group.layout().activate();APP.processEvents()
    assert panel.layout.indexOf(group)<panel.layout.indexOf(panel.lifetime_group)
    for control in (panel.trail_enabled,panel.trail_duration,panel.trail_interval,panel.trail_opacity):
        label=panel.trail_form.labelForField(control)
        assert label.text() and control.toolTip()
        assert label.geometry().right()<width and control.geometry().right()<width
        assert label.fontMetrics().horizontalAdvance(label.text())<=label.width()
    assert "world" in panel.trail_duration.toolTip().lower()
    _close(win)


def test_disabled_preserves_values_and_refresh_selection_language_noop(tmp_path):
    win,layer=window(tmp_path);panel=win.particle_properties;before=deepcopy(layer.particle_settings)
    other=deepcopy(layer);other.id="b";other.particle_settings.trail=Trail(False,41,5,.3125);win.project.effect_resource_layers.append(other);win.project.repair_effect_hierarchy()
    revision=win._project_edit_revision
    for language in ("ko","en","ko"):
        l=LocalizationService(QSettings(str(tmp_path/"language.ini"),QSettings.Format.IniFormat));l.set_language(language);panel.retranslate_ui(l)
        panel.set_resource_layer(other,win.project)
        assert panel.settings().trail==other.particle_settings.trail
        assert not panel.trail_duration.isEnabled() and not panel.trail_interval.isEnabled() and not panel.trail_opacity.isEnabled()
        panel.set_resource_layer(layer,win.project);panel.set_settings(before);panel._set_motion_frame(before.motion,4)
        assert panel.settings()==before and panel.trail_duration.isEnabled()
    panel.trail_opacity.setValue(.625)
    assert layer.particle_settings==before and win.application_undo_stack.count()==0 and win._project_edit_revision==revision and not win.dirty
    _close(win)


@pytest.mark.parametrize("control,value",[("trail_duration",3),("trail_interval",17)])
def test_invalid_interval_crossing_reject_revert_without_command(tmp_path,control,value):
    win,layer=window(tmp_path);before=deepcopy(layer.particle_settings);revision=win._project_edit_revision
    getattr(win.particle_properties,control).setValue(value)
    assert layer.particle_settings==before and win.application_undo_stack.count()==0 and win._project_edit_revision==revision and not win.dirty
    assert win.particle_properties.settings()==before and win.particle_properties.trail_status.text()
    _close(win)


def test_budget_violation_toggle_rejected_without_dirty_or_command(tmp_path):
    # Valid OFF preserves an over-budget future trail; ON is explicitly rejected.
    win,layer=window(tmp_path,Trail(False,240,1,.75))
    layer.particle_settings.particle_count_min=layer.particle_settings.particle_count_max=40
    win.particle_properties.set_settings(layer.particle_settings)
    before=deepcopy(layer.particle_settings);revision=win._project_edit_revision
    win.particle_properties.trail_enabled.setChecked(True)
    assert layer.particle_settings==before and not win.particle_properties.trail_enabled.isChecked()
    assert "8192" in win.particle_properties.trail_status.text()
    assert win.application_undo_stack.count()==0 and win._project_edit_revision==revision and not win.dirty
    _close(win)
