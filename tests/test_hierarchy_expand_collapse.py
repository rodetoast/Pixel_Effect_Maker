import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from copy import deepcopy
from PySide6.QtCore import QSettings
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QApplication

from app.models.layer_group import LayerGroup,group_node
from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget

APP=QApplication.instance() or QApplication([])


def test_expand_collapse_all_is_runtime_only_and_repairs_hidden_primary(tmp_path):
    project=Project.create_default(width=8,height=8,frame_count=2);layers=[CompositionLayer(str(index),"source_asset",str(index),0,1) for index in range(3)];group=LayerGroup("G",children=[layers[0].id,layers[1].id]);composition=ResourceComposition("C",8,8,12,2,layers=layers,groups=[group],root_order=[group_node(group.id),{"type":"layer","id":layers[2].id}]);composition.sync_flat_order();project.resource_compositions=[composition]
    editor=ResourceEditorWidget(QSettings(str(tmp_path/"hierarchy.ini"),QSettings.Format.IniFormat));editor.set_undo_stack(QUndoStack());editor.refresh(project);editor.controller.select_composition(composition.id,layers[0].id);before=deepcopy(project.to_dict())
    assert editor.set_all_groups_expanded(True) and group.id in editor.expanded_group_ids
    assert editor.set_all_groups_expanded(False) and group.id not in editor.expanded_group_ids
    assert editor.layer_selection.primary_id==group.id and project.to_dict()==before
    editor.close()
