from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.project import FORMAT_VERSION, Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.localization_service import LocalizationService
from app.services.resource_composition_render_service import render_composition_frame
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.ui.resource_editor_v2.composition_inspector import LayerInspector


APP = QApplication.instance() or QApplication([])


def localization(tmp_path, language="en"):
    settings = QSettings(str(tmp_path / f"{language}.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", language)
    return LocalizationService(settings, system_locale="en_US")


def effect_context(tmp_path, language="en"):
    project = Project.create_default(width=24, height=24, frame_count=3)
    composition = ResourceComposition("sprite", 24, 24, 12, 3, True)
    project.resource_compositions.append(composition)
    layer = EffectResourceLayer("layer", composition.id, placement_mode=PLACEMENT_PARTICLE, end_frame=2)
    project.effect_resource_layers.append(layer)
    panel = ParticlePropertiesPanel(); panel.retranslate_ui(localization(tmp_path, language)); panel.set_resource_layer(layer, project)
    panel.resize(320, 720); panel.show(); APP.processEvents()
    return project, layer, panel


def resource_context(tmp_path, language="en"):
    pixels = np.zeros((9, 11, 4), dtype=np.uint8); pixels[1:8, 2:10] = [220, 70, 30, 255]
    project = Project.create_default(width=24, height=24, frame_count=1)
    asset = SourceAsset("sprite", pixels); project.source_assets.append(asset)
    composition = ResourceComposition("sprite", 24, 24, 12, 1, True)
    layer = CompositionLayer("sprite", "source_asset", asset.id, 0, 0, pivot_x=asset.pivot_x, pivot_y=asset.pivot_y)
    for name in ("rotation_x", "rotation_y", "rotation", "perspective_strength"): layer.add_property(name)
    composition.layers.append(layer); project.resource_compositions.append(composition)
    inspector = LayerInspector(); inspector.retranslate(localization(tmp_path, language)); inspector.set_layer(layer, asset, 0)
    return project, asset, composition, layer, inspector


def test_resource_editor_exposes_sprite_2_5d_as_primary_transform(tmp_path):
    _, _, _, _, inspector = resource_context(tmp_path)
    assert {"rotate_x", "rotate_y", "rotate", "scale", "pivot"} <= set(inspector.mode_buttons)
    assert all(button.isVisibleTo(inspector) for button in inspector.mode_buttons.values())
    inspector.close()


def test_effect_editor_system_and_surface_are_inside_advanced(tmp_path):
    _, _, panel = effect_context(tmp_path)
    transform = panel.transform_panel
    assert transform.system_group.parentWidget() is transform.advanced_body
    assert transform.surface_group.parentWidget() is transform.advanced_body
    assert panel.layout.indexOf(transform) > panel.layout.indexOf(panel.motion_basic_group)
    panel.close()


def test_advanced_section_defaults_enabled_and_visible(tmp_path):
    _, _, panel = effect_context(tmp_path)
    assert panel.transform_panel.is_advanced_expanded()
    assert panel.transform_panel.advanced_body.isVisibleTo(panel)
    panel.close()


def test_system_space_help_points_to_resource_editor_for_sprite_tilt(tmp_path):
    _, _, panel = effect_context(tmp_path, "en")
    assert "spawn positions" in panel.transform_panel.description.text()
    assert "Resource Editor" in panel.transform_panel.description.text()
    panel.close()


def test_surface_transform_marks_nonidentity_legacy_state(tmp_path):
    project, layer, panel = effect_context(tmp_path)
    assert not panel.transform_panel.advanced_status.isVisibleTo(panel)
    layer.surface_transform.rotation_y = 12
    panel.set_resource_layer(layer, project); APP.processEvents()
    assert panel.transform_panel.advanced_status.isVisibleTo(panel)
    assert "applied" in panel.transform_panel.advanced_status.text().lower()
    panel.close()


def test_perspective_names_and_help_are_role_specific(tmp_path):
    _, _, panel = effect_context(tmp_path, "en")
    transform = panel.transform_panel
    assert transform.form.labelForField(transform.fields["perspective_strength"].parentWidget()).text() == "System Perspective"
    assert transform.surface_form.labelForField(transform.surface_fields["perspective_strength"]).text() == "Surface Perspective"
    assert "motion paths" in transform.fields["perspective_strength"].toolTip()
    assert "post-raster" in transform.surface_fields["perspective_strength"].toolTip()
    assert panel.motion_advanced_group.layout().labelForField(panel.motion_perspective).text() == "Motion Local Perspective"
    panel.close()


def test_resource_perspective_and_rotations_explain_sprite_only(tmp_path):
    _, _, _, _, inspector = resource_context(tmp_path, "en")
    cards = inspector.property_cards
    assert "Sprite plane only" in cards["perspective_strength"]["editors"][0].toolTip()
    assert "Particle motion paths are unchanged" in cards["rotation_x"]["editors"][0].toolTip()
    assert "already tilted" in cards["rotation"]["editors"][0].toolTip()
    inspector.close()


def test_internal_transform_names_are_not_exposed_in_korean_ui(tmp_path):
    _, _, panel = effect_context(tmp_path, "ko")
    visible = " ".join((panel.transform_panel.title(), panel.transform_panel.system_group.title(), panel.transform_panel.surface_group.title(), panel.transform_panel.description.text()))
    assert "Layer Space" not in visible and "Surface Transform" not in visible
    assert "시스템 공간 변형" in visible and "표면 변형 (호환성)" in visible
    panel.close()


def test_advanced_checkbox_emits_only_enable_state(tmp_path):
    project, layer, panel = effect_context(tmp_path)
    before = project.to_dict(); events = []; enabled=[]
    panel.transform_changed.connect(lambda *args: events.append("transform"))
    panel.draft_changed.connect(lambda *args: events.append("draft"))
    panel.transform_panel.surface_transform_changed.connect(lambda *args: events.append("surface"))
    panel.transform_panel.advanced_enabled_changed.connect(lambda _,state:enabled.append(state))
    panel.transform_panel.set_advanced_expanded(False); APP.processEvents()
    assert events == [] and enabled==[False] and project.to_dict() == before and FORMAT_VERSION == 18
    panel.close()


def test_advanced_without_selected_layer_does_not_dirty_or_invalidate(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    window = MainWindow(ShortcutSettingsService(settings)); calls = []
    monkeypatch.setattr(window, "_invalidate_playback_cache", lambda *args, **kwargs: calls.append("invalidate"))
    for name in ("render_effect_resource_layer", "apply_effect_resource_layer", "apply_effect_resource_layer_current_frame", "render_particle_frames"):
        monkeypatch.setattr("app.ui.main_window." + name, lambda *args, _name=name, **kwargs: calls.append(_name))
    window.dirty = False; window._non_undo_dirty = False
    window.composition_layer_properties.transform_panel.set_advanced_expanded(False); APP.processEvents()
    assert not window.dirty and not window._non_undo_dirty and calls == []
    window.close()


def test_advanced_toggle_preserves_resource_rgba(tmp_path):
    project, _, composition, _, inspector = resource_context(tmp_path)
    before = render_composition_frame(project, composition, 0).copy()
    panel = ParticlePropertiesPanel(); effect = EffectResourceLayer("effect", composition.id, placement_mode=PLACEMENT_PARTICLE)
    project.effect_resource_layers.append(effect); panel.set_resource_layer(effect, project)
    panel.transform_panel.set_advanced_expanded(True); panel.transform_panel.set_advanced_expanded(False)
    assert np.array_equal(render_composition_frame(project, composition, 0), before)
    panel.close(); inspector.close()
