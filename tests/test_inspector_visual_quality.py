"""Screen-space regression, without manually forcing descendant geometries."""
from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPalette, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from tools.inspector_visual_probe import make_panel, geometry_issues

APP = QApplication.instance() or QApplication([])


def settle():
    for _ in range(5):APP.processEvents()


@pytest.mark.parametrize("language", ["ko", "en"])
@pytest.mark.parametrize("width", [280, 320, 360])
@pytest.mark.parametrize("scale", [1, 1.25, 1.5])
@pytest.mark.parametrize("dark", [False, True])
def test_screen_space_vertical_geometry_transitions(tmp_path, language, width, scale, dark):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/malgun.ttf")
    p, project, a, b = make_panel(tmp_path, language, width, scale)
    try:
        if dark:
            palette = QPalette(); palette.setColor(QPalette.ColorRole.Window, QColor(35, 37, 40))
            palette.setColor(QPalette.ColorRole.Base, QColor(26, 28, 31))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(235, 235, 235))
            palette.setColor(QPalette.ColorRole.Text, QColor(235, 235, 235))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(235, 235, 235))
            palette.setColor(QPalette.ColorRole.Button, QColor(45, 47, 50))
            palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(170, 170, 170)); p.setPalette(palette)
            settle()
            assert p.trail_group.disclosure.palette().color(QPalette.ColorRole.ButtonText).lightness()>100
        for motion in ("linear", "helix"):
            settings = deepcopy(a.particle_settings); settings.motion.mode = motion
            p.set_settings(settings); p.workflow.sync(); settle()
            for enabled in (False, True):
                settings.trail.enabled = enabled; p.set_settings(settings); settle()
                for category in ("trail", "events", "rendering"):
                    p.workflow.jump(category); settle()
                assert not geometry_issues(p), geometry_issues(p)
                before = deepcopy(project.to_dict())
                p.trail_group.set_expanded(False); p.sub_group.set_expanded(False); settle()
                p.workflow.jump("trail"); p.workflow.jump("events"); settle()
                assert project.to_dict() == before
                assert not geometry_issues(p), geometry_issues(p)
        # Width/font refresh, explicit OFF-field reveal, and selection roundtrip.
        p.workflow.jump("motion", p.gravity_strength); settle()
        p.set_resource_layer(b, project); p.set_resource_layer(a, project); settle()
        p.resize(width + 24, 1000); settle(); p.resize(width, 1100); settle()
        font = p.font(); font.setPointSizeF(9 * scale); p.setFont(font); settle()
        assert not geometry_issues(p), geometry_issues(p)
        assert p.trail_group.disclosure.font().pointSizeF()==p.trail_group.font().pointSizeF()
        assert p.emission_mode.currentData() == "burst" and p.spawn_shape.currentData() == "point"
        assert p.emission_mode.currentText() != "burst" and p.spawn_shape.currentText() != "point"
        assert "None" not in p.workflow.selection.text()
        assert p.workflow.action_area.isAncestorOf(p.export)
    finally:p.close()


def test_source_native_title_first_field_and_commands_have_distinct_rows(tmp_path):
    p, *_ = make_panel(tmp_path, "ko", 320, 1.5)
    try:
        p.workflow.jump("source"); settle()
        assert not geometry_issues(p), geometry_issues(p)
        assert p.workflow.action_area.title()=="작업" and "내보내기" in p.workflow.action_help.text()
        assert any(editor is p.export for _, editor, _, _ in p.workflow.search_properties("Export"))
    finally:p.close()
