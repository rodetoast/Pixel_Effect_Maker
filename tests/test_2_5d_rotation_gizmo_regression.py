import os
import time
from copy import deepcopy

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QPoint,QPointF,QSettings,QThreadPool,Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_layer_transform_3d_render_service import projected_quad
from app.services.particle_render_service import PARTICLE_RENDER_STATS
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])
AXES=("rotate_x","rotate_y","rotate_z")


def context(tmp_path,name="rotation"):
    settings=QSettings(str(tmp_path/f"{name}.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en")
    window=MainWindow(ShortcutSettingsService(settings));pixels=np.zeros((12,12,4),dtype=np.uint8);pixels[2:10,3:9]=[240,90,30,220]
    asset=SourceAsset("spark",pixels,pivot_x=6,pivot_y=6);composition=ResourceComposition("Rotation",12,12,12,3,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,2,pivot_x=6,pivot_y=6))
    window.project.source_assets.append(asset);window.project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    window.canvas.resize(760,700);window.show();APP.processEvents()
    return window,layer


def close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.transform_inspector_timer.stop()
    window._pending_resource_transforms.clear();window.dirty=False;window._non_undo_dirty=False;window.close();QThreadPool.globalInstance().waitForDone(2500);APP.processEvents()


def wait_proxy(window,active=None,timeout=2500):
    elapsed=0
    while elapsed<timeout:
        APP.processEvents();state=window.canvas.interactive_transform_proxy
        if state is not None and (active is None or state.active is active):return state
        QTest.qWait(10);elapsed+=10
    return window.canvas.interactive_transform_proxy


def select_mode(window,mode):
    panel=window.particle_properties.transform_panel;panel.set_advanced_expanded(True);APP.processEvents();QTest.mouseClick(panel.gizmo_buttons[mode],Qt.MouseButton.LeftButton);APP.processEvents()
    assert window.canvas.resource_transform_mode==mode and panel.gizmo_buttons[mode].isChecked()


def target_for(window,angle=135):
    center=window.canvas.resource_transform_handle_positions()["center"]
    radians=np.radians(angle);return QPoint(round(center.x()+42*np.cos(radians)),round(center.y()+42*np.sin(radians)))


def test_rotation_gizmo_crosses_360_without_wrapping_to_zero(tmp_path):
    window,layer=context(tmp_path,"multi-turn");layer.layer_transform.rotation_z=350;window.select_resource_layer(layer.id);select_mode(window,"rotate_z")
    handle=window.canvas.resource_transform_handle_positions()["rotate_z"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(window.canvas,target_for(window,10));APP.processEvents()
    assert window.canvas.resource_transform.rotation_z==pytest.approx(370,abs=3)
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=target_for(window,10));close(window)


def test_gizmo_remains_visible_while_delayed_exact_worker_installs(tmp_path,monkeypatch):
    window,layer=context(tmp_path,"delayed-overlay");select_mode(window,"rotate_y")
    import app.services.interactive_gizmo_service as service
    original=service.render_effect_resource_layer_current_base_frame
    monkeypatch.setattr(service,"render_effect_resource_layer_current_base_frame",lambda *args,**kwargs:(time.sleep(.15),original(*args,**kwargs))[1])
    handle=window.canvas.resource_transform_handle_positions()["rotate_y"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    installed_before=window.interactive_gizmo_renderer.collector.installed
    for index in range(100):
        QTest.mouseMove(window.canvas,target_for(window,45+index));QTest.qWait(10);APP.processEvents()
        positions=window.canvas.resource_transform_handle_positions()
        assert window.canvas._resource_transform_drag=="rotate_y" and window.canvas.resource_transform is not None
        assert {"center","rotate_y","x","y","z"}<=set(positions)
    elapsed=0
    while window.interactive_gizmo_renderer.collector.installed<=installed_before and elapsed<1000:
        QTest.qWait(10);APP.processEvents();elapsed+=10
        assert window.canvas._resource_transform_drag=="rotate_y"
        assert {"center","rotate_y","x","y","z"}<=set(window.canvas.resource_transform_handle_positions())
    assert window.interactive_gizmo_renderer.collector.installed>installed_before
    assert window.canvas._resource_transform_drag=="rotate_y" and window.canvas.effect_guide_settings is not None
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=target_for(window,145));close(window)


def test_proxy_paint_order_keeps_guide_and_gizmo_as_final_overlay(tmp_path,monkeypatch):
    window,layer=context(tmp_path,"paint-order");select_mode(window,"rotate_x");window.canvas.set_effect_guide(layer.id,"particle",layer.particle_settings);window.canvas.set_effect_guides_visible(True)
    handle=window.canvas.resource_transform_handle_positions()["rotate_x"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(window.canvas,target_for(window));
    state=wait_proxy(window,active=True);assert state is not None
    order=[]
    monkeypatch.setattr(window.canvas,"_paint_interactive_transform_proxy",lambda painter,state:order.append("proxy"))
    monkeypatch.setattr(window.canvas,"_paint_resource_transform_gizmo",lambda painter:order.append("gizmo"))
    monkeypatch.setattr(window.canvas,"_paint_effect_guide",lambda painter:order.append("guide"))
    image=QImage(window.canvas.size(),QImage.Format.Format_ARGB32);painter=QPainter(image);window.canvas.render(painter,QPoint());painter.end()
    assert "proxy" in order and order[-2:]==["guide","gizmo"]
    assert window.canvas._resource_transform_drag=="rotate_x"
    QTest.keyClick(window.canvas,Qt.Key.Key_Escape);close(window)


@pytest.mark.parametrize("mode",AXES)
def test_rotation_button_selects_canonical_tool(mode,tmp_path):
    window,_=context(tmp_path,f"button-{mode}");select_mode(window,mode);close(window)


@pytest.mark.parametrize("mode",AXES)
def test_rotation_qtest_drag_updates_transient_inspector_proxy_and_release(mode,tmp_path,monkeypatch):
    window,layer=context(tmp_path,f"drag-{mode}");select_mode(window,mode);property_name=mode.replace("rotate_","rotation_")
    before=deepcopy(layer.layer_transform);before_undo=window.application_undo_stack.count()
    full=[];current=[];module=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer","apply_effect_resource_layer_current_frame"])
    original_full=module.apply_effect_resource_layer;original_current=module.apply_effect_resource_layer_current_frame
    monkeypatch.setattr(module,"apply_effect_resource_layer",lambda *a,**k:full.append(1) or original_full(*a,**k))
    monkeypatch.setattr(module,"apply_effect_resource_layer_current_frame",lambda *a,**k:current.append(1) or original_current(*a,**k))
    handle=window.canvas.resource_transform_handle_positions()[mode].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    assert window.canvas._resource_transform_drag==mode
    QTest.mouseMove(window.canvas,target_for(window));APP.processEvents()
    transient=deepcopy(window.canvas.resource_transform);value=getattr(transient,property_name)
    assert value==pytest.approx(135,abs=2) and not hasattr(transient,mode)
    assert layer.layer_transform.to_dict()==before.to_dict()
    panel=window.particle_properties.transform_panel;elapsed=0
    while panel.fields[property_name].value()!=pytest.approx(value,abs=.01) and elapsed<500:
        QTest.qWait(10);APP.processEvents();elapsed+=10
    assert panel.fields[property_name].value()==pytest.approx(value,abs=.01)
    state=wait_proxy(window,active=True);assert state is not None
    assert state.last_applied_revision>=transient.revision and state.applied_transform.is_identity()
    assert full==[] and current==[]
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=target_for(window));APP.processEvents()
    assert getattr(layer.layer_transform,property_name)==pytest.approx(value)
    elapsed=0
    while elapsed<2500 and window.canvas.interactive_transform_proxy is not None:QTest.qWait(10);APP.processEvents();elapsed+=10
    assert window.application_undo_stack.count()==before_undo+1 and full==[] and current==[]
    window.application_undo_stack.undo();assert getattr(layer.layer_transform,property_name)==getattr(before,property_name)
    window.application_undo_stack.redo();assert getattr(layer.layer_transform,property_name)==pytest.approx(value)
    close(window)


@pytest.mark.parametrize("mode",AXES)
def test_rotation_escape_restores_without_model_mutation_undo_or_exact(mode,tmp_path,monkeypatch):
    window,layer=context(tmp_path,f"escape-{mode}");select_mode(window,mode);before=deepcopy(layer.layer_transform);undo=window.application_undo_stack.count();calls=[]
    module=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer_current_frame"]);original=module.apply_effect_resource_layer_current_frame
    monkeypatch.setattr(module,"apply_effect_resource_layer_current_frame",lambda *a,**k:calls.append(1) or original(*a,**k))
    handle=window.canvas.resource_transform_handle_positions()[mode].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(window.canvas,target_for(window));APP.processEvents()
    QTest.keyClick(window.canvas,Qt.Key.Key_Escape);APP.processEvents()
    assert layer.layer_transform.to_dict()==before.to_dict() and window.canvas.resource_transform.to_dict()==before.to_dict()
    assert window.application_undo_stack.count()==undo and calls==[] and window.canvas.interactive_transform_proxy is None
    close(window)


@pytest.mark.parametrize("mode",AXES)
def test_one_hundred_rotation_moves_use_proxy_only(mode,tmp_path,monkeypatch):
    window,layer=context(tmp_path,f"perf-{mode}");select_mode(window,mode)
    window._schedule_resource_transform_prewarm();revision=window.interactive_proxy_prewarm.request_revision;state=None;elapsed=0
    while elapsed<2500:
        APP.processEvents();state=window.canvas.interactive_transform_proxy;token=None if state is None else state.prewarm_token
        if state is not None and not state.active and token is not None and token.request_revision==revision:break
        QTest.qWait(10);elapsed+=10
    assert state is not None and state.prewarm_token.request_revision==revision
    # Isolate the drag measurement from any lower-priority current-frame job
    # already queued while the window/selection was being initialized.
    assert QThreadPool.globalInstance().waitForDone(2500);APP.processEvents()
    panel=window.particle_properties.transform_panel;set_layers=[];timeline=[]
    monkeypatch.setattr(panel,"set_layer",lambda *a,**k:set_layers.append(1))
    monkeypatch.setattr(window.timeline,"refresh",lambda *a,**k:timeline.append(1))
    before_stats=dict(PARTICLE_RENDER_STATS);qimages=window.canvas.proxy_base_image_cache.qimage_creations;qpixmaps=window.canvas.proxy_base_image_cache.qpixmap_creations
    handle=window.canvas.resource_transform_handle_positions()[mode].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    center=window.canvas.resource_transform_handle_positions()["center"]
    for index in range(100):
        angle=(index+1)*2.7;radians=np.radians(angle);point=QPoint(round(center.x()+42*np.cos(radians)),round(center.y()+42*np.sin(radians)));QTest.mouseMove(window.canvas,point)
    APP.processEvents();property_name=mode.replace("rotate_","rotation_")
    assert window.canvas.interaction_stats["calls"].get(f"{property_name}_updates")==100
    assert PARTICLE_RENDER_STATS["full_sequence_renders"]==before_stats["full_sequence_renders"]
    assert PARTICLE_RENDER_STATS["current_frame_renders"]==before_stats["current_frame_renders"]
    assert window.canvas.proxy_base_image_cache.qimage_creations==qimages and window.canvas.proxy_base_image_cache.qpixmap_creations==qpixmaps
    assert set_layers==[] and timeline==[]
    QTest.keyClick(window.canvas,Qt.Key.Key_Escape);close(window)


@pytest.mark.parametrize("mode,zoom",[(axis,zoom) for axis in AXES for zoom in (.25,1.0,4.0)])
def test_rotation_hit_and_drag_work_with_zoom_and_pan(mode,zoom,tmp_path):
    window,layer=context(tmp_path,f"zoom-{mode}-{zoom}");select_mode(window,mode);window.canvas.zoom=zoom;window.canvas.pan_offset=QPointF(31,-19);APP.processEvents()
    handle=window.canvas.resource_transform_handle_positions()[mode].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);assert window.canvas._resource_transform_drag==mode
    QTest.mouseMove(window.canvas,target_for(window,120));property_name=mode.replace("rotate_","rotation_")
    assert getattr(window.canvas.resource_transform,property_name)==pytest.approx(120,abs=3) and getattr(layer.layer_transform,property_name)==0
    QTest.keyClick(window.canvas,Qt.Key.Key_Escape);close(window)


def test_rotation_existing_current_keyframe_is_edited_transiently_and_committed(tmp_path):
    window,layer=context(tmp_path,"keyframe");property_name="rotation_z";layer.layer_transform.set_keyframe(property_name,0,20);window.select_resource_layer(layer.id);select_mode(window,"rotate_z")
    handle=window.canvas.resource_transform_handle_positions()["rotate_z"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(window.canvas,target_for(window,120));APP.processEvents()
    # Existing inspector policy edits a current-frame key when one exists.
    track=window.canvas.resource_transform.tracks[property_name];key=next(item for item in track.keyframes if item.frame==0)
    assert key.value==pytest.approx(120,abs=3)
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=target_for(window,120));APP.processEvents()
    assert layer.layer_transform.value(property_name,0)==pytest.approx(120,abs=3);close(window)
