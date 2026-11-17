"""UX-2 IA contracts: existing editor identity, view-only navigation and bounds."""
from copy import deepcopy

import pytest
from PySide6.QtCore import QPoint, Qt, QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.services.localization_service import LocalizationService
from app.ui.particle_inspector_workflow import CATEGORIES
from tests.test_inspector_components import scene, snapshot

APP = QApplication.instance() or QApplication([])


def test_exact_category_order_all_live_settings_and_identity(scene):
    win, parent, _, _ = scene; p = win.particle_properties; w = p.workflow
    assert tuple(w.sections) == tuple(CATEGORIES)
    assert [p.layout.itemAt(i).widget() for i in range(8)] == list(w.sections.values())
    assert p.settings() == parent.particle_settings
    editors = [editor for _, editor, _, _ in w.registry]
    assert len(editors) == len(set(editors))
    for name, category in {"clip": "source", "clip_speed_min": "source", "random_start_frame": "source",
        "count_min": "emit", "lifetime_min": "emit", "start_delay_max": "emit", "speed_min": "emit",
        "motion_mode": "motion", "gravity_strength": "motion", "angular_velocity_max": "motion",
        "scale_min": "look", "rotation_max": "look", "scale_point_editor": "look",
        "trail_opacity": "trail", "death_sub_target": "events", "blend_mode": "rendering", "parent_layer": "transform"}.items():
        editor = getattr(p, name)
        assert editors.count(editor) == 1 and w.sections[category].isAncestorOf(editor)
    # Every active original property registry entry is indexed, not cloned.
    assert all(editor in editors for _, _, _, records in p._group_records for _, editor in records)


def test_all_disclosures_jumps_search_are_document_noops(scene):
    win, parent, _, _ = scene; p = win.particle_properties; w = p.workflow
    before = snapshot(win)
    for category, section in w.sections.items():
        section.set_expanded(False)
        assert w.jump(category)
        assert section.is_expanded()
        section.set_expanded(False)
    assert w.search_properties("Count")
    assert any(editor is p.gravity_strength for _, editor, _, _ in w.search_properties("Gravity Strength"))
    w.search.setText("Gravity Strength"); w._activate_result(0)
    assert w.sections["motion"].is_expanded()
    assert snapshot(win) == before
    assert parent.advanced_transform_enabled == p.transform_panel.isChecked()


def test_session_roundtrip_keeps_independent_categories_and_scroll(scene):
    win, a, b, _ = scene; p = win.particle_properties; w = p.workflow
    w.sections["emit"].set_expanded(False); w.jump("motion")
    p.set_resource_layer(b, win.project)
    assert w.sections["emit"].is_expanded() and not w.sections["motion"].is_expanded()
    w.jump("look")
    p.set_resource_layer(a, win.project)
    assert not w.sections["emit"].is_expanded() and w.sections["motion"].is_expanded()
    assert not w.sections["look"].is_expanded()
    assert p.settings() == a.particle_settings


def test_conditional_detail_hiding_preserves_values_and_search_can_reveal(scene):
    win, _, _, _ = scene; p = win.particle_properties; w = p.workflow
    settings = deepcopy(p.settings())
    settings.spawn_shape = "point"; settings.radius = 17
    settings.gravity_enabled = settings.drag_enabled = settings.noise_enabled = False
    settings.gravity_strength = .75
    settings.scale_over_lifetime.enabled = settings.color_over_lifetime.enabled = False
    p.set_settings(settings); w.sync()
    assert p.settings() == settings
    assert not p.gravity_strength.isVisibleTo(w.sections["motion"].body)
    assert not p.radius.isVisibleTo(w.sections["emit"].body)
    assert p.scale_point_editor.isHidden() and p.color_point_editor.isHidden()
    before = snapshot(win)
    w.jump("motion", p.gravity_strength)
    assert p.gravity_strength.isVisibleTo(p) and not p.gravity_strength.isEnabled()
    assert p.settings() == settings and snapshot(win) == before


def test_pending_numeric_blocks_view_jump_without_commit(scene):
    win, _, _, _ = scene; p = win.particle_properties; w = p.workflow
    win.show(); w.jump("emit", p.count_min); APP.processEvents()
    p.count_min.setFocus(); p.count_min.lineEdit().selectAll()
    QTest.keyClicks(p.count_min.lineEdit(), "2")
    assert w.pending_numeric()
    before = snapshot(win)
    assert not w.jump("rendering")
    w.sections["emit"].set_expanded(False)
    assert w.sections["emit"].is_expanded() and p.count_min.lineEdit().text() == "2"
    assert snapshot(win) == before


def test_important_warning_and_surface_state_discoverable_closed(scene):
    win, parent, _, _ = scene; p = win.particle_properties; w = p.workflow
    p.sub_status.set_message("Missing target", "error")
    w.sections["events"].set_expanded(False)
    assert not w.sections["events"].badge.isHidden()
    assert not w.warnings.isHidden() and w.warnings.findData("events") > 0
    parent.surface_transform.rotation_y = 12
    p.set_resource_layer(parent, win.project)
    assert "Nonidentity" in w.sections["transform"].summary.text()
    assert not w.surface_section.is_expanded()


@pytest.mark.parametrize("language", ["en", "ko"])
@pytest.mark.parametrize("width", [280, 320, 360])
@pytest.mark.parametrize("scale", [1, 1.25, 1.5])
def test_navigation_pinned_and_category_geometry(scene, tmp_path, language, width, scale):
    win, _, _, _ = scene; p = win.particle_properties; w = p.workflow
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/malgun.ttf")
    locale = LocalizationService(QSettings(str(tmp_path / "ux2.ini"), QSettings.Format.IniFormat), language)
    locale.set_language(language); p.retranslate_ui(locale)
    p.setFont(QFont("Malgun Gothic", 9)); font = p.font(); font.setPointSizeF(9 * scale); p.setFont(font)
    p.setParent(None); p.resize(width, 700); p.show(); APP.processEvents(); w.sync(); APP.processEvents()
    before = w.navigation.pos()
    for category, section in w.sections.items():
        w.jump(category); APP.processEvents()
        section.set_warning("Layout warning", "warning")
        APP.processEvents(); APP.processEvents()
        assert section.width() <= p.viewport().width()
        assert section.height() >= section.minimumSizeHint().height()
        assert section.body.height() >= section.body.minimumSizeHint().height()
        assert section.summary.height() >= section.summary.heightForWidth(section.summary.width())
        if section.badge.isVisibleTo(p):
            assert not section.disclosure.geometry().intersects(section.badge.geometry())
        for widget in (w.selection, w.jump_combo, w.search):
            rect = widget.rect().translated(widget.mapTo(w.navigation, QPoint()))
            assert rect.left() >= 0 and rect.right() < w.navigation.width()
        assert p.viewport().geometry().top() >= w.navigation.height()
    p.verticalScrollBar().setValue(p.verticalScrollBar().maximum()); APP.processEvents()
    assert w.navigation.pos() == before
    assert w.search_properties("Count")
    p.close()
