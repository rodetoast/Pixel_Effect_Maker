"""Controlled scheduler/cancel paths for the same actual Qt Inspector callback."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from tests.test_interactive_transform_proxy import APP,context,close,LayoutCounter
from tests.gizmo_sync_support import GizmoSyncObservation

def begin(tmp_path,monkeypatch,delay=False):
    window,layer,_=context(tmp_path,"sync_wait");panel=window.composition_layer_properties.transform_panel
    window._set_resource_transform_gizmo(layer.id,"rotate_y")
    if delay:
        # Hold scheduling behind an explicit test gate; do not assume that a
        # 40/90ms wall-time margin is stable under a loaded suite either.
        original=window.transform_inspector_timer.start
        queued=[]
        monkeypatch.setattr(window.transform_inspector_timer,"start",lambda *args:queued.append(args))
    probe=GizmoSyncObservation(window,layer,panel,monkeypatch)
    counter=LayoutCounter();panel.installEventFilter(counter);APP.processEvents();counter.count=0
    handle=window.canvas.resource_transform_handle_positions()["rotate_y"].toPoint()
    QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
    for value in range(20):QTest.mouseMove(window.canvas,handle+QPoint(value+1,value%5))
    if delay:probe.release_timer=lambda:original(*queued[-1])
    return window,probe,counter,handle

def finish(window,probe,handle):
    probe.disconnect()
    if window.canvas._resource_transform_drag:QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(20,0))
    close(window)

def test_completion_wait_covers_late_qt_callback_not_just_elapsed_sleep(tmp_path,monkeypatch,record_property):
    window,probe,counter,handle=begin(tmp_path,monkeypatch,delay=True)
    try:
        APP.processEvents()
        assert not probe.records and probe.snapshot()["stage"]=="awaiting_callback"
        assert probe.snapshot()["transient_changed"] and probe.signals>0 and probe.requested
        probe.release_timer()  # Starts the unchanged 33ms production Qt timer.
        assert probe.wait(1000),probe.snapshot()
        assert all(names==("rotation_y",) for names in probe.records) and counter.count<=3
        assert probe.snapshot()["value_matches"] and not probe.snapshot()["document_changed"]
    finally:
        record_property("gizmo_sync",{**probe.snapshot(),"layout_requests":counter.count});finish(window,probe,handle)

def test_escape_cancels_pending_request_instead_of_faking_success(tmp_path,monkeypatch,record_property):
    window,probe,_,handle=begin(tmp_path,monkeypatch,delay=True)
    try:
        probe.release_timer()
        QTest.keyClick(window.canvas,Qt.Key.Key_Escape);APP.processEvents()
        assert not probe.wait(20)
        state=probe.snapshot()
        assert state["stage"]=="timer_cancelled" and not state["pending"] and not state["timer_active"]
        assert not state["callback_count"] and not state["document_changed"]
    finally:
        record_property("gizmo_sync",probe.snapshot());finish(window,probe,handle)
