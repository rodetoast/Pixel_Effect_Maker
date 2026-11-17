"""Synthetic UX-2 evidence; writes only a fresh output directory outside repo."""
import argparse
import json
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from app.models.project import Project
from app.models.resource_composition import ResourceComposition
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.layer_group import LayerGroup
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.ui.main_window import MainWindow
from tools.audit_editor_ux import metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Output must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/malgun.ttf")
    app.setFont(QFont("Malgun Gothic", 9))
    settings = QSettings(str(output / "isolated.ini"), QSettings.Format.IniFormat)
    project = Project.create_default()
    comp = ResourceComposition("Synthetic Spark", width=16, height=16, frame_count=4)
    project.resource_compositions.append(comp)
    layer = EffectResourceLayer("Synthetic particle", comp.id, placement_mode=PLACEMENT_PARTICLE)
    target = EffectResourceLayer("Synthetic target", comp.id, placement_mode=PLACEMENT_PARTICLE)
    single = EffectResourceLayer("Synthetic single", comp.id)
    group = LayerGroup("Synthetic group")
    project.effect_resource_layers.extend([layer, target, single])
    project.effect_layer_groups.append(group); project.repair_effect_hierarchy()
    rows = []
    for language in ("en", "ko"):
        locale = LocalizationService(settings, language); locale.set_language(language)
        for mode in ("linear", "helix"):
            ps = layer.particle_settings; active = mode == "helix"
            ps.motion.mode = mode
            ps.gravity_enabled = ps.drag_enabled = ps.noise_enabled = active
            ps.scale_over_lifetime.enabled = ps.color_over_lifetime.enabled = active
            ps.trail.enabled = active
            for event in (ps.birth_sub_emitter, ps.death_sub_emitter):
                event.enabled = active; event.target_layer_id = target.id if active else None
            for scale in (1, 1.25, 1.5):
                for width in (280, 320, 360):
                    p = ParticlePropertiesPanel(); p.retranslate_ui(locale); p.set_resource_layer(layer, project)
                    font = QFont("Malgun Gothic", 9); font.setPointSizeF(9 * scale)
                    p.setFont(font); p.resize(width, 700); p.show()
                    app.processEvents(); p.widget().layout().activate(); app.processEvents()
                    initial = metrics(p); heights = {}; jumps = []
                    initial_nav_height = p.workflow.navigation.height()
                    if language == "ko" and width == 320 and scale in (1, 1.5):
                        p.grab().save(str(output / f"initial_{mode}_{scale}.png"))
                    for section in p.workflow.sections.values():section.set_expanded(False)
                    for category, section in p.workflow.sections.items():
                        samples = []
                        for _ in range(3):
                            section.set_expanded(False); app.processEvents(); start = perf_counter()
                            p.workflow.jump(category)
                            for _ in range(3):
                                app.processEvents(); p.widget().layout().activate()
                            samples.append((perf_counter() - start) * 1000)
                        heights[category] = section.height()
                        jumps.extend(samples); section.set_expanded(False)
                    refresh = []
                    for _ in range(3):
                        start = perf_counter(); p.set_resource_layer(target, project); p.set_resource_layer(layer, project); app.processEvents()
                        refresh.append((perf_counter() - start) * 1000)
                    rows.append(dict(language=language, mode=mode, scale=scale, width=width,
                        initial=initial, navigation_height=initial_nav_height, expanded_category_heights=heights,
                        jump_median_ms=median(jumps), selection_roundtrip_median_ms=median(refresh)))
                    p.close(); p.deleteLater(); app.processEvents()
    window = MainWindow(ShortcutSettingsService(settings), project); window.show()
    shell = []
    for width, height in ((1024, 768), (1280, 800), (1600, 900)):
        window.resize(width, height)
        for kind, item in (("group", group), ("single", single), ("particle", layer)):
            window.select_resource_layer(item.id); app.processEvents()
            shell.append(dict(requested_width=width, actual_width=window.width(), selection=kind,
                inspector=type(window.properties_stack.currentWidget()).__name__))
    result = dict(boundary="Synthetic offscreen; not native Windows manual, DPI or task click timing.",
        matrix=rows, main_window_selections=shell)
    (output / "workflow.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for timer in (window.resource_transform_render_timer, window.resource_transform_finalize_timer,
                  window.particle_motion_render_timer, window.particle_motion_finalize_timer):timer.stop()
    window.dirty = window._non_undo_dirty = False; window.close(); app.processEvents()
    print(json.dumps(dict(output=str(output), matrix=len(rows), shell=len(shell))))


if __name__ == "__main__":
    main()
