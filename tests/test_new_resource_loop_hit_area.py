import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionButton

from app.services.localization_service import LocalizationService
from app.ui.resource_editor_v2.new_resource_dialog import NewResourceDialog


APP = QApplication.instance() or QApplication([])


def _dialog(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    dialog = NewResourceDialog(None, LocalizationService(settings, "en"), defaults=(64, 64, 12, True))
    dialog.resize(520, 420); dialog.show(); APP.processEvents()
    return dialog


def test_loop_checkbox_click_target_is_indicator_and_text_only(tmp_path):
    dialog = _dialog(tmp_path); checkbox = dialog.loop
    assert checkbox.width() < dialog.form.geometry().width()
    option = QStyleOptionButton(); option.initFrom(checkbox); option.text = checkbox.text()
    indicator = checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, checkbox)
    before = checkbox.isChecked(); QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=indicator.center())
    assert checkbox.isChecked() is not before
    text_point = QPoint(min(checkbox.width() - 2, indicator.right() + max(4, (checkbox.width() - indicator.right()) // 2)), checkbox.height() // 2)
    QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=text_point)
    assert checkbox.isChecked() is before
    empty = checkbox.mapTo(dialog, QPoint(checkbox.width() + 80, checkbox.height() // 2))
    QTest.mouseClick(dialog, Qt.MouseButton.LeftButton, pos=empty)
    assert checkbox.isChecked() is before
    dialog.close()


def test_loop_checkbox_remains_keyboard_accessible(tmp_path):
    dialog = _dialog(tmp_path); checkbox = dialog.loop; dialog.name.setFocus(); APP.processEvents()
    for _ in range(12):
        if checkbox.hasFocus(): break
        QTest.keyClick(dialog, Qt.Key.Key_Tab); APP.processEvents()
    assert checkbox.hasFocus()
    before = checkbox.isChecked(); QTest.keyClick(checkbox, Qt.Key.Key_Space)
    assert checkbox.isChecked() is not before
    dialog.close()
