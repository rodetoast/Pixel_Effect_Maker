import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from copy import deepcopy

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleMotionSettings
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_resource_layer_render_service import effect_resource_layer_base_frame_key, invalidate_effect_resource_layer_base
from app.services.particle_render_service import PARTICLE_RENDER_STATS
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def context(tmp_path, name="motion-composite", layers=3):
    service = ShortcutSettingsService(QSettings(str(tmp_path / f"{name}.ini"), QSettings.Format.IniFormat))
    window = MainWindow(service)
    pixels = np.zeros((8, 8, 4), dtype=np.uint8)
    pixels[2:6, 2:6] = [255, 90, 20, 220]
    asset = SourceAsset("spark", pixels, pivot_x=4, pivot_y=4)
    composition = ResourceComposition("resource", 8, 8, 12, 4, True)
    composition.layers.append(CompositionLayer("spark", "source_asset", asset.id, 0, 3, pivot_x=4, pivot_y=4))
    window.project.source_assets.append(asset)
    window.project.resource_compositions.append(composition)
    values = [window.create_resource_layer_from_resource(composition.id, PLACEMENT_PARTICLE) for _ in range(layers)]
    selected = values[1 if len(values) > 1 else 0]
    selected.particle_settings.particle_count_min = selected.particle_settings.particle_count_max = 4
    selected.particle_settings.motion = ParticleMotionSettings(mode="orbit", radius_start=8, radius_end=12)
    invalidate_effect_resource_layer_base(selected.id)
    window.select_resource_layer(selected.id)
    window.canvas.resize(760, 700)
    window.show()
    APP.processEvents()
    return window, selected


def wait_for_prewarm(window, timeout=1000):
    elapsed = 0
    while elapsed < timeout:
        APP.processEvents()
        state = window.canvas.interactive_transform_proxy
        if state is not None and not state.active:
            return state
        QTest.qWait(20)
        elapsed += 20
    return window.canvas.interactive_transform_proxy


def wait_for_gizmo_render(window,minimum=1,timeout=2000):
    before=window.interactive_gizmo_renderer.collector.installed;elapsed=0
    while elapsed<timeout and window.interactive_gizmo_renderer.collector.installed<before+minimum:
        APP.processEvents();QTest.qWait(10);elapsed+=10
    APP.processEvents()


def finish(window):
    window.particle_motion_render_timer.stop()
    window.particle_motion_finalize_timer.stop()
    window.resource_transform_render_timer.stop()
    window.resource_transform_finalize_timer.stop()
    window.interactive_proxy_prewarm.cancel()
    window.interactive_proxy_prewarm._poll.stop()
    window._pending_particle_motion.clear()
    window.canvas.clear_interactive_transform_proxy(update=False)
    window.dirty = False
    window._non_undo_dirty = False
    window.close()


def queue_radius(window, layer, value):
    layer.particle_settings.motion.radius_end = value
    layer.particle_settings.motion.revision += 1
    window.canvas.set_effect_guide(layer.id, "particle_system", layer.particle_settings)
    window._queue_particle_motion_render(layer)


def test_motion_drag_reuses_underlay_overlay_and_partial_dirty_rect(tmp_path, monkeypatch):
    window, layer = context(tmp_path)
    prewarmed = wait_for_prewarm(window)
    assert prewarmed is not None and not prewarmed.active
    underlay, overlay = prewarmed.underlay_pixmap, prewarmed.overlay_pixmap
    full_before = PARTICLE_RENDER_STATS["full_sequence_renders"]
    spawn_misses = PARTICLE_RENDER_STATS["spawn_cache_misses"]
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame", lambda *args: (_ for _ in ()).throw(AssertionError("generated frame mutated during drag")))
    monkeypatch.setattr(window.canvas, "_proxy_layers_pixmap", lambda *args: (_ for _ in ()).throw(AssertionError("other layers recomposited")))
    queue_radius(window, layer, 20)
    window.particle_motion_render_timer.stop()
    window._flush_particle_motion_current()
    wait_for_gizmo_render(window)
    state = window.canvas.interactive_transform_proxy
    assert state.active and state.underlay_pixmap is underlay and state.overlay_pixmap is overlay
    assert PARTICLE_RENDER_STATS["full_sequence_renders"] == full_before
    assert PARTICLE_RENDER_STATS["spawn_cache_misses"] == spawn_misses
    dirty = window.canvas.last_proxy_dirty_rect
    assert not dirty.isNull() and dirty.width() * dirty.height() < window.canvas.width() * window.canvas.height()
    finish(window)


def test_fifty_motion_requests_are_latest_wins_without_full_sequence(tmp_path):
    window, layer = context(tmp_path, "latest")
    assert wait_for_prewarm(window) is not None
    current_before = PARTICLE_RENDER_STATS["current_frame_renders"]
    full_before = PARTICLE_RENDER_STATS["full_sequence_renders"]
    for value in range(50):
        queue_radius(window, layer, 12 + value)
    assert window.particle_motion_render_timer.isActive()
    assert window._pending_particle_motion == {layer.id: (layer.particle_settings.motion.revision, window.frame_index)}
    window.particle_motion_render_timer.stop()
    window._flush_particle_motion_current()
    wait_for_gizmo_render(window)
    window.particle_motion_finalize_timer.stop()
    assert window.canvas.proxy_stats["motion_apply_calls"] == 1
    assert PARTICLE_RENDER_STATS["current_frame_renders"] == current_before + 1
    assert PARTICLE_RENDER_STATS["full_sequence_renders"] == full_before
    assert window._pending_particle_motion == {layer.id: (layer.particle_settings.motion.revision, window.frame_index)}
    finish(window)


def test_motion_local_z_does_not_rebuild_effect_depth_buffers(tmp_path):
    window, layer = context(tmp_path, "local-z")
    assert wait_for_prewarm(window) is not None
    before = window.canvas.proxy_prewarm_token(layer, effect_resource_layer_base_frame_key(window.project, layer, 0)).composite_key
    layer.particle_settings.motion.center_z += 40
    layer.particle_settings.motion.revision += 1
    after = window.canvas.proxy_prewarm_token(layer, effect_resource_layer_base_frame_key(window.project, layer, 0)).composite_key
    assert before == after
    finish(window)


def test_motion_release_runs_one_exact_current_frame_render(tmp_path, monkeypatch):
    window, layer = context(tmp_path, "release", 1)
    before_installs=window.interactive_gizmo_renderer.collector.final_exact_installs
    queue_radius(window, layer, 30)
    window.particle_motion_render_timer.stop()
    window._flush_particle_motion_final()
    elapsed=0
    while elapsed<2000 and window.interactive_gizmo_renderer.collector.final_exact_installs==before_installs:
        APP.processEvents();QTest.qWait(10);elapsed+=10
    assert window.interactive_gizmo_renderer.collector.final_exact_installs==before_installs+1
    assert not window._pending_particle_motion and window.canvas.interactive_transform_proxy is None
    finish(window)


def test_motion_prewarm_renders_current_frame_not_full_sequence(tmp_path):
    window, layer = context(tmp_path, "prewarm-current", 1)
    window.interactive_proxy_prewarm.cancel()
    window.canvas.interactive_transform_proxy = None
    full_before = PARTICLE_RENDER_STATS["full_sequence_renders"]
    current_before = PARTICLE_RENDER_STATS["current_frame_renders"]
    window._schedule_resource_transform_prewarm()
    assert wait_for_prewarm(window) is not None
    assert PARTICLE_RENDER_STATS["full_sequence_renders"] == full_before
    assert current_before+1 <= PARTICLE_RENDER_STATS["current_frame_renders"] <= current_before+2
    finish(window)
