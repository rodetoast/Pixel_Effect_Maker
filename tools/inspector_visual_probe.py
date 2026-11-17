"""Synthetic Inspector screen-coordinate audit; no user files or render changes."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QPoint, QRect, QSettings
from PySide6.QtGui import QFont, QFontDatabase, QPalette, QColor
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QGroupBox, QStyle, QStyleOptionGroupBox


def screen_rect(widget):
    return QRect(widget.mapToGlobal(QPoint()), widget.size())


def geometry_issues(panel):
    """Check visible layout, including scrolled-off siblings in global coordinates.

    Native widget implementation children (spin's line edit etc.) intentionally
    overlap; compare logical layout siblings, not every descendant pair.
    """
    issues = []
    sections = list(panel.workflow.sections.values())
    for first, second in zip(sections, sections[1:]):
        if screen_rect(first).intersects(screen_rect(second)):
            issues.append("section:" + first.section_id + "/" + second.section_id)
    for section in sections:
        for first, second in ((section.disclosure, section.summary), (section.summary, section.body)):
            if first.isVisibleTo(panel) and second.isVisibleTo(panel) and screen_rect(first).intersects(screen_rect(second)):
                issues.append("header/body:" + section.section_id)
    for form in (panel.trail_form, panel.sub_form):
        visible = [form.itemAt(i).widget() for i in range(form.count()) if form.itemAt(i).widget().isVisibleTo(panel)]
        for first, second in zip(visible, visible[1:]):
            if screen_rect(first).intersects(screen_rect(second)):
                issues.append("row-sibling:" + form.parentWidget().parentWidget().section_id)
        for row in form.rows.values():
            if not row.isVisibleTo(panel):continue
            widgets = [widget for widget in (row.label, row.editor, row.message) if widget.isVisibleTo(panel)]
            for first, second in zip(widgets, widgets[1:]):
                if screen_rect(first).intersects(screen_rect(second)):
                    issues.append("label/editor:" + row.label.text())
            for widget in widgets:
                if not screen_rect(row).contains(screen_rect(widget)):
                    issues.append("row-containment:" + row.label.text())
    for group in panel.widget().findChildren(QGroupBox):
        if not group.isVisibleTo(panel):continue
        option = QStyleOptionGroupBox(); group.initStyleOption(option)
        if not option.text:continue  # Custom section headers aren't native titles.
        title = group.style().subControlRect(QStyle.ComplexControl.CC_GroupBox, option, QStyle.SubControl.SC_GroupBoxLabel, group)
        title.translate(group.mapToGlobal(QPoint()))
        for label in group.findChildren(QLabel):
            if label.isVisibleTo(group) and screen_rect(label).intersects(title):
                issues.append("native-title:" + group.title() + "/" + label.text())
    for label in panel.widget().findChildren(QLabel):
        if label.isVisibleTo(panel) and label.wordWrap() and label.text():
            if label.height() < label.heightForWidth(label.width()):
                issues.append("text-height:" + label.objectName() + "/" + label.text()[:30])
    return issues


def make_panel(output, language="ko", width=320, scale=1.5):
    from app.models.project import Project
    from app.models.resource_composition import ResourceComposition
    from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
    from app.services.localization_service import LocalizationService
    from app.ui.particle_properties_panel import ParticlePropertiesPanel
    project = Project.create_default(); comp = ResourceComposition("Synthetic Spark")
    project.resource_compositions.append(comp)
    layer = EffectResourceLayer("Synthetic Particle", comp.id, placement_mode=PLACEMENT_PARTICLE)
    target = EffectResourceLayer("Impact Spark", comp.id, placement_mode=PLACEMENT_PARTICLE)
    project.effect_resource_layers.extend((layer, target)); project.repair_effect_hierarchy()
    layer.particle_settings.trail.enabled = True
    layer.particle_settings.birth_sub_emitter.enabled = layer.particle_settings.death_sub_emitter.enabled = True
    layer.particle_settings.birth_sub_emitter.target_layer_id = layer.particle_settings.death_sub_emitter.target_layer_id = target.id
    locale = LocalizationService(QSettings(str(output / "isolated.ini"), QSettings.Format.IniFormat), language)
    locale.set_language(language)
    panel = ParticlePropertiesPanel(); panel.retranslate_ui(locale); panel.set_resource_layer(layer, project)
    font = QFont("Malgun Gothic", 9); font.setPointSizeF(9 * scale); panel.setFont(font)
    panel.resize(width, 1100); panel.show()
    for key, section in panel.workflow.sections.items():section.set_expanded(key in {"trail", "events", "rendering"})
    for _ in range(4):QApplication.processEvents()
    panel.verticalScrollBar().setValue(panel.trail_group.mapTo(panel.widget(), QPoint()).y())
    QApplication.processEvents()
    return panel, project, layer, target


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:parser.error("Use an external output directory")
    output.mkdir(parents=True, exist_ok=False)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/malgun.ttf")
    app.setFont(QFont("Malgun Gothic", 9))
    result = []
    for language in ("ko", "en"):
        panel, *_ = make_panel(output, language)
        panel.grab().save(str(output / (language + "_trail_events.png")))
        issues = geometry_issues(panel)
        result.append(dict(language=language, issues=issues))
        panel.close()
    panel, project, layer, _ = make_panel(output)
    palette=QPalette()
    for role,color in ((QPalette.ColorRole.Window,"#232528"),(QPalette.ColorRole.Base,"#1a1c1f"),
        (QPalette.ColorRole.AlternateBase,"#2d2f32"),(QPalette.ColorRole.Button,"#2d2f32"),
        (QPalette.ColorRole.WindowText,"#ebebeb"),(QPalette.ColorRole.Text,"#ebebeb"),
        (QPalette.ColorRole.ButtonText,"#ebebeb"),(QPalette.ColorRole.PlaceholderText,"#aaaaaa")):
        palette.setColor(role,QColor(color))
    panel.setPalette(palette)
    for _ in range(5):app.processEvents()
    panel.grab().save(str(output / "ko_dark_trail_events.png"))
    result.append(dict(language="ko",palette="synthetic dark",issues=geometry_issues(panel)))
    panel.close()
    source_panel,*_=make_panel(output)
    source_panel.workflow.jump("source")
    for _ in range(5):app.processEvents()
    source_panel.verticalScrollBar().setValue(0);app.processEvents()
    source_panel.grab().save(str(output / "ko_source_actions.png"));source_panel.close()
    from app.ui.canvas_widget import CanvasWidget
    from app.models.project import Project
    from app.models.effect_resource_layer import EffectLayerTransform3D
    import numpy as np
    canvas_project=Project.create_default();canvas_project.frames=canvas_project.frames[:1]
    pixels=canvas_project.frames[0].layer_pixels[canvas_project.layers[0].id]
    yy,xx=np.indices(pixels.shape[:2]);cx=canvas_project.width//2;cy=canvas_project.height//2
    ring=((xx-cx)**2+(yy-cy)**2>=70)&((xx-cx)**2+(yy-cy)**2<=100)
    pixels[ring]=(255,210,60,255);pixels[cy:cy+2,cx:cx+2]=(20,20,20,255)
    canvas=CanvasWidget();canvas.resize(420,420);canvas.set_project(canvas_project);canvas.zoom=6
    canvas.set_resource_layer_transform("synthetic",EffectLayerTransform3D(),mode="scale");canvas.show();app.processEvents()
    canvas.grab().save(str(output / "gizmo_visible.png"))
    canvas.set_effect_guides_visible(False);app.processEvents();canvas.grab().save(str(output / "gizmo_hidden.png"));canvas.close()
    from app.ui.main_window import MainWindow
    from app.services.settings_service import ShortcutSettingsService
    window=MainWindow(ShortcutSettingsService(QSettings(str(output / "window.ini"),QSettings.Format.IniFormat)),project)
    window.resize(1280,900);window.show();window.select_resource_layer(layer.id);app.processEvents()
    window.effect_library.composition_group.grab().save(str(output / "layer_controls.png"))
    for timer in (window.resource_transform_render_timer,window.resource_transform_finalize_timer,
                  window.particle_motion_render_timer,window.particle_motion_finalize_timer):timer.stop()
    window.dirty=window._non_undo_dirty=False;window.close();app.processEvents()
    (output / "geometry.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":main()
