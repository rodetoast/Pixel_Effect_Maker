from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QAbstractButton

from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.external_tools_dialog import ExternalToolsDialog
from app.ui.interface_settings_dialog import InterfaceSettingsDialog
from app.ui.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
from app.ui.project_settings_dialog import ProjectSettingsDialog
from app.ui.resource_editor_v2.new_resource_dialog import NewResourceDialog
from app.ui.startup_dialog import StartupDialog


APPLICATION = QApplication.instance() or QApplication([])
SYMBOL_ONLY_TEXT = {"▶", "■", "◀", "▶|", "◆", "×"}
# Qt owns the menu overflow button and supplies its platform behavior; application
# code cannot attach stable localized help to this private implementation detail.
QT_INTERNAL_BUTTONS = {"qt_menubar_ext_button", "qt_tableview_cornerbutton"}


def service(tmp_path, language="en"):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", language)
    return ShortcutSettingsService(settings)


def test_active_application_buttons_have_tooltips(tmp_path):
    window = MainWindow(service(tmp_path))
    missing = []
    for button in window.findChildren(QAbstractButton):
        if button.objectName() in QT_INTERNAL_BUTTONS:
            continue
        if not button.toolTip().strip():
            missing.append(button.objectName() or f"{type(button).__name__}:{button.text()!r}")
    assert missing == [], missing
    window.dirty = False
    window.close()


def test_major_actions_have_behavior_tooltips_and_status_tips(tmp_path):
    window = MainWindow(service(tmp_path))
    actions = (
        window.new_action, window.open_action, window.save_action, window.save_as_action,
        window.project_settings_action, window.import_source_action, window.import_resources_action,
        window.external_tools_action, window.export_action, window.keyboard_shortcuts_action,
        window.undo_action, window.redo_action, window.new_layer_action, window.delete_layer_action,
        window.new_frame_action, window.new_empty_frame_action, window.delete_frame_action,
        window.play_action, window.status_bar_action, window.interface_settings_action,
    )
    assert all(action.toolTip().strip() and action.statusTip().strip() for action in actions)
    assert all(action.toolTip().strip() != action.text().replace("&", "").strip() for action in actions)
    window.dirty = False
    window.close()


def test_runtime_language_and_configured_shortcut_update_existing_tooltips(tmp_path):
    window = MainWindow(service(tmp_path, "ko"))
    assert "이펙트 에디터" in window.effect_workspace_button.toolTip()
    assert "단축키: Enter" in window.timeline.play_button.toolTip()
    window.localization.set_language("en")
    assert "Effect Editor" in window.effect_workspace_button.toolTip()
    assert "Shortcut: Enter" in window.timeline.play_button.toolTip()
    updated = dict(window.shortcuts)
    updated["play_stop_animation"] = ["P"]
    assert window.apply_shortcuts(updated)
    assert "Shortcut: P" in window.timeline.play_button.toolTip()
    assert "Shortcut: P" in window.resource_editor.composition_timeline.play.toolTip()
    window.dirty = False
    window.close()


def test_play_and_visibility_tooltips_follow_current_state(tmp_path):
    window = MainWindow(service(tmp_path, "en"))
    assert "Play" in window.timeline.play_button.toolTip()
    window.set_playing(True)
    assert "Pause" in window.timeline.play_button.toolTip()
    window.set_playing(False)
    assert "Play" in window.timeline.play_button.toolTip()

    asset = SourceAsset("asset", __import__("numpy").zeros((2, 2, 4), dtype="uint8"))
    layer = CompositionLayer("Layer", "source_asset", asset.id, 0, 1)
    composition = ResourceComposition("Resource", 2, 2, 12, 2, True, layers=[layer])
    window.project.source_assets.append(asset)
    window.project.resource_compositions.append(composition)
    inspector = window.resource_editor.layer_inspector
    inspector.set_layer(layer, asset, 0)
    assert "Hide" in inspector.visible.toolTip()
    inspector.visible.setChecked(False)
    assert "Show" in inspector.visible.toolTip()
    window.dirty = False
    window.close()


def test_resource_gizmo_and_property_symbol_controls_have_localized_help(tmp_path):
    window = MainWindow(service(tmp_path, "en"))
    inspector = window.resource_editor.layer_inspector
    assert "selected layer" in inspector.mode_buttons["move"].toolTip()
    assert "Shift" in inspector.mode_buttons["rotate"].toolTip()
    assert "origin" in inspector.mode_buttons["pivot"].toolTip()
    layer = CompositionLayer("Layer", "source_asset", "asset", 0, 11)
    layer.add_property("rotation")
    inspector.set_layer(layer, None, 0)
    controls = inspector.property_cards["rotation"]
    assert "keyframe" in controls["keyframe"].toolTip().lower()
    assert "keyframes" in controls["remove"].toolTip().lower()
    window.localization.set_language("ko")
    assert "선택한 레이어" in inspector.mode_buttons["move"].toolTip()
    window.dirty = False
    window.close()


def test_major_dialog_controls_have_behavior_tooltips(tmp_path):
    window = MainWindow(service(tmp_path, "en"))
    localization = window.localization
    startup = StartupDialog(None, localization)
    project = ProjectSettingsDialog(window.project, None, lambda values: True, localization=localization)
    shortcuts = KeyboardShortcutsDialog(window.shortcuts, localization=localization)
    interface = InterfaceSettingsDialog(window.settings_service.settings, localization)
    external = ExternalToolsDialog(window.settings_service.settings, localization)
    resource = NewResourceDialog(None, localization, defaults=(64, 64, 12, True))
    controls = (
        startup.create_button, startup.open_button, project.apply_button,
        *project.anchor_by_button.keys(), shortcuts.restore_button, shortcuts.apply_button,
        interface.reset, external.browse, external.detect, external.validate, external.clear,
        resource.create, resource.length_unit,
    )
    assert all(control.toolTip().strip() for control in controls)
    for dialog in (startup, project, shortcuts, interface, external, resource):
        dialog.close()
    window.dirty = False
    window.close()
