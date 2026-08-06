import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from copy import deepcopy
import json

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.frame_payload_codec import DEFAULT_FRAME_PAYLOAD_CODEC
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings, ParticleMotionSettings
from app.models.project import Project
from app.models.resource_composition import ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.project_io import SavePerformanceCollector, load_project, save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def motion_project():
    project = Project.create_default(width=16, height=16)
    pixels = np.zeros((4, 4, 4), dtype=np.uint8)
    pixels[1:3, 1:3] = [240, 100, 30, 255]
    asset = SourceAsset("spark", pixels)
    composition = ResourceComposition("resource", width=4, height=4, frame_count=4)
    project.source_assets.append(asset)
    project.resource_compositions.append(composition)
    settings = ParticleEmitterSettings(
        composition.id,
        resource_type="resource_composition",
        output_frame_count=4,
        particle_count_min=1,
        particle_count_max=1,
        speed_min=0,
        speed_max=0,
        lifetime_min=4,
        lifetime_max=4,
        motion=ParticleMotionSettings(mode="orbit", radius_start=3, radius_end=6),
    )
    layer = EffectResourceLayer(
        "orbit", composition.id, placement_mode=PLACEMENT_PARTICLE,
        end_frame=3, particle_settings=settings,
    )
    project.effect_resource_layers.append(layer)
    return project, layer, asset


def motion_window(tmp_path):
    project, layer, asset = motion_project()
    service = ShortcutSettingsService(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    window = MainWindow(service, initial_project=project)
    window._dirty_particle_motion_layers.add(layer.id)
    window._pending_particle_motion[layer.id] = (layer.particle_settings.motion.revision, 0)
    window.dirty = True
    return window, layer, asset


def close_window(window):
    window.particle_motion_render_timer.stop()
    window.particle_motion_finalize_timer.stop()
    window.dirty = False
    window._non_undo_dirty = False
    window.close()


def test_motion_metadata_save_does_not_materialize_particle_sequence(tmp_path, monkeypatch):
    window, _, _ = motion_window(tmp_path)
    monkeypatch.setattr(window, "_materialize_resource_transform_sequences", lambda: (_ for _ in ()).throw(AssertionError("materialized")))
    assert window._save_to_path(tmp_path / "motion.peffect.json")
    close_window(window)


def test_motion_metadata_save_does_not_render_particle_frames(tmp_path, monkeypatch):
    window, _, _ = motion_window(tmp_path)
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer", lambda *args: (_ for _ in ()).throw(AssertionError("full render")))
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame", lambda *args: (_ for _ in ()).throw(AssertionError("frame render")))
    assert window._save_to_path(tmp_path / "motion.peffect.json")
    close_window(window)


def test_motion_metadata_save_does_not_run_bake(tmp_path, monkeypatch):
    window, _, _ = motion_window(tmp_path)
    monkeypatch.setattr(window, "bake_particle_emitter", lambda *args: (_ for _ in ()).throw(AssertionError("bake")))
    assert window._save_to_path(tmp_path / "motion.peffect.json")
    close_window(window)


def test_motion_metadata_save_does_not_run_export(tmp_path, monkeypatch):
    window, _, _ = motion_window(tmp_path)
    monkeypatch.setattr("app.ui.main_window.export_preview_sequence", lambda *args: (_ for _ in ()).throw(AssertionError("export")))
    monkeypatch.setattr("app.ui.main_window.export_png_frames", lambda *args: (_ for _ in ()).throw(AssertionError("export")))
    assert window._save_to_path(tmp_path / "motion.peffect.json")
    close_window(window)


def test_motion_metadata_save_does_not_reencode_source_pixels(tmp_path):
    project, layer, _ = motion_project()
    codec = DEFAULT_FRAME_PAYLOAD_CODEC
    codec.clear()
    save_project(project, tmp_path / "first")
    codec.reset_stats()
    layer.particle_settings.motion.radius_start = 9
    layer.particle_settings.motion.revision += 1
    save_project(project, tmp_path / "second")
    assert codec.stats.encode_calls == 0


def test_motion_metadata_save_preserves_dirty_sequence_state(tmp_path):
    window, layer, _ = motion_window(tmp_path)
    pending = dict(window._pending_particle_motion)
    dirty = set(window._dirty_particle_motion_layers)
    assert window._save_to_path(tmp_path / "motion.peffect.json")
    assert window._pending_particle_motion == pending
    assert window._dirty_particle_motion_layers == dirty == {layer.id}
    close_window(window)


def test_motion_metadata_round_trip_without_materialization(tmp_path, monkeypatch):
    window, layer, _ = motion_window(tmp_path)
    expected = deepcopy(layer.particle_settings.motion)
    calls = []
    import app.services.project_io as project_io
    original_replace = project_io.os.replace
    monkeypatch.setattr(project_io.os, "replace", lambda source, target: (calls.append((source, target)), original_replace(source, target))[1])
    target = tmp_path / "motion.peffect.json"
    assert window._save_to_path(target)
    loaded = load_project(target)
    actual = loaded.effect_resource_layers[0].particle_settings.motion
    assert actual == expected and len(calls) == 1
    assert json.loads(target.read_text(encoding="utf-8"))["format_version"] == 8
    close_window(window)
