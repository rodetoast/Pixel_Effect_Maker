"""Bounded offscreen investigation of the existing inspector-sync test path."""
import os
os.environ["QT_QPA_PLATFORM"]="offscreen"
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from pytest import MonkeyPatch
from tests.test_interactive_transform_proxy import APP,context,close,LayoutCounter

def observe(directory):
    with MonkeyPatch.context() as patch:
        window,layer,_=context(directory,"probe")
        panel=window.composition_layer_properties.transform_panel
        window._set_resource_transform_gizmo(layer.id,"rotate_y")
        timer=window.transform_inspector_timer;started=perf_counter();events=[]
        def event(name,**data):events.append(dict(event=name,ms=round((perf_counter()-started)*1000,3),**data))
        original_start=timer.start;original_stop=timer.stop;original_fields=panel.set_transform_fields
        def start(*args):
            event("timer_start",active_before=timer.isActive(),interval=int(args[0]) if args else timer.interval());return original_start(*args)
        def stop():event("timer_stop");return original_stop()
        def fields(item,frame,names):event("fields_applied",fields=list(names));return original_fields(item,frame,names)
        patch.setattr(timer,"start",start);patch.setattr(timer,"stop",stop);patch.setattr(panel,"set_transform_fields",fields)
        window.canvas.resource_transform_changed.connect(lambda identifier,transform,final:event("transform_signal",final=final,fields=list(window.canvas.resource_transform_changed_fields),pending=window._pending_transform_inspector is not None))
        timer.timeout.connect(lambda:event("timer_timeout",pending=window._pending_transform_inspector is not None))
        counter=LayoutCounter();panel.installEventFilter(counter);APP.processEvents();counter.count=0
        original=layer.layer_transform.value("rotation_y",window.frame_index)
        try:
            handle=window.canvas.resource_transform_handle_positions()["rotate_y"].toPoint()
            event("before_press",hit=window.canvas._hit_resource_transform(handle))
            QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle)
            event("after_press",drag=window.canvas._resource_transform_drag)
            for value in range(20):QTest.mouseMove(window.canvas,handle+QPoint(value+1,value%5))
            event("before_wait",pending=window._pending_transform_inspector is not None,active=timer.isActive(),remaining=timer.remainingTime())
            QTest.qWait(40);APP.processEvents()
            snapshot=dict(records=sum(e["event"]=="fields_applied" for e in events),signals=sum(e["event"]=="transform_signal" for e in events),pending=window._pending_transform_inspector is not None,active=timer.isActive(),remaining=timer.remainingTime(),transient_changed=window.canvas.resource_transform.value("rotation_y",window.frame_index)!=original,document_changed=layer.layer_transform.value("rotation_y",window.frame_index)!=original,layout_requests=counter.count)
            event("legacy_assertion",**snapshot)
            # Observe recovery without manually calling the production callback.
            for _ in range(100):
                if any(e["event"]=="fields_applied" for e in events):break
                QTest.qWait(10);APP.processEvents()
            event("after_completion_wait",records=sum(e["event"]=="fields_applied" for e in events),pending=window._pending_transform_inspector is not None)
            return dict(at_40ms=snapshot,events=events)
        finally:
            if window.canvas._resource_transform_drag:
                QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(20,0))
            close(window);window.deleteLater();APP.processEvents()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--attempts",type=int,default=12)
    parser.add_argument("--precede",action="append",default=[],help="Existing related test file to run before observation")
    parser.add_argument("--verify-fixed",action="store_true",help="Reuse the repaired target test, not legacy 40ms observation")
    args=parser.parse_args();output=args.output.resolve()
    if ROOT==output or ROOT in output.parents or not 1<=args.attempts<=30:parser.error("Use fresh outside-repo output; 1..30 attempts")
    output.mkdir(parents=True,exist_ok=False);results=[]
    if args.precede:
        import pytest
        code=pytest.main([*args.precede,"-q","-p","no:cacheprovider","--basetemp",str(output/"precede"),"--tb=short"])
        print(f"preceding_tests_exit={int(code)}",flush=True)
    for index in range(args.attempts):
        folder=output/str(index);folder.mkdir()
        if args.verify_fixed:
            from tests.test_interactive_transform_proxy import test_gizmo_updates_only_changed_inspector_field_without_layout as target
            properties=[]
            with MonkeyPatch.context() as patch:target(folder,patch,lambda key,value:properties.append(value))
            results.append(properties[-1])
        else:results.append(observe(folder))
    with (output/"observations.json").open("x",encoding="utf-8") as handle:json.dump(results,handle,indent=2)
    if args.verify_fixed:print(json.dumps(dict(attempts=len(results),complete=sum(r["stage"]=="complete" for r in results),states=results)))
    else:print(json.dumps(dict(attempts=len(results),legacy_empty=sum(r["at_40ms"]["records"]==0 for r in results),states=[r["at_40ms"] for r in results])))

if __name__=="__main__":main()
