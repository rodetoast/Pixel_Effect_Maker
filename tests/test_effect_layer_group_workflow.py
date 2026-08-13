import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow

APP=QApplication.instance() or QApplication([])


def _window(tmp_path):
    project=Project.create_default(width=4,height=4,frame_count=2)
    for index in range(3):
        pixels=np.zeros((1,1,4),dtype=np.uint8);pixels[0,0,3]=255;asset=SourceAsset(str(index),pixels);project.source_assets.append(asset);project.resource_compositions.append(ResourceComposition(str(index),4,4,12,2,layers=[CompositionLayer(str(index),"source_asset",asset.id,0,1)]))
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"effect-group.ini"),QSettings.Format.IniFormat)),initial_project=project)
    for composition in project.resource_compositions:window.create_resource_layer_from_resource(composition.id)
    window.application_undo_stack.clear();return window


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window.close()


def test_effect_group_has_no_generated_layer_and_roundtrips(tmp_path):
    window=_window(tmp_path);before=len(window.project.layers);ui=window._effect_ui_root_ids();window.select_effect_layers_with_modifiers(ui[0]);window.select_effect_layers_with_modifiers(ui[1],Qt.KeyboardModifier.ShiftModifier)
    group=window.create_effect_group_selected();assert group and len(window.project.layers)==before and all(item.id!=group.id for item in window.project.layers)
    loaded=Project.from_dict(window.project.to_dict());assert loaded.effect_group_by_id(group.id).children==group.children
    _close(window)

def test_effect_group_duplicate_delete_and_undo(tmp_path):
    window=_window(tmp_path);ui=window._effect_ui_root_ids();window.select_effect_layers_with_modifiers(ui[0]);window.select_effect_layers_with_modifiers(ui[1],Qt.KeyboardModifier.ShiftModifier);group=window.create_effect_group_selected();window.application_undo_stack.clear()
    duplicate=window.duplicate_effect_group(group.id);assert duplicate and duplicate.id!=group.id and len(duplicate.children)==2
    assert window.delete_effect_group(duplicate.id);assert window.project.effect_group_by_id(duplicate.id) is None
    window.application_undo_stack.undo();assert window.project.effect_group_by_id(duplicate.id)
    _close(window)
