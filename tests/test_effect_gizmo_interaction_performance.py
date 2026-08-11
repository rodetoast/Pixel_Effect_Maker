import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from copy import deepcopy

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleMotionSettings
from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_resource_layer_render_service import (
    invalidate_effect_resource_layer_base,
    render_effect_resource_layer_current_frame,
)
from app.services.particle_render_service import PARTICLE_RENDER_STATS
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.undo_commands import EditorValueCommand


APP = QApplication.instance() or QApplication([])


def wait_until(predicate, timeout=5000):
    elapsed = 0
    while elapsed < timeout and not predicate():
        APP.processEvents(); QTest.qWait(10); elapsed += 10
    APP.processEvents()
    return predicate()


def test_600_canvas_five_layers_hundred_motion_moves_are_transient_latest_wins_and_exact(tmp_path):
    project = Project.create_default(width=600, height=600, fps=12, frame_count=12)
    settings = QSettings(str(tmp_path / "gizmo-performance.ini"), QSettings.Format.IniFormat)
    window = MainWindow(ShortcutSettingsService(settings), initial_project=project)
    pixels = np.zeros((8, 8, 4), dtype=np.uint8); pixels[2:6, 2:6] = [255, 90, 20, 220]
    asset = SourceAsset("spark", pixels, pivot_x=4, pivot_y=4)
    composition = ResourceComposition("resource", 8, 8, 12, 12, True)
    composition.layers.append(CompositionLayer("spark", "source_asset", asset.id, 0, 11, pivot_x=4, pivot_y=4))
    project.source_assets.append(asset); project.resource_compositions.append(composition)
    layers = [window.create_resource_layer_from_resource(composition.id, PLACEMENT_PARTICLE) for _ in range(5)]
    selected = layers[2]; selected.particle_settings.particle_count_min = selected.particle_settings.particle_count_max = 100
    selected.particle_settings.motion = ParticleMotionSettings(mode="orbit", radius_start=8, radius_end=12)
    invalidate_effect_resource_layer_base(selected.id); window.select_resource_layer(selected.id)
    window.canvas.resize(760, 700); window.show(); APP.processEvents()
    assert wait_until(lambda: window.canvas.interactive_transform_proxy is not None)

    before_model = deepcopy(selected); full_before = PARTICLE_RENDER_STATS["full_sequence_renders"]
    current_before = PARTICLE_RENDER_STATS["current_frame_renders"]
    submitted_before = window.interactive_gizmo_renderer.collector.submitted
    for value in range(100):
        transient = deepcopy(selected); transient.particle_settings.motion.radius_end = 12 + value
        transient.particle_settings.motion.revision = selected.particle_settings.motion.revision + value + 1
        window._queue_particle_motion_render(transient)
    assert selected.to_dict() == before_model.to_dict()
    window.particle_motion_render_timer.stop(); window._flush_particle_motion_current()
    assert wait_until(lambda: window.interactive_gizmo_renderer.collector.installed > 0)
    assert window.interactive_gizmo_renderer.collector.submitted == submitted_before + 1
    assert PARTICLE_RENDER_STATS["current_frame_renders"] == current_before + 1
    assert PARTICLE_RENDER_STATS["full_sequence_renders"] == full_before

    before = deepcopy(selected); after = deepcopy(selected)
    after.particle_settings.motion.radius_end += 25; after.particle_settings.motion.revision += 1
    exact_before = window.interactive_gizmo_renderer.collector.final_exact_installs
    window.application_undo_stack.push(EditorValueCommand(window, selected.id, "resource_layer_interaction", before, after, "Motion Gizmo"))
    assert wait_until(lambda: window.interactive_gizmo_renderer.collector.final_exact_installs == exact_before + 1)
    generated = next(item for item in project.layers if item.id == selected.generated_layer_id)
    assert np.array_equal(project.frames[0].layer_pixels[generated.id], render_effect_resource_layer_current_frame(project, selected, 0))
    for action in (window.application_undo_stack.undo, window.application_undo_stack.redo):
        exact_before = window.interactive_gizmo_renderer.collector.final_exact_installs; action()
        assert wait_until(lambda: window.interactive_gizmo_renderer.collector.final_exact_installs == exact_before + 1)
        assert np.array_equal(project.frames[0].layer_pixels[generated.id], render_effect_resource_layer_current_frame(project, selected, 0))

    window.dirty = False; window._non_undo_dirty = False; window.close()
