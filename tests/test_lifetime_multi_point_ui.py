from copy import deepcopy
from unittest.mock import patch
import math
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from app.models.particle_emitter import LifetimeColorModulation, LifetimeScalarModulation
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.lifetime_point_editor import LifetimePointEditor
from app.ui.main_window import MainWindow
from tests.test_particle_scale_over_lifetime import _project, _close
from tests.test_lifetime_multi_point import curves

APP=QApplication.instance() or QApplication([])


@pytest.mark.parametrize("channel",["scale","opacity","color"])
def test_point_editor_add_remove_endpoints_limits_and_final_easing(channel):
    editor=LifetimePointEditor(channel)
    changes=[];editor.changed.connect(lambda:changes.append(1))
    before=deepcopy(editor.curve);assert editor.add_point()
    assert len(editor.curve.points)==3 and editor.curve.points[1].time==.5
    assert editor.curve.points[1].easing_to_next=="Linear"
    assert editor.remove_point() and editor.curve==before and len(changes)==2
    editor.list.setCurrentRow(0)
    assert not editor.time.isEnabled() and not editor.remove.isEnabled()
    assert not editor.edit_point("time",.1) and not editor.remove_point()
    editor.list.setCurrentRow(1)
    assert not editor.easing.isEnabled() and not editor.edit_point("easing_to_next","Ease In")
    for _ in range(6):assert editor.add_point()
    assert len(editor.curve.points)==8 and not editor.add.isEnabled() and not editor.add_point()
    editor.close()


@pytest.mark.parametrize("time",[0,1,-.1,1.1,math.nan,math.inf])
def test_point_time_invalid_reverts_no_change(time):
    editor=LifetimePointEditor("scale");editor.add_point();before=deepcopy(editor.curve)
    changes=[];editor.changed.connect(lambda:changes.append(1))
    assert not editor.edit_point("time",time)
    assert editor.curve==before and changes==[] and editor.status.text()
    assert editor.edit_point("time",.37)
    assert editor.curve.points[1].time==.37 and len(changes)==1
    editor.close()


def test_color_picker_cancel_rgb_only_noop_and_segment_easing():
    editor=LifetimePointEditor("color");before=deepcopy(editor.curve);changes=[]
    editor.changed.connect(lambda:changes.append(1))
    with patch("app.ui.lifetime_point_editor.QColorDialog.getColor",return_value=QColor()):editor.choose_color()
    assert editor.curve==before and changes==[]
    with patch("app.ui.lifetime_point_editor.QColorDialog.getColor",return_value=QColor(255,255,255,10)):editor.choose_color()
    assert changes==[]
    with patch("app.ui.lifetime_point_editor.QColorDialog.getColor",return_value=QColor(241,162,3,10)):editor.choose_color()
    assert editor.curve.points[0].rgb==(241,162,3) and len(changes)==1
    assert editor.edit_point("easing_to_next","Ease Out") and len(changes)==2
    assert "alpha" not in str(editor.curve.to_dict())
    editor.close()


def window(tmp_path):
    project,layer=_project();curves(layer.particle_settings)
    result=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"points.ini"),QSettings.Format.IniFormat)),project)
    result.select_resource_layer(layer.id);result.application_undo_stack.clear();result.application_undo_stack.setClean();result.dirty=False;result._non_undo_dirty=False
    return result,layer


@pytest.mark.parametrize("channel,action",[
    ("scale","add"),("scale","remove"),("scale","time"),("scale","value"),("scale","easing"),
    ("opacity","add"),("opacity","remove"),("opacity","time"),("opacity","value"),("opacity","easing"),
    ("color","add"),("color","remove"),("color","time"),("color","rgb"),("color","easing"),
])
def test_point_action_one_undo_exact_redo_and_no_autokey(tmp_path,channel,action):
    win,layer=window(tmp_path);panel=win.particle_properties;editor=getattr(panel,channel+"_point_editor")
    before=deepcopy(layer.particle_settings);editor.list.setCurrentRow(1)
    if action=="add":assert editor.add_point()
    elif action=="remove":assert editor.remove_point()
    else:assert editor.edit_point({"easing":"easing_to_next"}.get(action,action),{"time":.31,"value":.53,"easing":"Ease In/Out","rgb":(23,201,228)}[action])
    APP.processEvents();after=deepcopy(layer.particle_settings)
    assert before!=after and win.application_undo_stack.count()==1
    assert layer.particle_settings.motion.tracks=={}
    win.application_undo_stack.undo();assert layer.particle_settings==before
    win.application_undo_stack.redo();assert layer.particle_settings==after
    _close(win)


def test_refresh_selection_localization_scrub_preserve_sentinel_no_dirty_undo_revision(tmp_path):
    win,layer=window(tmp_path);panel=win.particle_properties
    before=deepcopy(layer.particle_settings);revision=win._project_edit_revision
    other=deepcopy(layer);other.id="other";other.name="Other";other.particle_settings.scale_over_lifetime=LifetimeScalarModulation()
    other.particle_settings.color_over_lifetime=LifetimeColorModulation()
    win.project.effect_resource_layers.append(other);win.project.repair_effect_hierarchy()
    for language in ("ko","en","ko"):
        localization=LocalizationService(QSettings(str(tmp_path/"language.ini"),QSettings.Format.IniFormat));localization.set_language(language)
        panel.retranslate_ui(localization)
        panel.set_resource_layer(other,win.project)
        panel.set_resource_layer(layer,win.project)
        panel._motion_frame=4;panel._set_motion_frame(before.motion,4)
        panel.set_settings(before)
        assert panel.settings()==before and layer.particle_settings==before
    assert win.application_undo_stack.count()==0 and win._project_edit_revision==revision and not win.dirty
    for editor in panel._point_editors:
        editor.list.setCurrentRow(1)
        value=editor.curve.points[1]
        assert not editor.edit_point("time",value.time)
    assert win.application_undo_stack.count()==0 and win._project_edit_revision==revision
    _close(win)


@pytest.mark.parametrize("channel",["scale","color"])
def test_enabled_each_user_action_one_undo(tmp_path,channel):
    win,layer=window(tmp_path);before=deepcopy(layer.particle_settings)
    getattr(win.particle_properties,channel+"_lifetime_enabled").setChecked(False)
    assert win.application_undo_stack.count()==1
    win.application_undo_stack.undo();assert layer.particle_settings==before
    _close(win)
