import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.services.settings_service import ShortcutSettingsService
from app.models.project import FORMAT_VERSION
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def make_window(tmp_path):
    settings = QSettings(str(tmp_path / "state.ini"), QSettings.Format.IniFormat)
    return MainWindow(ShortcutSettingsService(settings))


def finish(window):
    window.dirty = False
    window._non_undo_dirty = False
    window.close()


def test_failed_open_does_not_replace_current_project(tmp_path, monkeypatch):
    window = make_window(tmp_path)
    current = window.project
    bad = tmp_path / "bad.peffect.json"
    bad.write_text("{", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(bad), ""))
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    window.open_project()
    assert window.project is current
    finish(window)


def test_new_project_stops_existing_playback(tmp_path):
    window = make_window(tmp_path)
    window.set_playing(True)
    assert window.play_timer.isActive()
    from app.ui.new_project_dialog import NewProjectSettings
    window.apply_new_project_settings(
        NewProjectSettings("New", 8, 8, 12, True, frame_count=1)
    )
    assert not window.play_timer.isActive()
    finish(window)


def test_new_project_rejects_non_finite_and_oversized_initial_allocation():
    from app.ui.new_project_dialog import NewProjectSettings
    import pytest
    with pytest.raises(ValueError, match="finite integers"):
        NewProjectSettings("Bad", float("nan"), 8, 12, True, 1)
    with pytest.raises(ValueError, match="safe limit"):
        NewProjectSettings("Huge", 1024, 1024, 12, True, 999)


def test_copy_diagnostics_excludes_current_project_pixels(tmp_path):
    window = make_window(tmp_path)
    window.project.name = "PRIVATE_PROJECT_SENTINEL"
    window.copy_diagnostic_information()
    text = APP.clipboard().text()
    assert "Pixel Effect Maker v0.0.10" in text
    assert f"Project Format: {FORMAT_VERSION}" in text
    assert "PRIVATE_PROJECT_SENTINEL" not in text
    assert "layer_pixels" not in text
    finish(window)


def test_repeated_open_reuses_window_without_timer_or_cache_accumulation(tmp_path, monkeypatch):
    from app.models.project import Project
    from app.services.project_io import save_project
    from app.services import effect_resource_layer_render_service
    path = save_project(Project.create_default("Repeat", 8, 8), tmp_path / "repeat.peffect.json")
    window = make_window(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))
    for _ in range(20):
        window.open_project()
    assert window.project.name == "Repeat"
    assert window.interactive_proxy_prewarm._poll.isActive()
    assert not effect_resource_layer_render_service._BASE_CACHE
    finish(window)
