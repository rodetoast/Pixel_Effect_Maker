import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from app.main import prepare_normal_startup, preview_notice_enabled_for_arguments
from app.models.project import FORMAT_VERSION, Project
from app.services.localization_service import LocalizationService
from app.ui.preview_build_notice_dialog import (
    PreviewBuildNoticeDialog,
    preview_notice_settings_key,
    preview_notice_was_accepted,
    should_show_preview_notice,
)
from app.version import PREVIEW_BUILD, PREVIEW_NOTICE_REVISION


APP = QApplication.instance() or QApplication([])


def notice_context(tmp_path, language="en", manual=False):
    settings = QSettings(str(tmp_path / f"notice-{language}-{manual}.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/language", language)
    localization = LocalizationService(settings, system_locale="en_US")
    dialog = PreviewBuildNoticeDialog(localization, settings, manual_open=manual)
    return settings, localization, dialog


class FakeWindow:
    def __init__(self):
        self.localization = object()
        self.project = Project.create_default()
        self.project_path = None
        self.refreshes = 0
        self.created = None

    def _refresh_all(self):
        self.refreshes += 1

    def apply_new_project_settings(self, values):
        self.created = values


class AcceptedStartup:
    opened_project = None
    opened_path = None

    def __init__(self, parent, localization):
        pass

    def exec(self):
        return QDialog.DialogCode.Accepted

    def settings(self):
        return "new-project-values"


def test_preview_notice_is_enabled_for_preview_build(tmp_path):
    settings = QSettings(str(tmp_path / "enabled.ini"), QSettings.Format.IniFormat)
    assert PREVIEW_BUILD and should_show_preview_notice(settings)


def test_preview_notice_not_shown_for_version():
    assert not preview_notice_enabled_for_arguments(["--version"])


def test_preview_notice_not_shown_for_check():
    assert not preview_notice_enabled_for_arguments(["--check"])


def test_preview_notice_shown_on_normal_start():
    calls = []
    window = FakeWindow()
    assert prepare_normal_startup(window, [], notice_runner=lambda item: calls.append(item) or True, startup_factory=AcceptedStartup)
    assert calls == [window] and window.created == "new-project-values"


def test_preview_notice_shown_when_project_path_is_passed(tmp_path):
    path = tmp_path / "passed.peffect.json"; path.write_text("{}", encoding="utf-8")
    calls = []; loads = []
    window = FakeWindow(); loaded = Project.create_default("Loaded")
    assert prepare_normal_startup(window, [str(path)], notice_runner=lambda item: calls.append(item) or True, project_loader=lambda value: loads.append(value) or loaded)
    assert calls == [window] and loads == [Path(path)] and window.project is loaded and window.refreshes == 1


def test_accept_continues_startup():
    window = FakeWindow()
    assert prepare_normal_startup(window, [], notice_runner=lambda item: True, startup_factory=AcceptedStartup)
    assert window.created == "new-project-values"


def test_reject_exits_before_startup_dialog():
    window = FakeWindow()
    def forbidden(*args):
        raise AssertionError("Startup dialog must not be created")
    assert not prepare_normal_startup(window, [], notice_runner=lambda item: False, startup_factory=forbidden)


def test_reject_does_not_load_project(tmp_path):
    window = FakeWindow(); calls = []
    assert not prepare_normal_startup(window, [str(tmp_path / "never.peffect.json")], notice_runner=lambda item: False, project_loader=lambda value: calls.append(value))
    assert calls == []


def test_do_not_show_again_is_scoped_to_current_notice_revision(tmp_path):
    settings, _, dialog = notice_context(tmp_path)
    dialog.do_not_show_check.setChecked(True); dialog._accept_startup()
    assert preview_notice_was_accepted(settings)
    assert settings.value(preview_notice_settings_key(), False, type=bool)


def test_new_notice_revision_shows_again(tmp_path):
    settings = QSettings(str(tmp_path / "revision.ini"), QSettings.Format.IniFormat)
    old_key = preview_notice_settings_key(revision=max(0, PREVIEW_NOTICE_REVISION - 1))
    settings.setValue(old_key, True); settings.sync()
    assert should_show_preview_notice(settings)


def test_notice_setting_is_not_written_to_project(tmp_path):
    settings, _, dialog = notice_context(tmp_path)
    dialog.do_not_show_check.setChecked(True); dialog._accept_startup()
    assert "preview_notice" not in str(Project.create_default().to_dict())


def test_manual_open_ignores_previous_acceptance(tmp_path):
    settings = QSettings(str(tmp_path / "manual.ini"), QSettings.Format.IniFormat)
    settings.setValue(preview_notice_settings_key(), True)
    localization = LocalizationService(settings, system_locale="en_US")
    dialog = PreviewBuildNoticeDialog(localization, settings, manual_open=True)
    assert not should_show_preview_notice(settings)
    assert dialog.manual_open and dialog.do_not_show_check.isHidden() and dialog.exit_button is None


def test_help_menu_opens_project_overview(tmp_path, monkeypatch):
    from app.services.settings_service import ShortcutSettingsService
    from app.ui.main_window import MainWindow
    import app.ui.main_window as main_window_module

    calls = []
    class FakeDialog:
        def __init__(self, localization, settings, parent, manual_open=False):
            calls.append((localization, settings, parent, manual_open))
        def exec(self):
            calls.append("exec")

    monkeypatch.setattr(main_window_module, "PreviewBuildNoticeDialog", FakeDialog)
    service = ShortcutSettingsService(QSettings(str(tmp_path / "help.ini"), QSettings.Format.IniFormat))
    window = MainWindow(service); window.project_overview_action.trigger()
    assert calls[-1] == "exec" and calls[0][2] is window and calls[0][3] is True
    window.dirty = False; window._non_undo_dirty = False; window.close()


def test_preview_notice_korean_and_english_text(tmp_path):
    _, _, ko = notice_context(tmp_path, "ko")
    _, _, en = notice_context(tmp_path, "en")
    assert "개발 중" in ko.badge_label.text() and "중요한 작업" in ko.sections[0][1].text()
    assert "Work in progress" in en.badge_label.text() and "separate backups" in en.sections[0][1].text()


def test_preview_notice_retranslates(tmp_path):
    _, localization, dialog = notice_context(tmp_path, "en")
    localization.set_language("ko")
    assert dialog.do_not_show_check.text() == "이 빌드에서는 다시 표시하지 않기"


def test_preview_notice_fits_560_width_without_horizontal_scroll(tmp_path):
    _, _, dialog = notice_context(tmp_path)
    dialog.resize(560, 480); dialog.show(); APP.processEvents()
    assert dialog.minimumWidth() == 560 and dialog.width() == 560
    assert dialog.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert dialog.scroll_area.horizontalScrollBar().maximum() == 0
    dialog.close()


def test_preview_notice_keyboard_accept(tmp_path):
    _, _, dialog = notice_context(tmp_path)
    dialog.show(); APP.processEvents(); QTest.keyClick(dialog, Qt.Key.Key_Return)
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_preview_notice_escape_rejects(tmp_path):
    _, _, dialog = notice_context(tmp_path)
    dialog.show(); APP.processEvents(); QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_build_and_format_identity_remain_stable():
    from app.version import get_display_name
    assert get_display_name() == "Pixel Effect Maker v0.0.04" and FORMAT_VERSION == 9
