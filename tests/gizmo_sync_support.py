"""Test-only observations: no project payloads, no production instrumentation."""
from PySide6.QtCore import QElapsedTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

class GizmoSyncObservation:
    def __init__(self,window,layer,panel,monkeypatch):
        self.window=window;self.layer=layer;self.panel=panel;self.records=[]
        self.signals=0;self.starts=0;self.stops=0;self.callbacks=0
        self.requested=False;self.transient_changed=False;self.values_match=False
        self.initial=layer.layer_transform.value("rotation_y",window.frame_index)
        original_fields=panel.set_transform_fields;original_start=window.transform_inspector_timer.start;original_stop=window.transform_inspector_timer.stop
        def fields(item,frame,names):
            original_fields(item,frame,names)
            self.records.append(tuple(names))
            field=panel.fields["rotation_y"];expected=item.layer_transform.value("rotation_y",frame)
            self.values_match=abs(field.value()-expected)<=.5*10**(-field.decimals())+1e-9
        def start(*args):self.starts+=1;return original_start(*args)
        def stop():self.stops+=1;return original_stop()
        monkeypatch.setattr(panel,"set_transform_fields",fields)
        monkeypatch.setattr(window.transform_inspector_timer,"start",start)
        monkeypatch.setattr(window.transform_inspector_timer,"stop",stop)
        window.canvas.resource_transform_changed.connect(self.on_change)
        window.transform_inspector_timer.timeout.connect(self.on_timeout)

    def on_change(self,identifier,transform,final):
        if final:return
        self.signals+=1
        self.transient_changed=self.transient_changed or transform.value("rotation_y",self.window.frame_index)!=self.initial
        self.requested=self.requested or self.window._pending_transform_inspector is not None

    def on_timeout(self):self.callbacks+=1

    def completed(self):
        return bool(self.records and self.callbacks and self.values_match and self.latest_matches() and self.window._pending_transform_inspector is None and not self.window.transform_inspector_timer.isActive())

    def latest_matches(self):
        field=self.panel.fields["rotation_y"]
        expected=self.window.canvas.resource_transform.value("rotation_y",self.window.frame_index)
        return abs(field.value()-expected)<=.5*10**(-field.decimals())+1e-9

    def wait(self,timeout_ms=1000):
        # Qt's Python QTest binding has no qWaitFor(predicate). Pump the real
        # event loop against its completion state, not a guessed elapsed sleep.
        deadline=QElapsedTimer();deadline.start()
        while not self.completed():
            if deadline.elapsed()>=timeout_ms:return False
            QTest.qWait(1);QApplication.processEvents()
        # Include deferred geometry requests in the existing bounded-layout check.
        QApplication.processEvents()
        return self.completed()

    def snapshot(self):
        timer=self.window.transform_inspector_timer
        transformed=self.transient_changed or self.window.canvas.resource_transform.value("rotation_y",self.window.frame_index)!=self.initial
        if not transformed:stage="transform_not_changed"
        elif not self.signals:stage="signal_not_observed"
        elif not self.requested or not self.starts:stage="refresh_not_scheduled"
        elif self.stops and not self.callbacks:stage="timer_cancelled"
        elif not self.callbacks:stage="awaiting_callback"
        elif not self.records:stage="callback_without_fields"
        elif not self.values_match:stage="field_value_mismatch"
        else:stage="complete" if self.completed() else "pending_refresh"
        return dict(stage=stage,transient_changed=transformed,signal_count=self.signals,refresh_requested=self.requested,timer_starts=self.starts,timer_stops=self.stops,callback_count=self.callbacks,field_refresh_count=len(self.records),fields_correct=bool(self.records) and all(names==("rotation_y",) for names in self.records),value_matches=self.values_match and self.latest_matches(),pending=self.window._pending_transform_inspector is not None,timer_active=timer.isActive(),document_changed=self.layer.layer_transform.value("rotation_y",self.window.frame_index)!=self.initial)

    def disconnect(self):
        self.window.canvas.resource_transform_changed.disconnect(self.on_change)
        self.window.transform_inspector_timer.timeout.disconnect(self.on_timeout)
