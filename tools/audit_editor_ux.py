"""Read-only, synthetic offscreen UX inventory; never load a user's project.

Run from the repository with the test Python: python tools/audit_editor_ux.py
--output C:/Dev/pem_editor_ux_20261002. Output must be a new directory.
Counts describe logical controls, not Qt's private children or mouse clicks.
Font scaling is not Windows DPI scaling; geometry flags need visual review.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, QSettings, qVersion
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (QApplication, QAbstractButton, QAbstractSpinBox,
    QComboBox, QGroupBox, QLineEdit, QAbstractItemView, QScrollArea, QWidget,
    QKeySequenceEdit, QSlider)
from app.models.project import Project, FORMAT_VERSION
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.resource_composition import ResourceComposition, CompositionLayer
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.ui.new_project_dialog import NewProjectDialog
from app.ui.startup_dialog import StartupDialog
from app.ui.project_settings_dialog import ProjectSettingsDialog
from app.ui.interface_settings_dialog import InterfaceSettingsDialog
from app.ui.external_tools_dialog import ExternalToolsDialog
from app.ui.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
from app.ui.preview_build_notice_dialog import PreviewBuildNoticeDialog
from app.ui.resource_editor_v2.new_resource_dialog import NewResourceDialog
from app.ui.resource_editor_v2.composition_inspector import PropertySearchDialog


def controls(panel):
    """One spin/combo/list/table is one control; exclude implementation children."""
    result = []
    for widget in panel.findChildren(QWidget):
        if not isinstance(widget, (QAbstractButton, QAbstractSpinBox, QComboBox,
                                   QLineEdit, QAbstractItemView, QKeySequenceEdit, QSlider)):
            continue
        parent = widget.parentWidget()
        internal = False
        while parent is not None and parent is not panel:
            if isinstance(parent, (QAbstractSpinBox, QComboBox, QAbstractItemView, QKeySequenceEdit)):
                internal = True
                break
            parent = parent.parentWidget()
        if not internal:
            result.append(widget)
    return result


def size(value):
    return [value.width(), value.height()]


def metrics(panel):
    cs = controls(panel)
    visible = [w for w in cs if w.isVisibleTo(panel)]
    body = panel.widget() if isinstance(panel, QScrollArea) else panel
    viewport = panel.viewport() if isinstance(panel, QScrollArea) else panel
    in_view = [w for w in visible if viewport.rect().intersects(
        w.rect().translated(w.mapTo(viewport, QPoint(0, 0))))]
    groups = [g for g in panel.findChildren(QGroupBox) if g.isVisibleTo(panel)]
    sections = []
    for group in groups:
        # Direct ownership by nearest group avoids nested section double counts.
        own = []
        for control in visible:
            ancestor = control.parentWidget()
            while ancestor is not None and not isinstance(ancestor, QGroupBox):
                ancestor = ancestor.parentWidget()
            if ancestor is group:
                own.append(control)
        sections.append({"title": group.title(), "y": group.mapTo(body, QPoint()).y(),
                         "controls": len(own), "enabled": sum(w.isEnabled() for w in own),
                         "checkable_not_necessarily_collapsible": group.isCheckable()})
    overflow = []
    for control in visible:
        # UX-2 has a fixed navigation sibling outside the scrolling body.
        owner = body if body.isAncestorOf(control) else panel
        rect = control.rect().translated(control.mapTo(owner, QPoint()))
        if rect.left() < 0 or rect.right() >= QWidget.width(owner):
            overflow.append(control.objectName() or type(control).__name__)
    scrolls = [panel] if isinstance(panel, QScrollArea) else panel.findChildren(QScrollArea)
    return {"class": type(panel).__name__, "size": size(panel.size()),
            "size_hint": size(panel.sizeHint()), "minimum_size": size(panel.minimumSize()),
            "minimum_size_hint": size(panel.minimumSizeHint()), "content_height": QWidget.height(body),
            "constructed_controls": len(cs), "layout_visible_controls": len(visible),
            "viewport_intersecting_controls": len(in_view),
            "enabled_visible_controls": sum(w.isEnabled() for w in visible),
            "visible_groups": len(groups), "sections": sorted(sections, key=lambda s: s["y"]),
            "horizontal_bounds_flags": overflow,
            "scrolls": [{"vmax": s.verticalScrollBar().maximum(),
                         "hmax": s.horizontalScrollBar().maximum(),
                         "content_height": s.widget().height() if s.widget() else None}
                        for s in scrolls]}


def source_inventory():
    """Allocation sites, NOT runtime counts (loops/dynamic menus are recorded)."""
    result = []
    names = {"QPushButton", "QToolButton", "QCheckBox", "QComboBox", "QLineEdit",
             "QSpinBox", "QDoubleSpinBox", "QListWidget", "QTableWidget",
             "ScrollSafeSpinBox", "ScrollSafeDoubleSpinBox", "FocusWheelComboBox"}
    for path in sorted((ROOT / "app/ui").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            sites, menus = [], []
            for node in ast.walk(cls):
                if isinstance(node, ast.Call):
                    name = node.func.id if isinstance(node.func, ast.Name) else ""
                    if name in names:
                        sites.append({"type": name, "line": node.lineno})
                    if isinstance(node.func, ast.Attribute) and node.func.attr in {"addAction", "addActions", "addMenu"}:
                        menus.append({"line": node.lineno, "source": ast.unparse(node)})
            if sites or menus or "Dialog" in cls.name:
                result.append({"file": str(path.relative_to(ROOT)), "class": cls.name,
                               "control_allocation_sites_not_runtime_count": len(sites),
                               "sites": sites, "menu_sites": menus})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font-file", type=Path, default=Path("C:/Windows/Fonts/malgun.ttf"))
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Diagnostic output must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    font_loaded = False
    if args.font_file.is_file():
        font_id = QFontDatabase.addApplicationFont(str(args.font_file))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 9))
            font_loaded = True
    settings = QSettings(str(output / "isolated.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", "en")
    project = Project.create_default()
    comp = ResourceComposition("Synthetic resource", width=16, height=16, frame_count=4)
    project.resource_compositions.append(comp)
    layer = EffectResourceLayer("Synthetic particle", comp.id, placement_mode=PLACEMENT_PARTICLE, end_frame=3)
    project.effect_resource_layers.append(layer)
    target = EffectResourceLayer("Synthetic event target", comp.id, placement_mode=PLACEMENT_PARTICLE, end_frame=3)
    project.effect_resource_layers.append(target)
    window = MainWindow(ShortcutSettingsService(settings), project)
    window.localization.set_language("en")
    window.resize(1280, 800)
    window.show()
    window.select_resource_layer(layer.id)
    app.processEvents()
    panels = {}
    for name, panel in [("effect_library", window.effect_library), ("particle", window.particle_properties),
                        ("effect_timeline", window.timeline), ("effect_canvas", window.canvas)]:
        panels[name] = metrics(panel)
    layouts = []
    for width, height in [(900, 600), (1024, 768), (1280, 800), (1600, 900)]:
        window.resize(width, height)
        app.processEvents()
        layouts.append({"workspace": "effect", "requested": [width, height],
                        "actual": size(window.size()), "splitter": window.editor_splitter.sizes(),
                        "timeline": size(window.timeline.size()), "canvas": size(window.canvas.size())})
    window.set_workspace("resource")
    window.resource_editor.controller.select_composition(comp.id)
    window.resize(1280, 800)
    app.processEvents()
    editor = window.resource_editor
    for name, panel in [("resource_browser", editor.browser), ("resource_metadata", editor.composition_inspector),
                        ("resource_timeline", editor.composition_timeline), ("resource_canvas", editor.composition_canvas)]:
        panels[name] = metrics(panel)
    # Measure the unmodified shell hierarchy before detaching isolated inspectors.
    for width, height in [(900, 600), (1024, 768), (1280, 800), (1600, 900)]:
        window.resize(width, height)
        app.processEvents()
        layouts.append({"workspace": "resource", "requested": [width, height],
                        "actual": size(window.size()), "splitter": editor.splitter.sizes(),
                        "vertical_splitter": editor.vertical_splitter.sizes()})
    # Detached, isolated states: do not issue editing commands or render real files.
    for name, panel in [("resource_layer_empty_properties", editor.layer_inspector),
                        ("asset_inspector_no_asset", editor.asset_inspector),
                        ("group_inspector_no_group", editor.group_inspector),
                        ("single_layer", window.composition_layer_properties),
                        ("legacy_generator_no_selection", window.effect_properties)]:
        panel.setParent(None)
        panel.resize(320, 700)
        panel.show()
        app.processEvents()
        panels[name] = metrics(panel)
        panel.hide()
    synthetic_layer = CompositionLayer("Synthetic image layer", "source_asset", "no-disk-asset", 0, 3)
    for property_id in ("position", "scale", "rotation", "opacity"):
        synthetic_layer.add_property(property_id)
    editor.layer_inspector.set_layer(synthetic_layer, None, 0)
    editor.layer_inspector.show()
    app.processEvents()
    panels["resource_layer_four_properties"] = metrics(editor.layer_inspector)
    editor.layer_inspector.hide()
    dialogs = {}
    locale = window.localization
    for name, dialog in [
        ("new_project", NewProjectDialog(localization=locale)),
        ("startup", StartupDialog(localization=locale)),
        ("project_settings", ProjectSettingsDialog(project, None, lambda values: False, localization=locale)),
        ("interface_settings", InterfaceSettingsDialog(settings, locale)),
        ("external_tools", ExternalToolsDialog(settings, locale)),
        ("shortcuts", KeyboardShortcutsDialog(window.shortcuts, localization=locale)),
        ("preview_notice", PreviewBuildNoticeDialog(locale, settings)),
        ("overview", PreviewBuildNoticeDialog(locale, settings, manual_open=True)),
        ("new_resource", NewResourceDialog(None, locale)),
        ("property_search", PropertySearchDialog({}, locale)),
    ]:
        dialog.show()
        app.processEvents()
        dialogs[name] = metrics(dialog)
        dialog.hide()
        dialog.deleteLater()
    app.processEvents()
    matrix = []
    for language in ("en", "ko"):
        locale = LocalizationService(settings, language)
        locale.set_language(language)
        for mode in ("linear", "helix"):
            # Compare a default OFF linear state with a populated ON helix state.
            active = mode == "helix"
            ps = layer.particle_settings
            ps.gravity_enabled = ps.drag_enabled = ps.noise_enabled = active
            ps.scale_over_lifetime.enabled = ps.color_over_lifetime.enabled = active
            ps.trail.enabled = active
            ps.birth_sub_emitter.enabled = ps.death_sub_emitter.enabled = active
            ps.birth_sub_emitter.target_layer_id = ps.death_sub_emitter.target_layer_id = target.id if active else None
            for scale in (1, 1.25, 1.5):
                for width in (280, 320, 360):
                    panel = ParticlePropertiesPanel()
                    panel.retranslate_ui(locale)
                    layer.particle_settings.motion.mode = mode
                    panel.set_resource_layer(layer, project)
                    font = QFont(app.font())
                    font.setPointSizeF(font.pointSizeF() * scale)
                    panel.setFont(font)
                    panel.resize(width, 700)
                    panel.show()
                    app.processEvents()
                    panel.widget().layout().activate()
                    app.processEvents()
                    result = metrics(panel)
                    result.update(language=language, motion=mode, optional_features_enabled=active,
                                  font_scale=scale, requested_width=width)
                    matrix.append(result)
                    if language == "ko" and mode == "linear" and width == 320:
                        panel.grab().save(str(output / f"particle_ko_linear_320_font_{scale}.png"))
                    panel.close()
                    panel.deleteLater()
                    app.processEvents()
    menus = [{"title": action.text(), "actions": [a.text() for a in action.menu().actions() if not a.isSeparator()]}
             for action in window.menuBar().actions() if action.menu()]
    result = {"boundary": "Synthetic offscreen, not Windows native/manual/DPI QA. No click counts or quality score.",
              "qt": qVersion(), "format": FORMAT_VERSION, "font": app.font().toString(),
              "font_file_loaded": font_loaded, "font_supports_hangul": QFontMetrics(app.font()).inFontUcs4(ord("가")),
              "control_definition": "logical interactive widgets; hidden adapters excluded from visible count; groups separately; item count not control count",
              "panels": panels, "dialogs": dialogs, "main_layouts": layouts, "particle_matrix": matrix,
              "menus": menus, "source_inventory": source_inventory()}
    (output / "inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    window.resource_transform_render_timer.stop()
    window.resource_transform_finalize_timer.stop()
    window.particle_motion_render_timer.stop()
    window.particle_motion_finalize_timer.stop()
    window.dirty = False
    window._non_undo_dirty = False
    window.close()
    app.processEvents()
    print(json.dumps({"output": str(output), "matrix_rows": len(matrix), "panels": len(panels)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
