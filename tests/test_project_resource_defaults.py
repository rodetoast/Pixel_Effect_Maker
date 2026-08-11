import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.source_asset import SourceAsset
from app.ui.new_project_dialog import NewProjectDialog
from app.ui.resource_editor_v2.new_resource_dialog import NewResourceDialog


APP = QApplication.instance() or QApplication([])


class Localization:
    def text(self, key):
        return key


def test_new_project_defaults_to_600x600_and_one_second():
    dialog = NewProjectDialog()
    values = dialog.settings()
    assert (values.width, values.height) == (600, 600)
    assert values.fps == 12
    assert values.frame_count == 12
    project = Project.create_default()
    assert (project.width, project.height, project.fps, len(project.frames)) == (600,600,12,12)


def test_project_fps_change_updates_auto_frame_count():
    dialog = NewProjectDialog()
    dialog.fps_spin.setValue(24)
    assert dialog.frame_count_auto
    assert dialog.frame_count_spin.value() == 24


def test_manual_project_frame_count_disables_auto_link():
    dialog = NewProjectDialog()
    dialog.fps_spin.setValue(24)
    dialog.frame_count_spin.setValue(48)
    assert not dialog.frame_count_auto
    dialog.fps_spin.setValue(30)
    assert dialog.frame_count_spin.value() == 48


def test_new_resource_defaults_to_300x300_and_project_second():
    dialog = NewResourceDialog(None, Localization(), defaults=(300,300,24,True))
    _,width,height,fps,frames,_ = dialog.values()
    assert (width,height,fps,frames) == (300,300,24,24)


def test_resource_fps_change_updates_auto_frame_count():
    dialog = NewResourceDialog(None, Localization(), defaults=(300,300,12,True))
    dialog.fps.setValue(30)
    assert dialog.resource_frame_count_auto
    assert dialog.frames.value() == 30


def test_manual_resource_frame_count_disables_auto_link():
    dialog = NewResourceDialog(None, Localization(), defaults=(300,300,12,True))
    dialog.frames.setValue(48)
    assert not dialog.resource_frame_count_auto
    dialog.fps.setValue(30)
    assert dialog.frames.value() == 48


def test_existing_resource_does_not_follow_later_project_fps():
    project = Project.create_default(width=32,height=32,fps=24)
    dialog = NewResourceDialog(None, Localization(), defaults=(300,300,project.fps,True))
    name,width,height,fps,frames,loop = dialog.values()
    from app.models.resource_composition import ResourceComposition
    resource = ResourceComposition(name,width,height,fps,frames,loop)
    project.fps = 60
    assert (resource.fps,resource.frame_count) == (24,24)


def test_asset_based_resource_keeps_asset_size_and_inherits_project_second():
    import numpy as np
    asset = SourceAsset("Imported.png", np.zeros((45, 80, 4), dtype=np.uint8))
    dialog = NewResourceDialog(asset, Localization(), defaults=(300,300,30,True))
    _,width,height,fps,frames,_ = dialog.values()
    assert (width,height,fps,frames) == (80,45,30,30)
