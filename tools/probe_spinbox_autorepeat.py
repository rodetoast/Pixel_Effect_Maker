"""Bounded synthetic offscreen press/repeat observations, no user payload."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QObject,QEvent,QElapsedTimer,QTimer,QAbstractEventDispatcher,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle,QStyleFactory,QProxyStyle,QWidget
import pytest
from tests.test_native_spinbox_buttons import APP,localization,source_asset,button_center
from app.ui.resource_editor_v2.new_resource_dialog import NewResourceDialog
from tests import test_native_spinbox_buttons as native_tests


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--attempts',type=int,choices=range(1,17),default=6)
    parser.add_argument('--style',choices=['current','Fusion','windows11'],default='current')
    parser.add_argument('--precede',action='append',default=[])
    parser.add_argument('--block-dispatch',action='store_true')
    parser.add_argument('--threshold',type=int,choices=[0,900],default=0)
    parser.add_argument('--verify-fixed',action='store_true')
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    if args.precede:
        code=pytest.main([*args.precede,'-q','-p','no:cacheprovider','--basetemp='+str(out/'precede')])
        if code:return int(code)
    results=[]
    for attempt in range(args.attempts):
        with tempfile.TemporaryDirectory(dir=out) as directory:
            if args.verify_fixed:
                fixture=native_tests.dialog.__wrapped__(Path(directory));dialog=next(fixture)
                try:
                    native_tests.test_mouse_press_hold_uses_qt_native_auto_repeat(dialog)
                    results.append(dict(attempt=attempt,contract='PASS'))
                finally:
                    try:next(fixture)
                    except StopIteration:pass
                continue
            _,language=localization(Path(directory));dialog=NewResourceDialog(source_asset(),language)
            if args.style!='current' or args.threshold:
                class ProbeStyle(QProxyStyle):
                    def styleHint(self,hint,option=None,widget=None,returnData=None):
                        if args.threshold and hint==QStyle.StyleHint.SH_SpinBox_ClickAutoRepeatThreshold:return args.threshold
                        return super().styleHint(hint,option,widget,returnData)
                style=ProbeStyle(QStyleFactory.create(args.style if args.style!='current' else 'Fusion'));style.setParent(dialog)
                for widget in (dialog,*dialog.findChildren(QWidget)):widget.setStyle(style)
            dialog.show();APP.processEvents();spin=dialog.width;spin.setValue(91)
            timer=QElapsedTimer();timer.start();events=[]
            class Observer(QObject):
                def eventFilter(self,watched,event):
                    if event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease,QEvent.Type.Timer,
                                       QEvent.Type.FocusIn,QEvent.Type.FocusOut,QEvent.Type.Hide,QEvent.Type.StyleChange,QEvent.Type.EnabledChange):
                        events.append(dict(ms=timer.elapsed(),event=event.type().name,value=spin.value(),
                                           timer=event.timerId() if event.type()==QEvent.Type.Timer else None))
                    return False
            observer=Observer(spin);spin.installEventFilter(observer)
            spin.valueChanged.connect(lambda value:events.append(dict(ms=timer.elapsed(),event='valueChanged',value=value)))
            hints={name:spin.style().styleHint(getattr(QStyle.StyleHint,name),None,spin) for name in (
                'SH_SpinBox_ClickAutoRepeatThreshold','SH_SpinBox_ClickAutoRepeatRate')}
            point=button_center(spin,QStyle.SubControl.SC_SpinBoxUp)
            try:
                QTest.mousePress(spin,Qt.MouseButton.LeftButton,pos=point)
                if args.block_dispatch:
                    def bounded_busy_callback():
                        events.append(dict(ms=timer.elapsed(),event='busy_start',value=spin.value()))
                        deadline=QElapsedTimer();deadline.start()
                        while deadline.elapsed()<750:pass
                        events.append(dict(ms=timer.elapsed(),event='busy_end',value=spin.value()))
                    QTimer.singleShot(100,bounded_busy_callback)
                QTest.qWait(800)
                events.append(dict(ms=timer.elapsed(),event='legacy_assert_boundary',value=spin.value(),
                                   timer_intervals=[t.interval for t in QAbstractEventDispatcher.instance().registeredTimers(spin)]))
                QTest.mouseRelease(spin,Qt.MouseButton.LeftButton,pos=point)
                results.append(dict(attempt=attempt,style=spin.style().objectName(),hints=hints,
                                    enabled=spin.isEnabled(),step_up=bool(spin.stepEnabled() & spin.StepEnabledFlag.StepUpEnabled),
                                    final=spin.value(),events=events))
            finally:
                dialog.close();dialog.deleteLater();APP.processEvents()
    (out/'observations.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
