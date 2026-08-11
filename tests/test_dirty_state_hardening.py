import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def make_window(tmp_path):
    settings = QSettings(str(tmp_path / "dirty.ini"), QSettings.Format.IniFormat)
    window = MainWindow(ShortcutSettingsService(settings))
    window.dirty = True
    window._non_undo_dirty = True
    return window


def finish(window):
    window.dirty = False
    window._non_undo_dirty = False
    window.close()


def test_close_save_failure_is_rejected(tmp_path, monkeypatch):
    window = make_window(tmp_path)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(window, "save", lambda: False)
    assert window._confirm_discard() is False
    assert window.dirty
    finish(window)


def test_close_cancel_preserves_dirty_project(tmp_path, monkeypatch):
    window = make_window(tmp_path)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    assert window._confirm_discard() is False
    assert window.dirty
    finish(window)


def test_close_discard_does_not_call_save(tmp_path, monkeypatch):
    window = make_window(tmp_path)
    calls = []
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Discard)
    monkeypatch.setattr(window, "save", lambda: calls.append("save") or True)
    assert window._confirm_discard() is True
    assert calls == []
    finish(window)
