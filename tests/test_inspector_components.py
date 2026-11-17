import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from copy import deepcopy
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QFont, QFontDatabase, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QWidget

from app.services.localization_service import LocalizationService
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox, FocusWheelComboBox
from app.ui.inspector_components import (InspectorSection, InspectorViewState,
    InspectorNumericRow, InspectorComboRow, InspectorWarning)
from app.ui.layout_metrics import inspector_color
from tests.test_particle_sub_emitter_ui import window
from tests.test_particle_scale_over_lifetime import _close

APP = QApplication.instance() or QApplication([])


@pytest.fixture
def scene(tmp_path):
    win, parent, target, other = window(tmp_path, "both")
    yield win, parent, target, other
    _close(win)


def snapshot(win):
    return (deepcopy(win.project.to_dict()), win.application_undo_stack.count(),
            win.dirty, win._non_undo_dirty, win._project_edit_revision)


def test_disclosure_is_not_feature_enable_or_document_state(scene):
    win, parent, target, _ = scene
    panel = win.particle_properties
    before = snapshot(win)
    advanced = parent.advanced_transform_enabled
    for section in (panel.trail_group, panel.sub_group):
        section.set_expanded(False)
        section.set_expanded(True)
        section.disclosure.click()
        assert not section.is_expanded()
    assert snapshot(win) == before
    assert parent.advanced_transform_enabled == advanced
    assert panel.birth_sub_enabled.isChecked() and panel.death_sub_enabled.isChecked()


def test_feature_switch_and_view_api_are_independent():
    section = InspectorSection("feature", InspectorViewState())
    feature = QCheckBox(section.body)
    feature.setChecked(True)
    section.set_expanded(False)
    assert feature.isChecked()
    feature.setChecked(False)
    assert not section.is_expanded()
    section.set_expanded(True)
    assert not feature.isChecked()
    section.close()


def test_collapse_does_not_commit_pending_numeric_text(scene):
    win, _, _, _ = scene
    panel = win.particle_properties
    win.show(); APP.processEvents()
    panel.trail_group.set_expanded(True)
    panel.ensureWidgetVisible(panel.trail_opacity)
    editor = panel.trail_opacity
    APP.processEvents()
    editor.setFocus(); APP.processEvents(); editor.lineEdit().selectAll()
    QTest.keyClicks(editor.lineEdit(), "0.123456")
    assert editor.lineEdit().text() == "0.123456"
    assert panel.trail_group._has_pending_numeric(), (APP.focusWidget(), editor.lineEdit().isModified(), editor.isVisible())
    before = snapshot(win)
    # A view API must not force focus-out/commit. Mouse navigation can first
    # trigger Qt's existing focus-out commit; that is the edit, not disclosure.
    panel.trail_group.disclosure.click(); APP.processEvents()
    assert snapshot(win) == before
    assert panel.trail_group.is_expanded()  # Pending text is not discarded either.
    assert "collaps" in panel.trail_group.disclosure.toolTip().lower() or "확정" in panel.trail_group.disclosure.toolTip()
    panel.name.setFocus(); APP.processEvents()  # Existing numeric focus-out commit.
    committed = snapshot(win)
    assert win.application_undo_stack.count() == 1, (editor.value(), editor.lineEdit().text(), panel.trail_status.text(), APP.focusWidget())
    QTest.mouseClick(panel.trail_group.disclosure, Qt.MouseButton.LeftButton); APP.processEvents()
    assert not panel.trail_group.is_expanded()
    assert snapshot(win) == committed


def test_selection_roundtrip_preserves_settings_and_per_layer_view_state(scene):
    win, parent, target, _ = scene
    panel = win.particle_properties
    before = snapshot(win)
    panel.sub_group.set_expanded(False)
    panel.trail_group.set_expanded(False)
    panel.set_resource_layer(target, win.project)
    assert not panel.sub_group.is_expanded()  # UX-2 defaults Events closed.
    panel.sub_group.set_expanded(False)
    panel.trail_group.set_expanded(True)
    panel.set_resource_layer(parent, win.project)
    assert not panel.sub_group.is_expanded() and not panel.trail_group.is_expanded()
    panel.set_resource_layer(target, win.project)
    assert not panel.sub_group.is_expanded() and panel.trail_group.is_expanded()
    assert panel.settings() == target.particle_settings
    assert snapshot(win) == before


def test_off_values_survive_and_details_disclose_without_mutating(scene):
    win, parent, _, _ = scene
    panel = win.particle_properties
    settings = deepcopy(parent.particle_settings)
    settings.trail.enabled = False
    settings.trail.duration_frames = 41
    settings.trail.sample_interval_frames = 5
    settings.trail.opacity = .3125
    settings.birth_sub_emitter.enabled = settings.death_sub_emitter.enabled = False
    panel.set_settings(settings)
    before = snapshot(win)
    for section in (panel.trail_group, panel.sub_group):
        section.set_expanded(False)
        section.set_expanded(True)
        assert section.summary.text() in {"Off", "꺼짐"}
    assert panel.settings() == settings
    assert panel.trail_form.rows[panel.trail_duration].isHidden()
    assert panel.sub_form.rows[panel.birth_sub_target].isHidden()
    assert snapshot(win) == before


@pytest.mark.parametrize("field,value", [("trail_opacity", .123456), ("death_sub_enabled", False)])
def test_pilot_accepted_edit_undo_one_summary_redo(scene, field, value):
    win, parent, _, _ = scene
    panel = win.particle_properties
    before = deepcopy(parent.particle_settings)
    control = getattr(panel, field)
    (control.setChecked if isinstance(value, bool) else control.setValue)(value)
    assert win.application_undo_stack.count() == 1
    after = deepcopy(parent.particle_settings)
    assert after != before and after.motion.tracks == before.motion.tracks
    if field == "trail_opacity":
        assert "0.123456" in panel.trail_group.summary.text()
    else:
        assert "Death" not in panel.sub_group.summary.text() and "사망" not in panel.sub_group.summary.text()
    win.application_undo_stack.undo()
    assert parent.particle_settings == before
    win.application_undo_stack.redo()
    assert parent.particle_settings == after


def test_rejected_edit_and_collapsed_warning_undo_zero(scene):
    win, parent, _, _ = scene
    panel = win.particle_properties
    settings = deepcopy(parent.particle_settings)
    settings.trail.enabled = True
    settings.trail.duration_frames = 17
    settings.trail.sample_interval_frames = 3
    parent.particle_settings = settings
    panel.set_settings(settings)
    before = snapshot(win)
    panel.trail_interval.setValue(17)
    assert snapshot(win) == before
    assert panel.trail_status.text()
    panel.trail_group.set_expanded(False)
    assert not panel.trail_group.badge.isHidden()
    assert panel.trail_group.badge.toolTip() == panel.trail_status.text()


def test_rejected_sub_target_warning_survives_collapse(scene):
    win, _, _, _ = scene
    panel = win.particle_properties
    before = snapshot(win)
    panel.birth_sub_target.addItem("Missing", "missing-id")
    panel.birth_sub_target.setCurrentIndex(panel.birth_sub_target.findData("missing-id"))
    assert snapshot(win) == before
    assert panel.sub_status.text()
    panel.sub_group.set_expanded(False)
    assert not panel.sub_group.badge.isHidden()
    assert panel.sub_group.badge.toolTip() == panel.sub_status.text()


def test_rows_wrap_existing_editors_without_replacing_commit_policy():
    numeric = ScrollSafeDoubleSpinBox()
    numeric.setRange(0, 1)
    row = InspectorNumericRow("Opacity", numeric, unit=" %", tooltip="Existing input")
    assert row.editor is numeric and not numeric.keyboardTracking()
    row.set_editor_enabled(False, "Feature is Off")
    assert row.message.text() and not numeric.isEnabled()
    row.set_editor_enabled(True)
    assert not row.message.text() and numeric.isEnabled()
    row.set_validation("Rejected")
    assert row.message.severity == "error"
    combo = FocusWheelComboBox()
    assert InspectorComboRow("Target", combo).editor is combo
    row.close()


def test_palette_tokens_no_hardcoded_data_swatch():
    palette = QPalette()
    assert inspector_color("focus", palette) == palette.color(QPalette.ColorRole.Highlight)
    assert inspector_color("disabled", palette) == palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
    for name in ("text_primary", "text_secondary", "text_muted", "state_info", "state_warning", "state_error", "state_danger", "border"):
        assert inspector_color(name, palette).isValid()


@pytest.mark.parametrize("language", ["ko", "en"])
@pytest.mark.parametrize("width", [280, 320, 360])
@pytest.mark.parametrize("factor", [1, 1.25, 1.5])
def test_pilot_layout_header_summary_badge_and_tab(tmp_path, language, width, factor):
    # Real glyph font, but synthetic/offscreen: not Windows DPI/native QA.
    font_file = Path("C:/Windows/Fonts/malgun.ttf")
    if font_file.exists():
        QFontDatabase.addApplicationFont(str(font_file))
    win, parent, target, _ = window(tmp_path, "both")
    try:
        panel = win.particle_properties
        locale = LocalizationService(QSettings(str(tmp_path / "locale.ini"), QSettings.Format.IniFormat), language)
        locale.set_language(language)
        target.name = "아주 긴 대상 이름으로 헤더 요약 줄바꿈 검사" if language == "ko" else "Long target name for wrapping header summary"
        panel.retranslate_ui(locale)
        panel.set_resource_layer(parent, win.project)
        assert panel.trail_group.title() == ("잔상 궤적" if language == "ko" else "Trail")
        assert panel.sub_group.title() == ("하위 방출기" if language == "ko" else "Sub-emitter")
        for section, form in ((panel.trail_group, panel.trail_form), (panel.sub_group, panel.sub_form)):
            section.setParent(None)
            section.setFont(QFont("Malgun Gothic", 9))
            font = section.font(); font.setPointSizeF(9 * factor); section.setFont(font)
            section.set_warning("확인 필요" if language == "ko" else "Check configuration", "warning")
            section.setFixedWidth(width)
            section.set_expanded(True)
            section.show(); APP.processEvents(); section.adjustSize(); APP.processEvents()
            for widget in (section.disclosure, section.summary, section.badge):
                rect = widget.rect().translated(widget.mapTo(section, QPoint()))
                assert rect.left() >= 0 and rect.right() < section.width()
            assert not section.disclosure.geometry().intersects(section.badge.geometry())
            assert section.summary.height() >= section.summary.heightForWidth(section.summary.width())
            for editor, row in form.rows.items():
                if row.isVisibleTo(section):
                    rect = editor.rect().translated(editor.mapTo(section, QPoint()))
                    assert rect.left() >= 0 and rect.right() < section.width()
                    assert editor.focusPolicy() != Qt.FocusPolicy.NoFocus
            section.disclosure.setFocus(); APP.processEvents()
            assert APP.focusWidget() is section.disclosure
            QTest.keyClick(section.disclosure, Qt.Key.Key_Space); APP.processEvents()
            assert not section.is_expanded() and not section.badge.isHidden()
            QTest.keyClick(section.disclosure, Qt.Key.Key_Space); APP.processEvents()
            QTest.keyClick(section.disclosure, Qt.Key.Key_Tab); APP.processEvents()
            assert section.body.isAncestorOf(APP.focusWidget())
            section.close()
    finally:
        _close(win)
