"""Style-local native repeat contracts, cancellation and negative controls."""
import pytest
from PySide6.QtCore import QObject,QEvent,QAbstractEventDispatcher
from PySide6.QtWidgets import QProxyStyle,QStyleFactory,QStyle,QWidget
from app.ui.focus_wheel_widgets import ScrollSafeSpinBox,ScrollSafeDoubleSpinBox
from tests.test_native_spinbox_buttons import APP,button_center
from tests.spinbox_repeat_support import verify_native_repeat


class RepeatStyle(QProxyStyle):
    def __init__(self,name,threshold=40):
        super().__init__(QStyleFactory.create(name));self.threshold=threshold
    def styleHint(self,hint,option=None,widget=None,returnData=None):
        if hint==QStyle.StyleHint.SH_SpinBox_ClickAutoRepeatThreshold:return self.threshold
        if hint==QStyle.StyleHint.SH_SpinBox_ClickAutoRepeatRate:return 25
        return super().styleHint(hint,option,widget,returnData)


def setup_widget(kind=ScrollSafeSpinBox,name='Fusion',threshold=40):
    spin=kind();spin.setRange(0,200);spin.setValue(91);style=RepeatStyle(name,threshold);style.setParent(spin)
    for widget in (spin,*spin.findChildren(QWidget)):widget.setStyle(style)
    spin.show();APP.processEvents()
    return spin


@pytest.mark.parametrize('name',['Fusion','windows11'])
@pytest.mark.parametrize('kind',[ScrollSafeSpinBox,ScrollSafeDoubleSpinBox])
@pytest.mark.parametrize('direction',[1,-1])
def test_controlled_style_native_repeats_and_stops(name,kind,direction):
    before=APP.style();spin=setup_widget(kind,name)
    try:
        control=QStyle.SubControl.SC_SpinBoxUp if direction==1 else QStyle.SubControl.SC_SpinBoxDown
        result=verify_native_repeat(spin,button_center(spin,control),direction)
        assert result['phase']=='complete' and result['timer_events']>=2
        assert result['after_release_changes']==0
        assert APP.style() is before
    finally:spin.close();spin.deleteLater();APP.processEvents()


def test_completion_contract_handles_style_threshold_beyond_legacy_800ms():
    spin=setup_widget(threshold=900)
    try:
        result=verify_native_repeat(spin,button_center(spin,QStyle.SubControl.SC_SpinBoxUp))
        assert result['phase']=='complete' and spin.value()>=94
    finally:spin.close();spin.deleteLater();APP.processEvents()


def test_contract_rejects_missing_repeat_and_releases_on_failure():
    spin=setup_widget()
    class BlockRepeat(QObject):
        def eventFilter(self,watched,event):return event.type()==QEvent.Type.Timer
    block=BlockRepeat(spin);spin.installEventFilter(block)
    try:
        with pytest.raises(AssertionError,match='await_repeat'):
            verify_native_repeat(spin,button_center(spin,QStyle.SubControl.SC_SpinBoxUp),timeout=150)
        assert spin.value()==92
        assert not QAbstractEventDispatcher.instance().registeredTimers(spin)
    finally:spin.removeEventFilter(block);spin.close();spin.deleteLater();APP.processEvents()


def test_contract_rejects_release_that_does_not_stop_repeat():
    class BrokenRelease(ScrollSafeSpinBox):
        def mouseReleaseEvent(self,event):event.accept()
    spin=setup_widget(BrokenRelease)
    try:
        with pytest.raises(AssertionError,match='active_repeat_timers'):
            verify_native_repeat(spin,button_center(spin,QStyle.SubControl.SC_SpinBoxUp))
    finally:spin.close();spin.deleteLater();APP.processEvents()
