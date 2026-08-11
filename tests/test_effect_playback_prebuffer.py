import os
from threading import Event
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_resource_layer_render_service import invalidate_effect_resource_layer_base
from app.services.alpha_composite_service import ALPHA_COMPOSITE_STATS,reset_alpha_composite_stats
from app.services.effect_playback_service import (
    PLAYBACK_FULL_PREBUFFER_MAX_FRAMES,
    PLAYBACK_PLAYING,
    PLAYBACK_PREPARING,
    PLAYBACK_STOPPED,
)
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


class FakeClock:
    def __init__(self):self.ms=0;self.starts=0
    def start(self):self.ms=0;self.starts+=1
    def elapsed(self):return self.ms


def window(tmp_path,frames=12,fps=12,size=16):
    project=Project.create_default(width=size,height=size,fps=fps,frame_count=frames)
    settings=QSettings(str(tmp_path/f"prebuffer-{frames}-{size}.ini"),QSettings.Format.IniFormat)
    settings.setValue("ui/language","en")
    return MainWindow(ShortcutSettingsService(settings),project)


def wait_for(predicate,timeout=5000):
    started=perf_counter()
    while not predicate() and (perf_counter()-started)*1000<timeout:APP.processEvents()
    APP.processEvents();assert predicate()


def finish(value):
    value.set_playing(False);value.dirty=False;value._non_undo_dirty=False;value.close();APP.processEvents()


def test_short_sequence_does_not_start_clock_before_all_frames_ready(tmp_path,monkeypatch):
    from app.services import effect_playback_service
    value=window(tmp_path);clock=FakeClock();value._playback_clock=clock;entered=Event();release=Event()
    real=effect_playback_service.render_exact_playback_frame
    def blocked(*args,**kwargs):
        entered.set();release.wait(2);return real(*args,**kwargs)
    monkeypatch.setattr(effect_playback_service,"render_exact_playback_frame",blocked)
    value.set_playing(True);assert entered.wait(2)
    assert value._playback_state==PLAYBACK_PREPARING and clock.starts==0 and value.frame_index==0
    assert "Preparing playback" in value.timeline.playback_status_label.text()
    clock.ms=900;release.set();wait_for(lambda:value._playback_state==PLAYBACK_PLAYING)
    assert clock.starts==1 and clock.ms==0
    assert value.effect_playback.ready_count(value._playback_plan.keys)==12
    assert value.effect_playback.collector.cache_misses==0
    assert value.effect_playback.collector.frame_drops==0
    finish(value)


def test_short_first_loop_is_fully_ready_and_warm_replay_renders_nothing(tmp_path):
    value=window(tmp_path);value.set_playing(True);wait_for(lambda:value._playback_state==PLAYBACK_PLAYING)
    assert value._playback_plan.full_prebuffer
    assert value.effect_playback.ready_count(value._playback_plan.keys)==12
    renders=value.effect_playback.collector.render_calls;value.set_playing(False);assert value._playback_state==PLAYBACK_STOPPED
    value.set_playing(True)
    assert value._playback_state==PLAYBACK_PLAYING
    assert value.effect_playback.collector.render_calls==renders
    for _ in range(24):value._advance_playback(True)
    assert value.effect_playback.collector.underruns==0
    assert value.effect_playback.collector.frame_drops==0
    finish(value)


def test_long_sequence_starts_after_half_second_buffer_not_full_cache(tmp_path):
    value=window(tmp_path,frames=40,fps=12);value.set_playing(True)
    assert value._playback_state==PLAYBACK_PREPARING and not value._playback_plan.full_prebuffer
    assert len(value._playback_plan.required_keys)==6
    wait_for(lambda:value._playback_state==PLAYBACK_PLAYING)
    assert value.effect_playback.ready_count(value._playback_plan.required_keys)==6
    assert len(value.effect_playback.cache)<40
    wait_for(lambda:len(value.effect_playback.cache)==40)
    finish(value)


def test_memory_budget_falls_back_from_short_full_prebuffer(tmp_path):
    value=window(tmp_path,frames=PLAYBACK_FULL_PREBUFFER_MAX_FRAMES,fps=60,size=64)
    value.effect_playback.cache.maximum_bytes=512*1024
    value.set_playing(True)
    assert not value._playback_plan.full_prebuffer
    assert len(value._playback_plan.required_keys)==15
    finish(value)


def test_stop_during_preparation_cancels_clock_and_rejects_late_result(tmp_path,monkeypatch):
    from app.services import effect_playback_service
    value=window(tmp_path);entered=Event();release=Event()
    def blocked(_project,_index,*_args):
        entered.set();release.wait(2);return np.zeros((16,16,4),dtype=np.uint8),{}
    monkeypatch.setattr(effect_playback_service,"render_exact_playback_frame",blocked)
    value.set_playing(True);assert entered.wait(2);generation=value.effect_playback.generation
    value.set_playing(False);release.set();wait_for(lambda:value.effect_playback.generation>generation)
    APP.processEvents()
    assert value._playback_state==PLAYBACK_STOPPED and not value.play_timer.isActive()
    assert len(value.effect_playback.cache)==0
    finish(value)


def test_prebuffer_starts_from_current_frame_and_wraps_frame_zero(tmp_path):
    value=window(tmp_path);value.frame_index=7;value.set_playing(True)
    assert [key.frame_index for key in value._playback_plan.keys]==[7,8,9,10,11,0,1,2,3,4,5,6]
    wait_for(lambda:value._playback_state==PLAYBACK_PLAYING)
    assert value._playback_start_frame==7
    assert value.effect_playback.cache.contains(value._playback_key(0))
    finish(value)


def test_edit_and_gizmo_start_cancel_preparation(tmp_path,monkeypatch):
    from app.services import effect_playback_service
    for action in ("edit","gizmo"):
        value=window(tmp_path);entered=Event();release=Event()
        def blocked(_project,_index,*_args):
            entered.set();release.wait(2);return np.zeros((16,16,4),dtype=np.uint8),{}
        monkeypatch.setattr(effect_playback_service,"render_exact_playback_frame",blocked)
        value.set_playing(True);assert entered.wait(2);generation=value.effect_playback.generation
        if action=="edit":value._mark_dirty()
        else:value._begin_effect_gizmo_interaction()
        release.set();APP.processEvents()
        assert value._playback_state==PLAYBACK_STOPPED
        assert value.effect_playback.generation>generation
        finish(value)


def test_600_canvas_particle_five_layer_cold_prebuffer_has_zero_first_loop_misses(tmp_path):
    value=window(tmp_path,frames=12,fps=12,size=600);project=value.project
    for index in range(3):
        layer=project.add_layer(f"Static {index+2}")
        for frame in project.frames:frame.layer_pixels[layer.id][20+index:28+index,20:28]=[40+index*50,80,220,180]
    pixels=np.zeros((8,8,4),dtype=np.uint8);pixels[2:6,2:6]=[255,90,20,220]
    asset=SourceAsset("spark",pixels,pivot_x=4,pivot_y=4);composition=ResourceComposition("resource",8,8,12,12,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,11,pivot_x=4,pivot_y=4))
    project.source_assets.append(asset);project.resource_compositions.append(composition)
    particle=value.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    particle.particle_settings.particle_count_min=particle.particle_settings.particle_count_max=100
    particle.particle_settings.output_frame_count=12;project.frames=project.frames[:12]
    invalidate_effect_resource_layer_base(particle.id);value._mark_dirty();reset_alpha_composite_stats()
    started=perf_counter();value.set_playing(True);wait_for(lambda:value._playback_state==PLAYBACK_PLAYING,15000)
    wall_ms=(perf_counter()-started)*1000.0;plan=value._playback_plan
    assert plan.full_prebuffer and value.effect_playback.ready_count(plan.keys)==12
    for _ in range(24):value._advance_playback(True)
    assert value.effect_playback.collector.underruns==0 and value.effect_playback.collector.frame_drops==0
    average=value.effect_playback.collector.average("exact_frame_generation")
    assert ALPHA_COMPOSITE_STATS["roi_pixels"]<ALPHA_COMPOSITE_STATS["source_pixels"]
    print(f"PLAYBACK_PREBUFFER_600 wall_ms={wall_ms:.3f} exact_avg_ms={average:.3f} particle_ms={value.effect_playback.collector.average('particle_exact_render'):.3f} layer_composite_ms={value.effect_playback.collector.average('layer_alpha_composite'):.3f} cache_install_ms={value.effect_playback.collector.average('qimage_to_qpixmap'):.3f} roi_pixels={ALPHA_COMPOSITE_STATS['roi_pixels']} source_pixels={ALPHA_COMPOSITE_STATS['source_pixels']}")
    finish(value)
