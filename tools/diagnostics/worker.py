"""Private subprocess worker. Never run against a user project or native Qt."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

class Reporter:
    def __init__(self,trace=False):self.items={};self.trace=trace;self.collection_errors=[]
    def pytest_runtest_logreport(self,report):
        item=self.items.setdefault(report.nodeid,dict(test=report.nodeid,status="PASS",duration_seconds=0.0,reason=""))
        item["duration_seconds"]+=report.duration
        # Explicit test-owned, bounded metadata only; never serialize arbitrary
        # pytest user properties, project values, images or traceback locals.
        for key,value in getattr(report,"user_properties",()):
            if key=="gizmo_sync" and isinstance(value,dict):
                booleans={"transient_changed","refresh_requested","fields_correct","value_matches","pending","timer_active","document_changed"}
                counts={"signal_count","timer_starts","timer_stops","callback_count","field_refresh_count","layout_requests"}
                stages={"transform_not_changed","signal_not_observed","refresh_not_scheduled","timer_cancelled","awaiting_callback","callback_without_fields","field_value_mismatch","pending_refresh","complete"}
                safe={k:v for k,v in value.items() if (k in booleans and type(v) is bool) or (k in counts and type(v) is int and 0<=v<=100000) or (k=="stage" and type(v) is str and v in stages)}
                item["observations"]={"gizmo_sync":safe}
        if report.failed:
            item.update(status="FAIL",reason="Assertion or fixture failure; rerun this test with --trace for details")
            if self.trace:
                # Pytest longrepr/locals may include serialized projects or RGBA.
                # Keep stage/location, never arbitrary assertion values/locals.
                crash=getattr(report.longrepr,"reprcrash",None)
                item["failure_location"]=dict(file=str(getattr(crash,"path","<unknown>")),line=getattr(crash,"lineno",None),stage=report.when)
        elif report.skipped and item["status"]!="FAIL":item.update(status="SKIP",reason="pytest skipped this case")
    def pytest_collectreport(self,report):
        if report.failed:self.collection_errors.append("pytest collection failed")

def cleanup_qt():
    # No importing Qt here on a dependency error; clean only if it was loaded.
    import sys
    module=sys.modules.get("PySide6.QtWidgets")
    app=module.QApplication.instance() if module else None
    if app is None:return
    for widget in app.topLevelWidgets():
        # No closeEvent/unsaved-preview dialogs in unattended diagnostics.
        # These objects belong only to this disposable synthetic worker.
        widget.hide();widget.deleteLater()
    app.processEvents()
    from PySide6.QtCore import QCoreApplication,QEvent
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

def execute(check,run_dir,trace=False,screenshots=False):
    import pytest
    from tools.diagnostics.trace_adapter import trace_adapters
    reporter=Reporter(trace);events=[]
    with tempfile.TemporaryDirectory(prefix="scratch-",dir=run_dir) as scratch:
        scratch=Path(scratch)
        os.environ.update(TEMP=str(scratch),TMP=str(scratch),TMPDIR=str(scratch))
        from PySide6.QtCore import QSettings,QStandardPaths,qVersion
        QStandardPaths.setTestModeEnabled(True)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        for scope in (QSettings.Scope.UserScope,QSettings.Scope.SystemScope):QSettings.setPath(QSettings.Format.IniFormat,scope,str(scratch/"settings"))
        from PySide6.QtWidgets import QApplication,QStyleFactory
        application=QApplication.instance() or QApplication([])
        application.setOrganizationName("PEMDiagnostics");application.setApplicationName("SyntheticChecks")
        if check.name=="ui" and "windows11" not in {name.lower() for name in QStyleFactory.keys()}:
            cleanup_qt()
            return dict(status="ERROR",reason="Required windows11 style is unavailable for the registered UI matrix",tests=[],evidence=[],trace=[])
        try:
            with trace_adapters(trace,events):
                code=int(pytest.main([*check.tests,"-q","--tb=short","-p","no:cacheprovider","--basetemp",str(scratch/"pytest")],plugins=[reporter]))
            evidence=[]
            if screenshots and check.name=="ui":
                # Existing probe is an evidence adapter, not a duplicated audit.
                import sys
                from unittest.mock import patch
                from tools.inspector_visual_probe import main as probe
                target=run_dir/"screenshots"
                with patch.object(sys,"argv",["inspector_visual_probe","--output",str(target)]):probe()
                evidence=[str(p.relative_to(run_dir)) for p in target.glob("*.png")]
            status="ERROR" if code not in (0,1,5) else "FAIL" if code==1 else "SKIP" if code==5 else "SKIP" if any(v["status"]=="SKIP" for v in reporter.items.values()) else "PASS"
            result=dict(status=status,pytest_exit_code=code,tests=list(reporter.items.values()),reason="; ".join(reporter.collection_errors),evidence=evidence,trace=events,runtime=dict(qt=qVersion(),qt_platform=os.environ.get("QT_QPA_PLATFORM"),synthetic_only=True))
            if status=="SKIP":result["reason"]="Some or all required cases skipped; this is not PASS"
            elif status=="FAIL":result["reason"]="One or more registered assertions failed"
            return result
        finally:cleanup_qt()

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--name",required=True);parser.add_argument("--run-dir",type=Path,required=True)
    parser.add_argument("--trace",action="store_true");parser.add_argument("--screenshots",action="store_true")
    args=parser.parse_args();directory=args.run_dir.resolve()
    # Parent must have created and contained this worker before imports/spawns.
    deadline=time.monotonic()+15
    while not (directory/"ready").exists():
        if time.monotonic()>deadline:raise RuntimeError("Parent containment barrier missing")
        time.sleep(.01)
    from tools.diagnostics.registry import REGISTRY
    try:result=execute(REGISTRY[args.name],directory,args.trace,args.screenshots)
    except Exception as exc:
        result=dict(status="ERROR",reason=f"Worker exception: {type(exc).__name__}",tests=[],evidence=[],trace=[])
        if args.trace:result["exception_type"]=type(exc).__name__
    with (directory/"worker.json").open("x",encoding="utf-8") as output:json.dump(result,output,ensure_ascii=True,indent=2)
    return 0 if result["status"]=="PASS" else 1 if result["status"]=="FAIL" else 2

if __name__=="__main__":raise SystemExit(main())
