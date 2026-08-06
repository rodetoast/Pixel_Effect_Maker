import os
from copy import deepcopy

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import pytest
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleMotionSettings
from app.models.resource_composition import ResourceComposition
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP=QApplication.instance() or QApplication([])


def window_context(tmp_path):
    service=ShortcutSettingsService(QSettings(str(tmp_path/"motion.ini"),QSettings.Format.IniFormat));window=MainWindow(service)
    composition=ResourceComposition("motion",width=16,height=16,frame_count=8);window.project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);layer.particle_settings.motion=ParticleMotionSettings(mode="orbit",radius_start=12,radius_end=24,turns=1);window.particle_preview_manager.revert(layer.as_particle_emitter())
    window.select_resource_layer(layer.id);window.canvas.resize(700,500);window.show();APP.processEvents();return window,layer


def test_motion_mode_disables_linear_and_enables_orbit_fields():
    panel=ParticlePropertiesPanel();project=__import__("app.models.project",fromlist=["Project"]).Project.create_default();composition=ResourceComposition("c");project.resource_compositions.append(composition);layer=EffectResourceLayer("p",composition.id,placement_mode=PLACEMENT_PARTICLE)
    panel.set_resource_layer(layer,project);assert panel.direction_group.isEnabled() and not panel.motion_radius_start.isEnabled()
    panel.motion_mode.setCurrentIndex(panel.motion_mode.findData("orbit"));assert not panel.direction_group.isEnabled() and panel.motion_radius_start.isEnabled() and not panel.motion_axis_end.isEnabled()
    panel.motion_mode.setCurrentIndex(panel.motion_mode.findData("helix"));assert panel.motion_axis_end.isEnabled()


def test_motion_reset_preserves_animation_tracks():
    panel=ParticlePropertiesPanel();project=__import__("app.models.project",fromlist=["Project"]).Project.create_default();composition=ResourceComposition("c");project.resource_compositions.append(composition);layer=EffectResourceLayer("p",composition.id,placement_mode=PLACEMENT_PARTICLE)
    layer.particle_settings.motion=ParticleMotionSettings(mode="orbit",radius_start=50);layer.particle_settings.motion.set_keyframe("radius_start",3,80)
    panel.set_resource_layer(layer,project);panel.reset_motion.click();result=panel.settings().motion
    assert result.mode=="linear" and result.radius_start==0 and result.value("radius_start",3)==80


def test_motion_center_radius_and_shift_angle_handles_use_shared_settings(tmp_path):
    window,layer=window_context(tmp_path);canvas=window.canvas
    canvas._guide_handle="motion_center";canvas._move_effect_guide(QPointF(40,45),Qt.KeyboardModifier.NoModifier)
    assert canvas.effect_guide_settings.motion.center_x==pytest.approx(40-layer.particle_settings.origin_x)
    center_x=canvas.effect_guide_settings.origin_x+canvas.effect_guide_settings.motion.center_x;center_y=canvas.effect_guide_settings.origin_y+canvas.effect_guide_settings.motion.center_y
    canvas._guide_handle="radius_start";canvas._move_effect_guide(QPointF(center_x+30,center_y),Qt.KeyboardModifier.NoModifier);assert canvas.effect_guide_settings.motion.radius_start==30
    canvas._guide_handle="start_angle";canvas._move_effect_guide(QPointF(center_x+20,center_y+7),Qt.KeyboardModifier.ShiftModifier);assert canvas.effect_guide_settings.motion.start_angle_degrees%15==0
    window.dirty=False;window.close()


def test_motion_canvas_drag_creates_one_undo_and_escape_creates_none(tmp_path):
    window,layer=window_context(tmp_path);canvas=window.canvas;center=canvas._guide_points()["motion_center"].toPoint();before=window.application_undo_stack.count()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=center);QTest.mouseMove(canvas,center+QPoint(18,12));QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=center+QPoint(18,12));APP.processEvents()
    assert window.application_undo_stack.count()==before+1
    snapshot=deepcopy(layer.particle_settings.motion.to_dict());before=window.application_undo_stack.count();start=canvas._guide_points()["radius_start"].toPoint()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(canvas,start+QPoint(30,0));QTest.keyClick(canvas,Qt.Key.Key_Escape);APP.processEvents()
    assert layer.particle_settings.motion.to_dict()==snapshot and window.application_undo_stack.count()==before
    window.dirty=False;window.close()


def test_motion_latest_wins_queue_keeps_one_layer_request(tmp_path):
    window,layer=window_context(tmp_path);window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop()
    for radius in (13,18,25):layer.particle_settings.motion.radius_start=radius;layer.particle_settings.motion.revision+=1;window._queue_particle_motion_render(layer)
    assert window._pending_particle_motion=={layer.id:(layer.particle_settings.motion.revision,window.frame_index)}
    window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window._flush_particle_motion_final();assert not window._pending_particle_motion
    window.dirty=False;window.close()


def test_explicit_motion_keyframe_button_uses_current_effect_frame(tmp_path):
    window,layer=window_context(tmp_path);window.select_frame(3);window.particle_properties.motion_keyframe_property.setCurrentIndex(window.particle_properties.motion_keyframe_property.findData("radius_start"));window.particle_properties.motion_radius_start.setValue(42);APP.processEvents();before=window.application_undo_stack.count();window.particle_properties.add_motion_keyframe.click();APP.processEvents()
    assert layer.particle_settings.motion.value("radius_start",3)==42 and window.application_undo_stack.count()==before+1
    window.application_undo_stack.undo();assert "radius_start" not in layer.particle_settings.motion.tracks
    window.dirty=False;window.close()
