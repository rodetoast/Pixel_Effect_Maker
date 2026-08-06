import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
import pytest

from app.models.project import Project
from app.services import project_io
from app.services.project_io import ProjectIOError,save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def window(tmp_path):
    settings=QSettings(str(tmp_path/"settings.ini"),QSettings.Format.IniFormat);value=MainWindow(ShortcutSettingsService(settings));value.dirty=True;value._non_undo_dirty=True;return value


def close(value):value.dirty=False;value._non_undo_dirty=False;value.close()


def test_atomic_save_flushes_fsyncs_and_replaces_target(tmp_path,monkeypatch):
    target=tmp_path/"project.peffect.json";calls=[];real_fsync=project_io.os.fsync;real_replace=project_io.os.replace
    monkeypatch.setattr(project_io.os,"fsync",lambda fd:calls.append("fsync") or real_fsync(fd));monkeypatch.setattr(project_io.os,"replace",lambda source,destination:calls.append((Path(source).parent,Path(destination))) or real_replace(source,destination))
    save_project(Project.create_default(),target)
    assert calls[0]=="fsync" and calls[1][0]==target.parent and calls[1][1]==target


def test_save_failure_preserves_existing_project_and_removes_temp(tmp_path,monkeypatch):
    target=tmp_path/"project.peffect.json";target.write_bytes(b"known-good");before=set(tmp_path.glob("*.tmp"))
    monkeypatch.setattr(project_io.os,"replace",lambda *args:(_ for _ in ()).throw(PermissionError("locked")))
    with pytest.raises(ProjectIOError):save_project(Project.create_default(),target)
    assert target.read_bytes()==b"known-good" and set(tmp_path.glob("*.tmp"))==before


def test_save_failure_keeps_dirty_state_and_path(tmp_path,monkeypatch):
    value=window(tmp_path);old=tmp_path/"old.peffect.json";value.project_path=old
    monkeypatch.setattr("app.ui.main_window.save_project",lambda *args:(_ for _ in ()).throw(ProjectIOError("disk full","save_failed")));monkeypatch.setattr(QMessageBox,"critical",lambda *args:None)
    assert not value.save() and value.dirty and value.project_path==old;close(value)


def test_save_as_failure_keeps_previous_project_path(tmp_path,monkeypatch):
    value=window(tmp_path);old=tmp_path/"old.peffect.json";value.project_path=old;new=tmp_path/"new.peffect.json"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *args:(str(new),""));monkeypatch.setattr("app.ui.main_window.save_project",lambda *args:(_ for _ in ()).throw(ProjectIOError("denied","save_failed")));monkeypatch.setattr(QMessageBox,"critical",lambda *args:None)
    assert not value.save_as() and value.project_path==old and value.dirty;close(value)


def test_save_as_cancel_is_noop(tmp_path,monkeypatch):
    value=window(tmp_path);old=tmp_path/"old.peffect.json";value.project_path=old;monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *args:("",""))
    assert not value.save_as() and value.project_path==old and value.dirty;close(value)


def test_duplicate_save_request_is_rejected(tmp_path):
    value=window(tmp_path);value._save_in_progress=True
    assert not value._save_to_path(tmp_path/"new.peffect.json") and value.dirty;value._save_in_progress=False;close(value)


def test_successful_save_clears_dirty_and_sets_path(tmp_path):
    value=window(tmp_path);target=tmp_path/"new.peffect.json"
    assert value._save_to_path(target) and value.project_path==target and not value.dirty and target.exists();close(value)


def test_save_completion_keeps_dirty_if_revision_changed(tmp_path,monkeypatch):
    value=window(tmp_path);target=tmp_path/"new.peffect.json"
    def changed(project,path):value._mark_dirty();return Path(path)
    monkeypatch.setattr("app.ui.main_window.save_project",changed)
    assert value._save_to_path(target) and value.project_path==target and value.dirty;close(value)
