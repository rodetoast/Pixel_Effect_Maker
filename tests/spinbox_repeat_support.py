"""Observe native Qt repeating steps without replacing production handlers."""
from PySide6.QtCore import QAbstractEventDispatcher,QElapsedTimer,QEvent,QObject,QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def wait_until(predicate,timeout=2500):
    clock=QElapsedTimer();clock.start()
    while not predicate():
        if clock.elapsed()>=timeout:return False
        QTest.qWait(1)
    return True


class RepeatObservation(QObject):
    def __init__(self,spin):
        super().__init__(spin);self.spin=spin;self.events=[];self.changes=[];self.timer_events=0;self.focus_out=0
        self.phase='before_press';self.released=False;self.after_release_changes=0
        self.clock=QElapsedTimer();self.clock.start()
        self.baseline_timers=self.timer_ids()
        spin.installEventFilter(self);spin.valueChanged.connect(self.changed)

    def timer_ids(self):
        return {info.timerId for info in QAbstractEventDispatcher.instance().registeredTimers(self.spin)}

    def eventFilter(self,watched,event):
        kind=event.type()
        if kind==QEvent.Type.Timer:self.timer_events+=1
        if kind==QEvent.Type.FocusOut and not self.released:self.focus_out+=1
        if kind in (QEvent.Type.Timer,QEvent.Type.FocusIn,QEvent.Type.FocusOut,QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease,QEvent.Type.Hide):
            self.events.append((self.clock.elapsed(),kind.name))
        return False

    def changed(self,value):
        self.changes.append((float(value),self.timer_events))
        if self.released:self.after_release_changes+=1

    def snapshot(self):
        return dict(phase=self.phase,timer_events=self.timer_events,value_changes=len(self.changes),
                    focus_out_before_release=self.focus_out,after_release_changes=self.after_release_changes,
                    active_repeat_timers=len(self.timer_ids()-self.baseline_timers),events=self.events[-16:])

    def disconnect(self):
        self.spin.removeEventFilter(self);self.spin.valueChanged.disconnect(self.changed)


def verify_native_repeat(spin,point,direction=1,timeout=2500):
    """Require an initial step, two timer-driven repeats, and release cancellation."""
    window=spin.window();window.activateWindow();spin.setFocus()
    assert wait_until(lambda:window.isActiveWindow() and spin.hasFocus(),timeout), 'spinbox activation deadline'
    probe=RepeatObservation(spin);start=spin.value();step=spin.singleStep()*direction
    try:
        try:
            probe.phase='press'
            QTest.mousePress(spin,Qt.MouseButton.LeftButton,pos=point)
            assert spin.value()==start+step,probe.snapshot()
            assert probe.timer_ids()-probe.baseline_timers,probe.snapshot()
            probe.phase='await_repeat'
            assert wait_until(lambda:len(probe.changes)>=3 and probe.timer_events>=2,timeout),probe.snapshot()
            assert [v for v,_ in probe.changes[:3]]==[start+step*i for i in (1,2,3)],probe.snapshot()
            assert all(timer_count>0 for _,timer_count in probe.changes[1:3]),probe.snapshot()
        finally:
            probe.released=True;probe.phase='released'
            QTest.mouseRelease(spin,Qt.MouseButton.LeftButton,pos=point)
        assert not probe.timer_ids()-probe.baseline_timers,probe.snapshot()
        value=spin.value();guard=QTimer(spin);guard.setSingleShot(True);guard.setTimerType(Qt.TimerType.PreciseTimer)
        rate=spin.style().styleHint(spin.style().StyleHint.SH_SpinBox_ClickAutoRepeatRate,None,spin)
        completed=[];guard.timeout.connect(lambda:completed.append(True));guard.start(max(1,rate)*2+10)
        assert wait_until(lambda:bool(completed),timeout),probe.snapshot()
        assert spin.value()==value and probe.after_release_changes==0,probe.snapshot()
        probe.phase='complete'
        return probe.snapshot()
    finally:
        if 'guard' in locals():guard.stop();guard.deleteLater()
        probe.disconnect()
