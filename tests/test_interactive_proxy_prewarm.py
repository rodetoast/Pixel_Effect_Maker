import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from copy import deepcopy
import numpy as np
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_resource_layer_render_service import effect_resource_layer_base_frame_key
from app.services.settings_service import ShortcutSettingsService
from app.ui.interactive_proxy_prewarm import (
    InteractiveCompositeCache, alpha_composite_layers, prefix_suffix_composite,
)
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def context(tmp_path,name="prewarm",layers=1):
    settings=QSettings(str(tmp_path/f"{name}.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en")
    window=MainWindow(ShortcutSettingsService(settings));pixels=np.zeros((12,12,4),dtype=np.uint8);pixels[2:10,3:9]=[240,90,30,173]
    asset=SourceAsset("spark",pixels,pivot_x=6,pivot_y=6);composition=ResourceComposition("Proxy Resource",12,12,12,3,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,2,pivot_x=6,pivot_y=6));window.project.source_assets.append(asset);window.project.resource_compositions.append(composition)
    values=[window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE) for _ in range(layers)]
    window.select_resource_layer(values[0].id);window.canvas.resize(760,700);window.show();APP.processEvents()
    return window,values,composition


def finish(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.interactive_proxy_prewarm.cancel();window.interactive_proxy_prewarm._poll.stop()
    window._pending_resource_transforms.clear();window.canvas.clear_interactive_transform_proxy(update=False);window.dirty=False;window._non_undo_dirty=False;window.close()


def wait_for_prewarm(window,timeout=800):
    elapsed=0
    while elapsed<timeout:
        APP.processEvents();state=window.canvas.interactive_transform_proxy
        if state is not None and not state.active:return state
        QTest.qWait(20);elapsed+=20
    return window.canvas.interactive_transform_proxy


def test_layer_selection_schedules_idle_prewarm(tmp_path):
    window,layers,_=context(tmp_path);window.select_resource_layer(layers[0].id)
    assert window.interactive_proxy_prewarm._timer.isActive();finish(window)


def test_frame_change_schedules_only_latest_prewarm(tmp_path):
    window,_,_=context(tmp_path,"frames")
    for frame in range(20):window.select_frame(frame%3)
    assert window.interactive_proxy_prewarm._pending.effect_frame==1
    assert window.interactive_proxy_prewarm.request_revision>=20;finish(window)


def test_scrubbing_does_not_prewarm_intermediate_frames(tmp_path):
    window,_,_=context(tmp_path,"scrub");window._resource_timeline_scrub_started()
    for frame in range(3):window.select_frame(frame)
    assert window.interactive_proxy_prewarm._pending is None
    window._resource_timeline_scrub_finished();assert window.interactive_proxy_prewarm._pending.effect_frame==2;finish(window)


def test_playback_does_not_run_interactive_prewarm(tmp_path):
    window,_,_=context(tmp_path,"play");window.set_playing(True)
    assert window.interactive_proxy_prewarm._pending is None and not window.interactive_proxy_prewarm._timer.isActive()
    window.set_playing(False);assert window.interactive_proxy_prewarm._timer.isActive();finish(window)


def test_prewarm_builds_base_crop_qimage_pixmap_and_composites_once(tmp_path):
    window,_,_=context(tmp_path,"build",3);state=wait_for_prewarm(window)
    assert state is not None and not state.active
    assert window.canvas.proxy_base_image_cache.alpha_bounds_scans==1
    assert window.canvas.proxy_base_image_cache.qimage_creations==1 and window.canvas.proxy_base_image_cache.qpixmap_creations==1
    rebuilds=window.canvas.proxy_stats["depth_rebuilds"];images=window.canvas.proxy_base_image_cache.qimage_creations
    window._schedule_resource_transform_prewarm();assert wait_for_prewarm(window) is not None
    assert window.canvas.proxy_base_image_cache.qimage_creations==images and window.canvas.proxy_stats["depth_rebuilds"]==rebuilds
    finish(window)


def test_first_gizmo_press_uses_prewarmed_state(tmp_path,monkeypatch):
    window,layers,_=context(tmp_path,"press",3);assert wait_for_prewarm(window) is not None
    monkeypatch.setattr("app.ui.main_window.render_effect_resource_layer_base_frame",lambda *args:(_ for _ in ()).throw(AssertionError("base rebuilt")))
    monkeypatch.setattr(window.canvas,"_proxy_layers_pixmap",lambda *args:(_ for _ in ()).throw(AssertionError("layers recomposited")))
    handle=window.canvas.resource_transform_handle_positions()["z"].toPoint();QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    assert window.canvas.interactive_transform_proxy.active
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=handle);finish(window)


def test_partial_prewarm_reuses_available_items(tmp_path):
    window,layers,_=context(tmp_path,"partial");assert wait_for_prewarm(window) is not None
    key=effect_resource_layer_base_frame_key(window.project,layers[0],window.frame_index);base=window.canvas.proxy_base_image_cache.peek(key)
    window.canvas.interactive_transform_proxy=None;window.canvas.proxy_composite_cache.clear()
    window._schedule_resource_transform_prewarm();assert wait_for_prewarm(window) is not None
    assert window.canvas.proxy_base_image_cache.peek(key) is base;finish(window)


def test_stale_prewarm_result_is_rejected(tmp_path):
    window,_,_=context(tmp_path,"stale");window.interactive_proxy_prewarm.delay_ms=1;window._schedule_resource_transform_prewarm();QTest.qWait(2);window.select_frame(2)
    state=wait_for_prewarm(window)
    assert state is not None and state.frame==2;finish(window)


def test_newer_prewarm_request_cancels_older_request(tmp_path):
    window,_,_=context(tmp_path,"newer");first=window.interactive_proxy_prewarm.request_revision;window.select_frame(1);window.select_frame(2)
    assert window.interactive_proxy_prewarm.request_revision>=first+2 and window.interactive_proxy_prewarm._pending.effect_frame==2;finish(window)


def test_prewarm_never_blocks_active_interaction(tmp_path):
    window,_,_=context(tmp_path,"priority");window.canvas._resource_transform_drag="z";window._schedule_resource_transform_prewarm()
    assert window.interactive_proxy_prewarm._pending is None;window.canvas._resource_transform_drag=None;finish(window)


def test_transform_change_preserves_underlay_overlay_cache(tmp_path):
    window,layers,_=context(tmp_path,"transform",3);layer=layers[0];key=effect_resource_layer_base_frame_key(window.project,layer,0)
    before=window.canvas.proxy_prewarm_token(layer,key).composite_key;layer.layer_transform.position_x+=4;layer.layer_transform.revision+=1
    after=window.canvas.proxy_prewarm_token(layer,key).composite_key
    assert before==after;finish(window)


def test_other_layer_change_invalidates_relevant_composite_cache(tmp_path):
    window,layers,_=context(tmp_path,"other",3);layer=layers[0];key=effect_resource_layer_base_frame_key(window.project,layer,0);before=window.canvas.proxy_prewarm_token(layer,key).composite_key
    other=next(item for item in window.project.layers if item.id==layers[1].generated_layer_id);window.project.frames[0].layer_pixels[other.id]=window.project.frames[0].layer_pixels[other.id].copy()
    assert window.canvas.proxy_prewarm_token(layer,key).composite_key!=before;finish(window)


def test_visibility_change_invalidates_depth_signature(tmp_path):
    window,layers,_=context(tmp_path,"visible",3);layer=layers[0];key=effect_resource_layer_base_frame_key(window.project,layer,0);before=window.canvas.proxy_prewarm_token(layer,key)
    other=next(item for item in window.project.layers if item.id==layers[1].generated_layer_id);other.visible=False
    after=window.canvas.proxy_prewarm_token(layer,key);assert before.visibility_signature!=after.visibility_signature and before.depth_signature!=after.depth_signature;finish(window)


def test_z_order_signature_cache_reuse(tmp_path):
    window,layers,_=context(tmp_path,"depth",3);layer=layers[0];key=effect_resource_layer_base_frame_key(window.project,layer,0);base=window.canvas.proxy_prewarm_token(layer,key).composite_key
    layer.layer_transform.position_z-=1;layer.layer_transform.revision+=1;assert window.canvas.proxy_prewarm_token(layer,key).composite_key==base
    layer.layer_transform.position_z=10;layer.layer_transform.revision+=1;assert window.canvas.proxy_prewarm_token(layer,key).composite_key!=base;finish(window)


def test_prefix_suffix_composite_matches_direct_composite():
    a=np.zeros((3,3,4),dtype=np.uint8);b=a.copy();c=a.copy();a[:]=[255,0,0,100];b[:]=[0,255,0,120];c[:]=[0,0,255,140]
    prefix,suffix=prefix_suffix_composite((3,3),((a,1.0),(b,.5)),((c,.8),))
    assert np.array_equal(prefix,alpha_composite_layers((3,3),((a,1.0),(b,.5))))
    assert np.array_equal(suffix,alpha_composite_layers((3,3),((c,.8),)))


def test_equal_z_timeline_order_is_preserved(tmp_path):
    window,layers,_=context(tmp_path,"equal",3);layer=layers[1];signature,before,after=window.canvas._proxy_depth_signature(layer,layer.layer_transform)
    ordered=[item.id for item in before]+[layer.generated_layer_id]+[item.id for item in after]
    expected=[item.id for item in window.project.layers if item.visible]
    assert ordered==expected and signature==(tuple(item.id for item in before),tuple(item.id for item in after));finish(window)


def test_composite_cache_lru_respects_memory_limit():
    cache=InteractiveCompositeCache(maximum_bytes=800);pixmap=QPixmap(10,10)
    cache.put((1,),pixmap,pixmap,400);cache.put((2,),pixmap,pixmap,400);assert cache.get((1,)) is not None
    cache.put((3,),pixmap,pixmap,400)
    assert len(cache)==2 and cache.current_bytes<=800 and cache.get((2,)) is None and cache.evictions==1


def test_prewarm_completion_does_not_repaint_canvas(tmp_path,monkeypatch):
    window,_,_=context(tmp_path,"paint");calls=[];monkeypatch.setattr(window.canvas,"update",lambda *args:calls.append(args))
    window._schedule_resource_transform_prewarm();assert wait_for_prewarm(window) is not None
    assert calls==[];finish(window)


def test_undo_redo_schedules_only_final_state_prewarm(tmp_path):
    window,layers,_=context(tmp_path,"undo");layer=layers[0];after=deepcopy(layer.layer_transform);after.position_x=5;window.update_resource_layer_transform(layer.id,after)
    window.application_undo_stack.undo();window.application_undo_stack.redo()
    assert window.interactive_proxy_prewarm._pending.transform_revision==layer.layer_transform.revision;finish(window)


def test_layer_delete_clears_related_prewarm_state(tmp_path):
    window,_,_=context(tmp_path,"delete");assert wait_for_prewarm(window) is not None;window.delete_layer();APP.processEvents()
    assert window.canvas.interactive_transform_proxy is None;finish(window)


def test_project_open_clears_all_interactive_cache(tmp_path):
    window,_,_=context(tmp_path,"project");assert wait_for_prewarm(window) is not None
    window.canvas.set_project(Project.create_default());assert window.canvas.interactive_transform_proxy is None and len(window.canvas.proxy_composite_cache)==0;finish(window)
