from __future__ import annotations

from PySide6.QtCore import QSettings,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QDoubleSpinBox

from app.models.property_registry import NUMERIC_PROPERTY_SPECS
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel


APP=QApplication.instance() or QApplication([])


def test_registered_numeric_properties_respect_min_max_and_steps():
    panel=ParticlePropertiesPanel()
    controls=(panel.motion_perspective,panel.opacity_start,panel.opacity_end)
    for control in controls:
        spec=NUMERIC_PROPERTY_SPECS[str(control.property("numericSpec"))]
        assert control.minimum()==spec.minimum and control.maximum()==spec.maximum and control.singleStep()==spec.step and control.decimals()==spec.decimals


def test_spinbox_up_down_and_programmatic_values_clamp_to_bounds():
    spec=NUMERIC_PROPERTY_SPECS["normalized.perspective"];spin=QDoubleSpinBox();spin.setRange(spec.minimum,spec.maximum);spin.setSingleStep(.1);spin.setDecimals(3)
    spin.setValue(.95);spin.stepUp();assert spin.value()==1.0
    spin.setValue(.05);spin.stepDown();assert spin.value()==0.0
    spin.setValue(1.05);assert spin.value()==1.0
    spin.setValue(-.05);assert spin.value()==0.0


def test_direct_entry_outside_range_is_rejected_or_clamped():
    spin=QDoubleSpinBox();spin.setRange(0,1);spin.setDecimals(3);spin.show();spin.setFocus();spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"1.05");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Return)
    assert 0<=spin.value()<=1
    spin.lineEdit().selectAll();QTest.keyClicks(spin.lineEdit(),"-0.05");QTest.keyClick(spin.lineEdit(),Qt.Key.Key_Return)
    assert 0<=spin.value()<=1;spin.close()


def test_main_window_undo_index_callback_is_registered_qt_slot(tmp_path):
    settings=QSettings(str(tmp_path/"settings.ini"),QSettings.Format.IniFormat);window=MainWindow(ShortcutSettingsService(settings))
    assert window.metaObject().indexOfSlot("_undo_index_changed(int)")>=0
    window._undo_index_changed(window.application_undo_stack.index())
    window.dirty=False;window.close()
