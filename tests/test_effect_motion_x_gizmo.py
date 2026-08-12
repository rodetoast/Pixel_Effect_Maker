from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QPoint,QSettings,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleMotionSettings
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def context(tmp_path):
    settings=QSettings(str(tmp_path/"x-handle.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en")
    window=MainWindow(ShortcutSettingsService(settings));pixels=np.zeros((8,8,4),dtype=np.uint8);pixels[2:6,2:6]=[255,80,20,255]
    asset=SourceAsset("spark",pixels);composition=ResourceComposition("spark",8,8,12,4,True);composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,3,pivot_x=4,pivot_y=4))
    window.project.source_assets.append(asset);window.project.resource_compositions.append(composition);layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    layer.particle_settings.origin_x=window.project.width/2;layer.particle_settings.origin_y=window.project.height/2;layer.particle_settings.motion=ParticleMotionSettings(mode="orbit",radius_start=42,radius_end=60,start_angle_degrees=0);window.particle_preview_manager.revert(layer.as_particle_emitter())
    window.select_resource_layer(layer.id);window.canvas.resize(760,700);window.show();APP.processEvents();return window,layer


def finish(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.transform_inspector_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_effect_red_x_is_position_x_and_wins_over_overlapping_motion_handle(tmp_path):
    window,layer=context(tmp_path);canvas=window.canvas;handle=canvas.resource_transform_handle_positions()["x"].toPoint()
    assert canvas._hit_resource_transform(handle)=="x" and "layer space x" in canvas.resource_transform_tooltips["x"].lower()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle)
    assert canvas._resource_transform_drag=="x" and canvas._guide_handle is None
    QTest.keyClick(canvas,Qt.Key.Key_Escape);finish(window)


def test_effect_x_drag_updates_transform_guide_inspector_and_one_undo(tmp_path):
    window,layer=context(tmp_path);canvas=window.canvas;before_undo=window.application_undo_stack.count();handle=canvas.resource_transform_handle_positions()["x"].toPoint();guide_before=canvas._guide_points()["motion_center"]
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(canvas,handle+QPoint(36,0));APP.processEvents()
    transient=canvas.resource_transform.position_x;guide_after=canvas._guide_points()["motion_center"]
    assert transient>0 and guide_after.x()>guide_before.x()
    elapsed=0;field=window.particle_properties.transform_panel.fields["position_x"]
    while field.value()!=pytest.approx(transient,abs=.01) and elapsed<500:QTest.qWait(10);APP.processEvents();elapsed+=10
    assert field.value()==pytest.approx(transient,abs=.01)
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(36,0));APP.processEvents()
    assert layer.layer_transform.position_x==pytest.approx(transient) and window.application_undo_stack.count()==before_undo+1
    finish(window)


def test_effect_x_escape_restores_without_undo(tmp_path):
    window,layer=context(tmp_path);canvas=window.canvas;before=layer.layer_transform.position_x;undo=window.application_undo_stack.count();handle=canvas.resource_transform_handle_positions()["x"].toPoint()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(canvas,handle+QPoint(30,0));QTest.keyClick(canvas,Qt.Key.Key_Escape);APP.processEvents()
    assert layer.layer_transform.position_x==before and canvas.resource_transform.position_x==before and window.application_undo_stack.count()==undo
    finish(window)
