from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QFrame, QPushButton

from app.services.localization_service import LocalizationService
from tests.test_timeline_multi_key_editing import _close, _effect_window


APP = QApplication.instance() or QApplication([])


def _language(tmp_path, language):
    settings = QSettings(str(tmp_path / f"panel-{language}.ini"), QSettings.Format.IniFormat)
    service = LocalizationService(settings, language)
    service.set_language(language)
    return service


def _panel(tmp_path):
    window, single, particle = _effect_window(tmp_path)
    window.show()
    APP.processEvents()
    return window, window.effect_library, single, particle


def _assert_row_fits(row):
    layout = row.layout()
    widgets = [layout.itemAt(index).widget() for index in range(layout.count())]
    visible = [widget for widget in widgets if widget is not None and widget.isVisibleTo(row)]
    assert visible
    geometry = [(widget.objectName(), widget.text() if isinstance(widget, QPushButton) else "separator", widget.geometry().getRect()) for widget in visible]
    assert all(widget.geometry().left() >= 0 and widget.geometry().right() < row.width() for widget in visible), (row.width(), geometry)
    assert all(left.geometry().right() < right.geometry().left() for left, right in zip(visible, visible[1:]))


def test_panel_groups_commands_around_stretch_layer_list(tmp_path):
    window, panel, _single, _particle = _panel(tmp_path)
    layout = panel.composition_group.layout()
    assert [panel.composition_top_toolbar.property("commandGroup"), panel.composition_hierarchy_toolbar.property("commandGroup"), panel.composition_state_toolbar.property("commandGroup")] == ["create_edit", "hierarchy", "state_order"]
    assert layout.stretch(layout.indexOf(panel.composition_list)) == 1
    assert panel.composition_list.minimumHeight() >= 150
    assert len(panel.composition_group.findChildren(QFrame, "resourceLayerCommandSeparator")) == 1
    assert panel.composition_top_separator is None  # Duplicate/Delete separated by spacing, not a divider.
    assert not hasattr(panel, "move_composition_up") and not hasattr(panel, "move_composition_down")
    assert all(button.text() not in {"L", "S"} for button in panel.composition_group.findChildren(QPushButton))
    _close(window)


def test_korean_and_english_labels_are_explicit_and_accessible(tmp_path):
    window, panel, _single, _particle = _panel(tmp_path)
    expected = {
        "en": ("＋ Layer", "Duplicate", "Delete", "Create Group", "Ungroup", "Lock", "Solo", "Order", ["Bring Forward", "Send Back"]),
        "ko": ("＋ 레이어", "복제", "삭제", "그룹 만들기", "그룹 해제", "잠금", "솔로", "순서", ["앞으로", "뒤로"]),
    }
    controls = (panel.add_composition_button, panel.duplicate_composition_button, panel.remove_composition_button, panel.group_composition_button, panel.ungroup_composition_button, panel.lock_composition_button, panel.solo_composition_button, panel.order_composition_button)
    for language, labels in expected.items():
        panel.retranslate_ui(_language(tmp_path, language))
        assert tuple(button.text() for button in controls) == labels[:8]
        assert [action.text() for action in panel.order_composition_menu.actions()] == labels[8]
        assert all(button.accessibleName() and button.accessibleDescription() and button.toolTip() for button in controls)
    assert panel.remove_composition_button.property("commandRole") == "danger"
    assert panel.lock_composition_button.isCheckable() and panel.solo_composition_button.isCheckable()
    _close(window)


def test_toolbar_state_matches_shared_context_state_and_toggle_visual(tmp_path):
    window, panel, single, _particle = _panel(tmp_path)
    panel.select_composition(single.id)
    panel._sync_composition_controls()
    states = panel._composition_command_states()
    assert panel.duplicate_composition_button.isEnabled() == states["duplicate"]
    assert panel.remove_composition_button.isEnabled() == states["delete"]
    assert panel.order_composition_button.isEnabled() == states["reorder"]
    assert panel.order_front_action.isEnabled() == states["reorder"] == panel.order_back_action.isEnabled()
    before = deepcopy(window.project.to_dict())
    panel.retranslate_ui(_language(tmp_path, "ko"))
    assert window.project.to_dict() == before
    panel.lock_composition_button.click()
    APP.processEvents()
    selected = next(layer for layer in window.project.effect_resource_layers if layer.id == single.id)
    assert selected.locked and panel.lock_composition_button.isChecked()
    window.application_undo_stack.undo()
    APP.processEvents()
    assert not next(layer for layer in window.project.effect_resource_layers if layer.id == single.id).locked
    panel.solo_composition_button.click()
    APP.processEvents()
    assert next(layer for layer in window.project.effect_resource_layers if layer.id == single.id).solo and panel.solo_composition_button.isChecked()
    solo_item = next(panel.composition_list.item(row) for row in range(panel.composition_list.count()) if panel.composition_list.item(row).data(Qt.ItemDataRole.UserRole) == single.id)
    assert "Solo" in solo_item.toolTip()
    window.application_undo_stack.undo()
    APP.processEvents()
    assert not next(layer for layer in window.project.effect_resource_layers if layer.id == single.id).solo
    _close(window)


def test_disabled_reasons_order_menu_and_responsive_geometry(tmp_path):
    window, panel, single, _particle = _panel(tmp_path)
    panel.set_resource_selection(set(), None)
    panel._sync_composition_controls()
    assert not panel.group_composition_button.isEnabled() and "two" in panel.group_composition_button.toolTip().lower()
    assert not panel.ungroup_composition_button.isEnabled() and "group" in panel.ungroup_composition_button.toolTip().lower()
    panel.select_composition(single.id)
    moves = []
    panel.move_resource_layer_requested.connect(lambda identifier, direction: moves.append((identifier, direction)))
    panel.order_front_action.trigger()
    panel.order_back_action.trigger()
    assert moves == [(single.id, 1), (single.id, -1)]
    for width, height in ((1280, 720), (1600, 900), (1920, 1080)):
        window.resize(width, height)
        APP.processEvents()
        _assert_row_fits(panel.composition_top_toolbar)
        _assert_row_fits(panel.composition_hierarchy_toolbar)
        _assert_row_fits(panel.composition_state_toolbar)
        assert panel.composition_list.height() >= panel.composition_list.minimumHeight()
        for scale in (1.0, 1.25, 1.5):
            assert all(round(widget.geometry().right() * scale) <= round((row.width() - 1) * scale) for row in (panel.composition_top_toolbar, panel.composition_hierarchy_toolbar, panel.composition_state_toolbar) for widget in (row.layout().itemAt(index).widget() for index in range(row.layout().count())) if widget is not None)
    _close(window)
