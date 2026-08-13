import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget

APP=QApplication.instance() or QApplication([])


def _editor(tmp_path):
    project=Project.create_default(width=4,height=4,frame_count=2);composition=ResourceComposition("C",4,4,12,2)
    for index in range(4):
        pixels=np.zeros((1,1,4),dtype=np.uint8);pixels[0,0,3]=255;asset=SourceAsset(str(index),pixels);project.source_assets.append(asset);composition.layers.append(CompositionLayer(str(index),"source_asset",asset.id,0,1))
    composition.repair_hierarchy();project.resource_compositions=[composition]
    editor=ResourceEditorWidget(QSettings(str(tmp_path/"group.ini"),QSettings.Format.IniFormat));stack=QUndoStack();editor.set_undo_stack(stack);editor.refresh(project);editor.controller.select_composition(composition.id,composition.layers[-1].id)
    return editor,stack,composition


def test_create_collapse_rename_ungroup_and_undo(tmp_path):
    editor,stack,composition=_editor(tmp_path);ui=editor._ui_root_ids()
    editor.select_layer_with_modifiers(ui[0]);editor.select_layer_with_modifiers(ui[1],Qt.KeyboardModifier.ShiftModifier)
    group=editor.create_group_selected();assert group and group.children==list(reversed(ui[:2]))
    assert editor.rename_group(group.id,"Foreground") and composition.group_by_id(group.id).name=="Foreground"
    assert editor.toggle_group_expanded(group.id,False) and group.id not in editor.expanded_group_ids
    assert editor.ungroup(group.id) and not composition.groups
    stack.undo();assert composition.groups and composition.group_by_id(group.id)
    editor.close()

def test_group_lock_blocks_child_edit_and_delete(tmp_path):
    editor,stack,composition=_editor(tmp_path);ui=editor._ui_root_ids();editor.select_layer_with_modifiers(ui[0]);editor.select_layer_with_modifiers(ui[1],Qt.KeyboardModifier.ShiftModifier);group=editor.create_group_selected();stack.clear()
    assert editor.set_group_state(group.id,"locked",True)
    child=composition.group_by_id(group.id).children[0];editor.select_layer_with_modifiers(child)
    assert not editor.delete_selected_layers() and editor._layer_effectively_locked(next(item for item in composition.layers if item.id==child))
    editor.close()
