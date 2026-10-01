from __future__ import annotations

import json
import os
from copy import deepcopy

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_composition_layer_render_service import render_effect_composition_layer
from app.services.effect_resource_layer_render_service import render_effect_resource_layer
from app.services.particle_render_service import render_particle_frames
from app.services.project_io import load_project, save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def resource_project():
    project = Project.create_default(width=8, height=8)
    pixels = np.zeros((8, 8, 4), dtype=np.uint8); pixels[2:6, 2:6] = [255, 100, 20, 255]
    asset = SourceAsset("Spark", pixels)
    composition = ResourceComposition("Spark", 8, 8, 12, 4, True)
    composition.layers.append(CompositionLayer("Spark", "source_asset", asset.id, 0, 3))
    project.source_assets.append(asset); project.resource_compositions.append(composition)
    return project, composition


def service(tmp_path):
    settings = QSettings(str(tmp_path / "resource-layer.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", "en")
    return ShortcutSettingsService(settings)


def test_resource_layer_defaults_and_mode_switch_preserve_both_settings():
    project, composition = resource_project()
    layer = EffectResourceLayer("Fire", composition.id, start_frame=1, end_frame=3)
    layer.single_settings.end_x = 77
    layer.particle_settings.speed_max = 9
    layer.set_placement_mode("particle"); layer.set_placement_mode("single")
    assert layer.id and layer.visible and layer.placement_mode == "single"
    assert layer.single_settings.end_x == 77 and layer.particle_settings.speed_max == 9


def test_resource_layer_v6_round_trip_omits_legacy_effect_arrays(tmp_path):
    project, composition = resource_project()
    layer = EffectResourceLayer("Fire", composition.id)
    layer.particle_settings.random_start_frame = True
    project.effect_resource_layers.append(layer)
    data = project.to_dict()
    assert data["format_version"] == FORMAT_VERSION == 18
    assert "effect_composition_layers" not in data and "particle_emitters" not in data
    loaded = load_project(save_project(project, tmp_path / "v6.peffect.json"))
    assert loaded.effect_resource_layers[0].to_dict() == layer.to_dict()


def test_v5_layers_migrate_in_physical_order_with_ids_visibility_and_settings():
    project, composition = resource_project()
    particle_output = project.add_layer("Smoke"); particle_output.visible = False
    single_output = project.add_layer("Slash")
    particle = ParticleEmitter("Smoke", ParticleEmitterSettings(composition.id, resource_type="resource_composition", speed_max=7), generated_layer_id=particle_output.id, id="particle-id")
    single = EffectCompositionLayer("Slash", composition.id, start_x=3, end_x=6, generated_layer_id=single_output.id, id="single-id")
    data = project.to_dict(); data["format_version"] = 5; data.pop("effect_resource_layers")
    data["particle_emitters"] = [particle.to_dict()]; data["effect_composition_layers"] = [single.to_dict()]
    loaded = Project.from_dict(data)
    assert [(item.id,item.placement_mode,item.visible) for item in loaded.effect_resource_layers] == [("particle-id","particle",False),("single-id","single",True)]
    assert loaded.effect_resource_layers[0].particle_settings.speed_max == 7
    assert loaded.effect_resource_layers[1].single_settings.start_x == 3


def test_opening_v5_project_does_not_rewrite_source(tmp_path):
    project, _ = resource_project(); data = project.to_dict(); data["format_version"] = 5; data.pop("effect_resource_layers")
    data["particle_emitters"] = []; data["effect_composition_layers"] = []
    path = tmp_path / "legacy.peffect.json"; path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes(); loaded = load_project(path)
    assert path.read_bytes() == before and loaded.format_version == 18


def test_unified_render_dispatch_matches_legacy_renderers():
    project, composition = resource_project()
    single = EffectCompositionLayer("Single", composition.id, start_x=4, start_y=4, end_x=5, end_y=4, end_frame=3)
    unified_single = EffectResourceLayer.from_composition_layer(single)
    assert all(np.array_equal(a,b) for a,b in zip(render_effect_composition_layer(project,single),render_effect_resource_layer(project,unified_single)))
    particle = ParticleEmitter("Particles", ParticleEmitterSettings(composition.id, resource_type="resource_composition", output_frame_count=4, particle_count_min=2, particle_count_max=2, seed=4))
    unified_particle = EffectResourceLayer.from_particle_emitter(particle)
    assert all(np.array_equal(a,b) for a,b in zip(render_particle_frames(project,particle),render_effect_resource_layer(project,unified_particle)))


def test_mode_switch_is_undoable_and_delete_restores_both_modes(tmp_path):
    project, composition = resource_project(); window = MainWindow(service(tmp_path), project)
    layer = window.create_resource_layer_from_resource(composition.id)
    assert window.properties_stack.currentWidget() is window.composition_layer_properties
    layer.single_settings.end_x = 11; layer.particle_settings.seed = 42
    window.set_resource_layer_mode(layer.id,"particle")
    assert layer.placement_mode == "particle"
    assert window.properties_stack.currentWidget() is window.particle_properties
    window.application_undo_stack.undo(); assert layer.placement_mode == "single"
    window.application_undo_stack.redo(); assert layer.placement_mode == "particle"
    window.delete_layer(); assert layer not in project.effect_resource_layers
    window.application_undo_stack.undo()
    restored = project.effect_resource_layers[0]
    assert restored.id == layer.id and restored.single_settings.end_x == 11 and restored.particle_settings.seed == 42
    window.dirty=False;window.close()


def test_resource_layer_add_is_undoable(tmp_path):
    project, composition = resource_project(); window = MainWindow(service(tmp_path), project)
    layer = window.create_resource_layer_from_resource(composition.id); generated_id = layer.generated_layer_id
    window.application_undo_stack.undo()
    assert layer not in project.effect_resource_layers and all(item.id != generated_id for item in project.layers)
    window.application_undo_stack.redo()
    assert project.effect_resource_layers == [layer] and any(item.id == generated_id for item in project.layers)
    window.dirty=False;window.close()
