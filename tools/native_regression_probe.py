"""Isolated synthetic native fixture; no user project/settings are loaded."""
import os
import argparse
import json
from pathlib import Path
from copy import deepcopy

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--offscreen",action="store_true")
    parser.add_argument("--mode",choices=("lifetime","group"),default="lifetime")
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    os.environ["QT_QPA_PLATFORM"]="offscreen" if args.offscreen else "windows"
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from tools.inspector_visual_probe import make_panel
    from tests.test_native_regression_repair import point_geometry_issues
    app=QApplication.instance() or QApplication([])
    if args.mode=="group":
        from tests.test_native_regression_repair import rotation_project
        from app.services.settings_service import ShortcutSettingsService
        from app.ui.main_window import MainWindow
        from PySide6.QtCore import QSettings,Qt
        project,composition,*_=rotation_project(12,12)
        project.effect_resource_layers=[];project.repair_effect_hierarchy()
        win=MainWindow(ShortcutSettingsService(QSettings(str(args.output/"group.ini"),QSettings.Format.IniFormat)),project)
        layer=win.create_resource_layer_from_resource(composition.id)
        win.duplicate_resource_layer(layer.id)
        ids=win._effect_ui_root_ids();win.select_effect_layers_with_modifiers(ids[0]);win.select_effect_layers_with_modifiers(ids[1],Qt.KeyboardModifier.ControlModifier)
        win.setWindowTitle("Pixel Effect Maker - Group Regression QA");win.resize(1200,850)
        counter=[0]
        def group_capture():
            counter[0]+=1;win.dirty=False;win._non_undo_dirty=False
            win.grab().save(str(args.output/f"group_{counter[0]}.png"))
            state=dict(selected=list(win.effect_layer_selection.selected_ids),group_enabled=win.effect_library.group_composition_button.isEnabled(),ungroup_enabled=win.effect_library.ungroup_composition_button.isEnabled(),groups=[g.to_dict() for g in project.effect_layer_groups])
            (args.output/f"group_{counter[0]}.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
            print(json.dumps(state),flush=True)
            if args.offscreen:app.quit()
        for button in (win.effect_library.group_composition_button,win.effect_library.ungroup_composition_button):button.clicked.connect(lambda:QTimer.singleShot(150,group_capture))
        win.show();QTimer.singleShot(350,group_capture);app.exec();return
    p,project,a,b=make_panel(args.output,"ko",320,1.5)
    settings=deepcopy(a.particle_settings)
    settings.scale_over_lifetime.enabled=settings.color_over_lifetime.enabled=True
    p.set_settings(settings);p.workflow.jump("look")
    p.setWindowTitle("Pixel Effect Maker - Lifetime Regression QA")
    def capture():
        p.workflow.jump("look",p.scale_point_editor)
        for _ in range(5):app.processEvents()
        p.grab().save(str(args.output/"lifetime.png"))
        data={e.channel:dict(issues=point_geometry_issues(e),height=e.height(),minimum=e.minimumSizeHint().height(),hint=e.sizeHint().height(),hfw=e.heightForWidth(e.width())) for e in p._point_editors}
        (args.output/"geometry.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
        print(json.dumps(data),flush=True)
        if args.offscreen:app.quit()
    QTimer.singleShot(350,capture)
    app.exec()

if __name__=="__main__":main()
