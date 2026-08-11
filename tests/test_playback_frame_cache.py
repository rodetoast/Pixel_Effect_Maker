import os
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.services.effect_playback_service import PlaybackFrame,PlaybackFrameCache,PlaybackFrameKey
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def window(tmp_path,frames=6):
    project=Project.create_default(width=16,height=16,fps=12,frame_count=frames)
    settings=QSettings(str(tmp_path/"playback.ini"),QSettings.Format.IniFormat)
    return MainWindow(ShortcutSettingsService(settings),project)


def wait_ready(value,minimum=1,timeout_ms=3000):
    started=perf_counter()
    def pending():
        plan=value._playback_plan
        return len(value.effect_playback.cache)<minimum or (plan is not None and plan.full_prebuffer and value._playback_state!="playing")
    while pending() and (perf_counter()-started)*1000<timeout_ms:
        APP.processEvents()
    assert not pending()


def finish(value):
    value.set_playing(False);value.dirty=False;value._non_undo_dirty=False;value.close();APP.processEvents()


def test_playback_cache_uses_exact_rendered_frames(tmp_path):
    value=window(tmp_path);layer=value.project.layers[0];value.project.frames[2].layer_pixels[layer.id][3,4]=[20,40,220,255]
    value.set_playing(True);wait_ready(value,3)
    cached=value.effect_playback.get(value._playback_key(2))
    assert cached is not None
    assert np.array_equal(cached.rgba,value.project.compose_frame(2));finish(value)


def test_cache_hit_does_not_rerender_or_recreate_display_objects(tmp_path):
    value=window(tmp_path);value.set_playing(True);wait_ready(value,6)
    renders=value.effect_playback.collector.render_calls;qimages=value.effect_playback.collector.qimage_creations;pixmaps=value.effect_playback.collector.pixmap_creations
    for _ in range(10):assert value._display_cached_playback_frame(3)
    assert value.effect_playback.collector.render_calls==renders
    assert value.effect_playback.collector.qimage_creations==qimages
    assert value.effect_playback.collector.pixmap_creations==pixmaps
    finish(value)


def test_render_revision_invalidates_cache_but_selection_and_pan_do_not(tmp_path):
    value=window(tmp_path);value.set_playing(True);wait_ready(value,2);value.set_playing(False)
    generation=value.effect_playback.generation;count=len(value.effect_playback.cache)
    value.canvas.set_layer(0);value.canvas.pan_offset.setX(12)
    assert value.effect_playback.generation==generation and len(value.effect_playback.cache)==count
    value._mark_dirty()
    assert value.effect_playback.generation>generation and len(value.effect_playback.cache)==0
    finish(value)


def test_playback_cache_has_byte_limit_and_evicts_oldest():
    cache=PlaybackFrameCache(maximum_bytes=100);pixmap=QPixmap(1,1)
    def frame(index):
        rgba=np.zeros((2,2,4),dtype=np.uint8);key=PlaybackFrameKey(1,1,index,(2,2),(),());return PlaybackFrame(key,rgba,pixmap,64)
    first,second=frame(0),frame(1);cache.put(first);cache.put(second)
    assert cache.current_bytes<=100 and len(cache)==1
    assert cache.get(first.key) is None and cache.get(second.key) is second and cache.evictions==1


def test_project_transition_clears_playback_cache(tmp_path):
    value=window(tmp_path);value.set_playing(True);wait_ready(value,2);value.set_playing(False)
    from app.ui.new_project_dialog import NewProjectSettings
    value.apply_new_project_settings(NewProjectSettings("Next",8,8,12,True,2))
    assert len(value.effect_playback.cache)==0
    assert value.canvas.playback_pixmap is None
    finish(value)


def test_playback_missing_frame_does_not_render_on_ui_thread(tmp_path,monkeypatch):
    value=window(tmp_path);calls=[]
    monkeypatch.setattr(value.effect_playback,"get",lambda key:calls.append(key) or None)
    assert not value._display_cached_playback_frame(4)
    assert calls and value.effect_playback.collector.render_calls==0
    finish(value)


def particle_window(tmp_path):
    value=window(tmp_path,4);pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[1,1]=[255,80,20,255]
    asset=SourceAsset("spark",pixels,pivot_x=1,pivot_y=1);composition=ResourceComposition("R",3,3,12,4,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,3,pivot_x=1,pivot_y=1));value.project.source_assets.append(asset);value.project.resource_compositions.append(composition)
    layer=value.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);layer.particle_settings.output_frame_count=4;layer.particle_settings.particle_count_min=layer.particle_settings.particle_count_max=10
    layer.particle_settings.motion.mode="orbit";layer.particle_settings.motion.radius_start=2;layer.particle_settings.motion.radius_end=5;layer.particle_settings.motion.revision+=1;layer.layer_transform.position_x=2;layer.layer_transform.revision+=1
    value._mark_dirty();return value,layer


def test_cached_particle_playback_matches_exact_non_mutating_render(tmp_path):
    from copy import deepcopy
    from app.services.effect_resource_layer_render_service import apply_effect_resource_layer_current_frame
    value,layer=particle_window(tmp_path);expected_project=deepcopy(value.project);expected_layer=next(item for item in expected_project.effect_resource_layers if item.id==layer.id)
    apply_effect_resource_layer_current_frame(expected_project,expected_layer,2);expected=expected_project.compose_frame(2)
    value.set_playing(True);wait_ready(value,3);cached=value.effect_playback.get(value._playback_key(2))
    assert cached is not None and np.array_equal(cached.rgba,expected)
    finish(value)


def test_particle_cache_hit_does_not_rerender_particles(tmp_path,monkeypatch):
    from app.services import effect_playback_service
    value,_=particle_window(tmp_path);calls=[];real=effect_playback_service.render_effect_resource_layer_current_frame
    monkeypatch.setattr(effect_playback_service,"render_effect_resource_layer_current_frame",lambda *args,**kwargs:calls.append(args[2]) or real(*args,**kwargs))
    value.set_playing(True);wait_ready(value,4);render_calls=len(calls)
    for _ in range(8):assert value._display_cached_playback_frame(2)
    assert len(calls)==render_calls
    finish(value)


def test_cached_playback_frame_matches_bake_and_png_export(tmp_path):
    from copy import deepcopy
    from PIL import Image
    from app.services.effect_resource_layer_render_service import apply_effect_resource_layer
    from app.services.export_service import export_png_frames
    value,layer=particle_window(tmp_path)
    value.set_playing(True);wait_ready(value,4);cached=value.effect_playback.get(value._playback_key(2))
    assert cached is not None
    baked=deepcopy(value.project);baked_layer=next(item for item in baked.effect_resource_layers if item.id==layer.id)
    apply_effect_resource_layer(baked,baked_layer)
    baked_rgba=baked.compose_frame(2)
    exported=export_png_frames(baked,tmp_path/"playback_export")
    exported_rgba=np.asarray(Image.open(exported[2]).convert("RGBA"))
    assert np.array_equal(cached.rgba,baked_rgba)
    assert np.array_equal(cached.rgba,exported_rgba)
    finish(value)
