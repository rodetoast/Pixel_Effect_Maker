import os
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_SINGLE
from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_playback_service import PLAYBACK_PLAYING
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def wait_playing(window,timeout=5000):
    started=perf_counter()
    while window._playback_state!=PLAYBACK_PLAYING and (perf_counter()-started)*1000<timeout:APP.processEvents()
    assert window._playback_state==PLAYBACK_PLAYING


def test_static_single_resource_layer_renders_once_across_twelve_frame_prebuffer(tmp_path,monkeypatch):
    from app.services import effect_playback_service
    project=Project.create_default(width=64,height=64,fps=12,frame_count=12);settings=QSettings(str(tmp_path/"static.ini"),QSettings.Format.IniFormat)
    window=MainWindow(ShortcutSettingsService(settings),project);pixels=np.zeros((8,8,4),dtype=np.uint8);pixels[2:6,2:6]=[255,80,20,255]
    asset=SourceAsset("spark",pixels,pivot_x=4,pivot_y=4);composition=ResourceComposition("static",8,8,12,1,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,0,pivot_x=4,pivot_y=4));project.source_assets.append(asset);project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_SINGLE);layer.single_settings.start_frame=0;layer.single_settings.end_frame=11
    layer.single_settings.start_x=layer.single_settings.end_x;layer.single_settings.start_y=layer.single_settings.end_y
    calls=[];real=effect_playback_service.render_effect_resource_layer_current_frame
    monkeypatch.setattr(effect_playback_service,"render_effect_resource_layer_current_frame",lambda *args,**kwargs:calls.append(args[2]) or real(*args,**kwargs))
    window._mark_dirty();window.set_playing(True);wait_playing(window)
    assert len(calls)==1
    assert window.effect_playback.collector.static_layer_cache_misses==1
    assert window.effect_playback.collector.static_layer_cache_hits==11
    window.dirty=False;window._non_undo_dirty=False;window.close()


def test_animated_single_resource_layer_does_not_use_static_cache(tmp_path):
    from app.services.effect_playback_service import _static_resource_layer_key
    project=Project.create_default(width=16,height=16,fps=12,frame_count=12);window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"animated.ini"),QSettings.Format.IniFormat)),project)
    composition=ResourceComposition("animated",8,8,12,2,True);project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_SINGLE);layer.single_settings.start_frame=0;layer.single_settings.end_frame=11
    assert _static_resource_layer_key(project,layer) is None
    window.dirty=False;window._non_undo_dirty=False;window.close()
