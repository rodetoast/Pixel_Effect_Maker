import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from copy import deepcopy
import numpy as np
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QImage, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.layer_space_transform_service import projected_layer_quad
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_base_frame,render_effect_resource_layer_local_current_frame
from app.services import effect_resource_layer_render_service as render_service
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from tests.gizmo_sync_support import GizmoSyncObservation


APP=QApplication.instance() or QApplication([])


def context(tmp_path,name="proxy",particle=False):
    settings=QSettings(str(tmp_path/f"{name}.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en")
    window=MainWindow(ShortcutSettingsService(settings));pixels=np.zeros((12,12,4),dtype=np.uint8);pixels[2:10,3:9]=[240,90,30,173]
    asset=SourceAsset("spark",pixels,pivot_x=6,pivot_y=6);composition=ResourceComposition("Proxy Resource",12,12,12,3,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,2,pivot_x=6,pivot_y=6));window.project.source_assets.append(asset);window.project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE) if particle else window.create_resource_layer_from_resource(composition.id)
    window.canvas.resize(760,700);window.show();APP.processEvents()
    return window,layer,composition


def close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window._pending_resource_transforms.clear();window.canvas.clear_interactive_transform_proxy(update=False)
    window.dirty=False;window._non_undo_dirty=False;window.close()


def wait_for_active_proxy(window,timeout=2000):
    elapsed=0
    while elapsed<timeout:
        APP.processEvents();state=window.canvas.interactive_transform_proxy
        if state is not None and state.active:return state
        QTest.qWait(10);elapsed+=10
    return window.canvas.interactive_transform_proxy


def test_gizmo_drag_uses_proxy_and_release_runs_exact_once(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path);generated=next(item for item in window.project.layers if item.id==layer.generated_layer_id);before_pixels=window.project.frames[0].layer_pixels[generated.id].copy()
    exact=[];original=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer_current_frame"]).apply_effect_resource_layer_current_frame
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame",lambda *args,**kwargs:exact.append(args[1].layer_transform.revision) or original(*args,**kwargs))
    simulation=[];exact_numpy=[];original_simulation=render_service.render_particle_frames;original_transform=render_service.transform_rgba_frame
    monkeypatch.setattr(render_service,"render_particle_frames",lambda *args,**kwargs:simulation.append(1) or original_simulation(*args,**kwargs))
    monkeypatch.setattr(render_service,"transform_rgba_frame",lambda *args,**kwargs:exact_numpy.append(1) or original_transform(*args,**kwargs))
    before_undo=window.application_undo_stack.count();handle=window.canvas.resource_transform_handle_positions()["z"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    model_before=deepcopy(layer.layer_transform)
    for value in range(100):QTest.mouseMove(window.canvas,handle+QPoint(value+1,(value%7)-3))
    window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    state=wait_for_active_proxy(window)
    assert exact==[] and exact_numpy==[] and simulation==[] and state is not None and state.last_applied_revision>layer.layer_transform.revision
    assert layer.layer_transform.to_dict()==model_before.to_dict()
    assert np.array_equal(window.project.frames[0].layer_pixels[generated.id],before_pixels)
    assert window.canvas.proxy_base_image_cache.qimage_creations==1 and window.canvas.proxy_base_image_cache.qpixmap_creations==1
    assert window.canvas.proxy_stats["apply_calls"]<100 and window.canvas.proxy_stats["paint_calls"]<100
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(100,0));APP.processEvents()
    assert len(exact)==1 and len(exact_numpy)==1 and simulation==[] and window.canvas.interactive_transform_proxy is None and window.application_undo_stack.count()==before_undo+1
    close(window)


def test_gizmo_escape_restores_exact_once_without_undo(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"escape");before=deepcopy(layer.layer_transform);before_undo=window.application_undo_stack.count();calls=[]
    original=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer_current_frame"]).apply_effect_resource_layer_current_frame
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame",lambda *args,**kwargs:calls.append(1) or original(*args,**kwargs))
    handle=window.canvas.resource_transform_handle_positions()["z"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(window.canvas,handle+QPoint(30,-20));window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    QTest.keyClick(window.canvas,Qt.Key.Key_Escape);APP.processEvents()
    assert layer.layer_transform.to_dict()==before.to_dict() and calls==[] and window.application_undo_stack.count()==before_undo and window.canvas.interactive_transform_proxy is None
    close(window)


def test_spinbox_burst_uses_proxy_and_idle_or_editing_finished_finalizes_once(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"spin");calls=[];original=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer_current_frame"]).apply_effect_resource_layer_current_frame
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame",lambda *args,**kwargs:calls.append(args[1].layer_transform.position_x) or original(*args,**kwargs))
    retranslations=[];monkeypatch.setattr(window,"retranslate_ui",lambda *args:retranslations.append(1))
    spin=window.composition_layer_properties.transform_panel.fields["position_x"]
    for value in range(1,21):spin.setValue(value)
    assert calls==[] and retranslations==[];window.resource_transform_render_timer.stop();window._flush_resource_transform_current();assert wait_for_active_proxy(window) is not None
    spin.editingFinished.emit();APP.processEvents()
    assert calls==[20.0] and (window.canvas.interactive_transform_proxy is None or not window.canvas.interactive_transform_proxy.active)
    for value in range(21,26):spin.setValue(value)
    QTest.qWait(180)
    assert calls==[20.0,25.0]
    close(window)


def test_ctrl_wheel_burst_runs_one_idle_exact_render(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"wheel");calls=[];original=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer_current_frame"]).apply_effect_resource_layer_current_frame
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame",lambda *args,**kwargs:calls.append(1) or original(*args,**kwargs))
    window.composition_layer_properties.transform_panel.set_advanced_expanded(True);APP.processEvents()
    spin=window.composition_layer_properties.transform_panel.fields["position_x"];spin.setFocus();local=QPointF(spin.rect().center())
    for _ in range(20):
        event=QWheelEvent(local,QPointF(spin.mapToGlobal(local.toPoint())),QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.ControlModifier,Qt.ScrollPhase.ScrollUpdate,False);APP.notify(spin,event)
    assert calls==[] and spin.value()==20
    QTest.qWait(180);assert calls==[1] and window.canvas.interactive_transform_proxy is None
    close(window)


def test_proxy_reuses_cropped_base_image_and_shared_projected_quad(tmp_path):
    window,layer,_=context(tmp_path,"geometry");layer.layer_transform.rotation_x=28;layer.layer_transform.rotation_y=17;layer.layer_transform.perspective_strength=.6;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    state=wait_for_active_proxy(window);assert state and state.base.alpha_bounds is not None
    assert state.base.rgba.shape[0]<window.project.height and state.base.rgba.shape[1]<window.project.width
    base=render_effect_resource_layer_local_current_frame(window.project,layer,0);left,top,right,bottom=state.base.alpha_bounds
    assert np.array_equal(state.base.rgba,base[top:bottom+1,left:right+1])
    expected,valid=projected_layer_quad((left,top,right+1,bottom+1),layer.layer_transform.evaluated(0),window.project.width,window.project.height);assert valid.all()
    actual=np.array([[window.canvas.widget_to_canvas(point).x(),window.canvas.widget_to_canvas(point).y()] for point in state.projected_quad])
    assert np.allclose(actual,expected) and window.canvas.proxy_base_image_cache.qimage_creations==1
    for value in range(10):layer.layer_transform.rotation_y+=1;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    assert window.canvas.proxy_base_image_cache.qimage_creations==1 and window.canvas.proxy_base_image_cache.qpixmap_creations==1
    close(window)


def test_proxy_paint_avoids_project_compose_and_disables_smoothing(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"paint");layer.layer_transform.rotation_z=23;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();assert wait_for_active_proxy(window) is not None
    monkeypatch.setattr(window.project,"compose_frame",lambda *args:(_ for _ in ()).throw(AssertionError("exact compose used")))
    target=QImage(window.canvas.size(),QImage.Format.Format_ARGB32);window.canvas.render(target)
    assert window.canvas.proxy_stats["paint_calls"]>=1
    close(window)


def test_proxy_coalesces_latest_rejects_stale_and_never_overlaps(tmp_path):
    window,layer,_=context(tmp_path,"latest")
    for value in range(50):layer.layer_transform.rotation_y=value;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer)
    window.resource_transform_render_timer.stop();window._flush_resource_transform_current();state=wait_for_active_proxy(window)
    assert state.last_applied_revision==layer.layer_transform.revision and window.canvas.proxy_stats["apply_calls"]==1
    layer.layer_transform.revision+=1;assert not window.canvas.apply_interactive_transform_proxy(layer)
    layer.layer_transform.rotation_y+=1;window._queue_resource_transform_render(layer);state.render_in_progress=True;assert not window.canvas.apply_interactive_transform_proxy(layer);state.render_in_progress=False
    assert window.canvas.proxy_stats["overlap_rejections"]==1
    close(window)


def test_identical_projected_quad_skips_repaint_without_rounding_model(tmp_path):
    window,layer,_=context(tmp_path,"quantized");layer.layer_transform.position_x=6.125;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();assert wait_for_active_proxy(window) is not None;skips=window.canvas.proxy_stats["paint_skips"]
    exact_value=layer.layer_transform.position_x;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    assert window.canvas.proxy_stats["paint_skips"]==skips+1 and layer.layer_transform.position_x==exact_value
    close(window)


def test_small_proxy_uses_old_and_new_partial_dirty_bounds(tmp_path):
    window,layer,_=context(tmp_path,"dirty");layer.layer_transform.position_x=8;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();state=wait_for_active_proxy(window)
    dirty=window.canvas.last_proxy_dirty_rect
    assert dirty.contains(state.previous_projected_bounds) and dirty.contains(state.current_projected_bounds)
    assert dirty.width()<window.canvas.width() and dirty.height()<window.canvas.height() and window.canvas.proxy_stats["partial_updates"]==1
    close(window)


def test_depth_buffers_and_other_layers_stay_fixed_until_order_crossing(tmp_path):
    window,layer,composition=context(tmp_path,"depth");other=window.create_resource_layer_from_resource(composition.id);window.select_resource_layer(layer.id)
    layer.layer_transform.position_z=-2;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();state=wait_for_active_proxy(window);rebuilds=window.canvas.proxy_stats["depth_rebuilds"];underlay=state.underlay_pixmap.cacheKey();overlay=state.overlay_pixmap.cacheKey()
    for value in (-3,-4,-5):layer.layer_transform.position_z=value;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    assert window.canvas.proxy_stats["depth_rebuilds"]==rebuilds and state.underlay_pixmap.cacheKey()==underlay and state.overlay_pixmap.cacheKey()==overlay
    layer.layer_transform.position_z=2;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current()
    assert window.canvas.proxy_stats["depth_rebuilds"]==rebuilds+1
    close(window)


def test_proxy_keeps_gui_guides_visible_and_is_not_serialized(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"guides");layer.layer_transform.position_x=4;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();assert wait_for_active_proxy(window) is not None;calls=[]
    original=window.canvas._paint_effect_guide;monkeypatch.setattr(window.canvas,"_paint_effect_guide",lambda painter:calls.append(1) or original(painter))
    target=QImage(window.canvas.size(),QImage.Format.Format_ARGB32);window.canvas.render(target);assert calls and "interactive_transform_proxy" not in window.project.to_dict()
    window._flush_resource_transform_final();window.canvas.render(target);assert calls
    close(window)


class LayoutCounter(QObject):
    def __init__(self):super().__init__();self.count=0
    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.LayoutRequest:self.count+=1
        return False


def test_gizmo_updates_only_changed_inspector_field_without_layout(tmp_path,monkeypatch,record_property):
    window,layer,_=context(tmp_path,"inspector");panel=window.composition_layer_properties.transform_panel;window._set_resource_transform_gizmo(layer.id,"rotate_y")
    probe=GizmoSyncObservation(window,layer,panel,monkeypatch);records=probe.records
    counter=LayoutCounter();panel.installEventFilter(counter);APP.processEvents();counter.count=0
    handle=window.canvas.resource_transform_handle_positions()["rotate_y"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    try:
        for value in range(20):QTest.mouseMove(window.canvas,handle+QPoint(value+1,value%5))
        assert probe.wait(1000),probe.snapshot()
        # Keep the changed-field and bounded geometry contracts; do not accept
        # an unrelated refresh just because an arbitrary sleep has elapsed.
        assert records and all(names==("rotation_y",) for names in records) and counter.count<=3
        assert probe.values_match and probe.transient_changed and not probe.snapshot()["document_changed"]
    finally:
        record_property("gizmo_sync",{**probe.snapshot(),"layout_requests":counter.count})
        probe.disconnect()
        QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(20,0));close(window)


def test_playback_prepares_exact_cache_without_materializing_sequence_and_clears_proxy(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"playback");layer.layer_transform.rotation_x=18;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();assert wait_for_active_proxy(window) is not None
    calls=[];original=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer"]).apply_effect_resource_layer
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer",lambda *args,**kwargs:calls.append(1) or original(*args,**kwargs))
    applies=window.canvas.proxy_stats["apply_calls"];window.set_playing(True);window.set_playing(False)
    assert calls==[] and window.canvas.interactive_transform_proxy is None and window.canvas.proxy_stats["apply_calls"]==applies
    assert "interactive_transform_proxy" not in window.project.to_dict()
    close(window)


def test_bake_finalizes_proxy_then_uses_exact_sequence(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"bake",particle=True);layer.layer_transform.rotation_y=14;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();current=[];sequence=[]
    module=__import__("app.ui.main_window",fromlist=["apply_effect_resource_layer_current_frame","apply_effect_resource_layer"]);original_current=module.apply_effect_resource_layer_current_frame;original_sequence=module.apply_effect_resource_layer
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame",lambda *args,**kwargs:current.append(1) or original_current(*args,**kwargs));monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer",lambda *args,**kwargs:sequence.append(1) or original_sequence(*args,**kwargs))
    assert window.bake_particle_emitter(layer.id,deepcopy(layer.particle_settings))
    assert current==[] and sequence==[1] and window.canvas.interactive_transform_proxy is None
    close(window)


def test_particle_preview_uses_exact_transform_and_clears_proxy(tmp_path,monkeypatch):
    window,layer,_=context(tmp_path,"preview",particle=True);base,_=render_effect_resource_layer_base_frame(window.project,layer,0);layer.layer_transform.rotation_x=19;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer);window.resource_transform_render_timer.stop();window._flush_resource_transform_current();calls=[]
    from app.services import effect_layer_transform_3d_render_service as exact_service
    original=exact_service.transform_rgba_frame;monkeypatch.setattr(exact_service,"transform_rgba_frame",lambda *args,**kwargs:calls.append(1) or original(*args,**kwargs))
    window._particle_preview_ready(layer.id,1,[base.copy(),base.copy()])
    assert calls==[] and window.canvas.preview_frames is not None and window.canvas.interactive_transform_proxy is None
    close(window)
