"""DevEx orchestration contracts; production rendering assertions are reused."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import pytest
from tools import diagnose_editor as cli
from tools.diagnostics.registry import REGISTRY,select_checks
from tools.diagnostics.process import ProcessResult,run_process
from tools.diagnostics.worker import Reporter

def test_registry_is_bounded_existing_tests_and_tools_not_in_core():
    assert list(REGISTRY)==["ui","rotation","groups","render"]
    assert len(select_checks(["all"]))==4
    assert len(select_checks(["groups","groups"]))==1
    for check in REGISTRY.values():
        assert check.tests and check.timeout>0 and check.conditions
        for node in check.tests:assert (cli.ROOT/node.split("::")[0]).is_file()
    with pytest.raises(ValueError):select_checks(["all","ui"])
    with pytest.raises(ValueError):select_checks(["unknown"])

def test_list_starts_no_qt_or_child(tmp_path):
    code="import sys;from tools.diagnose_editor import main;assert main(['--list'])==0;assert 'PySide6.QtWidgets' not in sys.modules;assert 'pytest' not in sys.modules"
    result=run_process([sys.executable,"-c",code],cwd=cli.ROOT,env=cli.private_environment(tmp_path),timeout=15)
    assert result.returncode==0 and "Rotation" in result.tail

@pytest.mark.parametrize("states,code",[(('PASS',),0),(('FAIL',),1),(('SKIP',),2),(('ERROR',),2),(('FAIL','ERROR'),2)])
def test_exit_mapping_preserves_skips_and_errors(states,code):
    assert cli.exit_code([dict(status=state) for state in states])==code

@pytest.mark.parametrize("destination",["root","inside","ancestor","existing","symlink"])
def test_output_protection(tmp_path,destination):
    if destination=="root":path=cli.ROOT
    elif destination=="inside":path=cli.ROOT/"never-created-diagnostic-output"
    elif destination=="ancestor":path=cli.ROOT.parent
    elif destination=="existing":path=tmp_path
    else:
        path=tmp_path/"link"
        try:path.symlink_to(cli.ROOT,target_is_directory=True)
        except OSError:pytest.skip("This account cannot create symlinks")
    with pytest.raises((ValueError,OSError)):cli.fresh_output(path)

def fake_runner(status="PASS",code=0,timeout=False,valid=True):
    def run(command,**kwargs):
        folder=Path(kwargs["ready_file"]).parent
        if valid:
            (folder/"worker.json").write_text(json.dumps(dict(status=status,tests=[dict(test="synthetic[ko-280]",status=status)],reason="fixture result",evidence=[])),encoding="utf-8")
        return ProcessResult(code,timeout,"private C:\\private\\secret.peffect.json",.01,"owned process tree closed")
    return run

@pytest.mark.parametrize("status,code",[("PASS",0),("FAIL",1),("SKIP",2),("ERROR",2)])
def test_check_adapter_valid_json_and_outcome(tmp_path,status,code):
    result=cli.run_check(REGISTRY["groups"],tmp_path,1,runner=fake_runner(status,code))
    assert result["status"]==status and result["child_exit_code"]==code
    assert json.loads((tmp_path/"groups"/"result.json").read_text())["name"]=="groups"
    assert not (tmp_path/"groups"/"worker.json").exists()
    assert "private" not in json.dumps(result)

def test_timeout_is_error_not_assertion_failure(tmp_path):
    result=cli.run_check(REGISTRY["ui"],tmp_path,1,runner=fake_runner(code=-9,timeout=True,valid=False))
    assert result["status"]=="ERROR" and "timeout" in result["reason"]

def test_worker_missing_and_exit_mismatch_are_errors(tmp_path):
    first=tmp_path/"a";first.mkdir()
    assert cli.run_check(REGISTRY["ui"],first,1,runner=fake_runner(valid=False))["status"]=="ERROR"
    second=tmp_path/"b";second.mkdir()
    assert cli.run_check(REGISTRY["ui"],second,1,runner=fake_runner(code=1))["status"]=="ERROR"

@pytest.mark.parametrize("content",["not json",'{"status":"PASS","tests":[]}', '{"status":"PASS","tests":[{"status":"SKIP"}]}'])
def test_malformed_empty_or_skip_cannot_claim_pass(tmp_path,content):
    def run(command,**kwargs):
        (Path(kwargs["ready_file"]).parent/"worker.json").write_text(content,encoding="utf-8")
        return ProcessResult(0,False,"",.01,"closed")
    assert cli.run_check(REGISTRY["ui"],tmp_path,1,runner=run)["status"]=="ERROR"

def test_exception_reporting_does_not_leak_exception_payload(tmp_path):
    def fail(*a,**k):raise RuntimeError("private C:\\private\\payload.peffect.json token-secret")
    result=cli.run_check(REGISTRY["render"],tmp_path,1,runner=fail)
    assert result["status"]=="ERROR" and result["reason"].endswith("RuntimeError")
    assert "token-secret" not in json.dumps(result)

def test_opt_in_trace_redaction_and_options(tmp_path):
    seen=[]
    def runner(command,**kwargs):
        seen.extend(command);return fake_runner()(command,**kwargs)
    result=cli.run_check(REGISTRY["rotation"],tmp_path,1,trace=True,screenshots=True,runner=runner)
    assert "--trace" in seen and "--screenshots" in seen
    assert "child_output_tail" not in result and result["child_output_captured_chars"]>0
    assert cli.redact("C:\\private\\secret.json",tmp_path)=="<path>"

def test_private_environment_is_process_local(tmp_path,monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_COUNT","1");monkeypatch.setenv("GIT_CONFIG_KEY_0","test.key");monkeypatch.setenv("GIT_CONFIG_VALUE_0","value")
    before=dict(os.environ);env=cli.private_environment(tmp_path)
    assert dict(os.environ)==before
    assert env["QT_QPA_PLATFORM"]=="offscreen" and env["GIT_CONFIG_COUNT"]=="2"
    assert env["GIT_CONFIG_KEY_1"]=="safe.directory" and env["GIT_CONFIG_KEY_0"]=="test.key"
    assert all(str(tmp_path) in env[key] for key in ("APPDATA","LOCALAPPDATA","TEMP"))

def test_reporter_teardown_failure_and_skip_are_not_pass():
    reporter=Reporter()
    report=lambda **k:SimpleNamespace(nodeid="synthetic[ko-280]",duration=.01,failed=False,skipped=False,**k)
    reporter.pytest_runtest_logreport(report())
    failed=report();failed.failed=True
    reporter.pytest_runtest_logreport(failed)
    skipped=report();skipped.skipped=True
    reporter.pytest_runtest_logreport(skipped)
    assert reporter.items["synthetic[ko-280]"]["status"]=="FAIL"

def test_trace_does_not_persist_longrepr_or_payload():
    reporter=Reporter(trace=True)
    crash=SimpleNamespace(path="tests/synthetic.py",lineno=12)
    report=SimpleNamespace(nodeid="synthetic[ko-280]",duration=.1,failed=True,skipped=False,when="call",longrepr=SimpleNamespace(reprcrash=crash),longreprtext="layer_pixels PRIVATE PAYLOAD TOKEN")
    reporter.pytest_runtest_logreport(report)
    text=json.dumps(reporter.items)
    assert "PAYLOAD" not in text and "TOKEN" not in text and "layer_pixels" not in text
    assert reporter.items[report.nodeid]["failure_location"]["line"]==12

def test_gizmo_observations_are_allowlisted_on_failure_without_project_payload():
    reporter=Reporter()
    state=dict(stage="awaiting_callback",transient_changed=True,signal_count=19,refresh_requested=True,timer_starts=1,callback_count=0,pending=True,timer_active=True,layer_pixels="PRIVATE",project_path="C:/private/project.json",value_matches={"secret":"payload"})
    report=SimpleNamespace(nodeid="sync",duration=.1,failed=True,skipped=False,user_properties=[("gizmo_sync",state)])
    reporter.pytest_runtest_logreport(report)
    saved=reporter.items["sync"]["observations"]["gizmo_sync"]
    assert saved["stage"]=="awaiting_callback" and saved["signal_count"]==19 and saved["callback_count"]==0
    assert "PRIVATE" not in json.dumps(saved) and "project_path" not in saved and "value_matches" not in saved
    assert reporter.items["sync"]["status"]=="FAIL"

def _alive(pid):
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x100000,False,pid)
        if not handle:return False
        try:return kernel.WaitForSingleObject(handle,0)==258
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False

@pytest.mark.parametrize("timeout",[True,False])
def test_owned_descendant_cleanup_on_timeout_and_normal_exit(tmp_path,timeout):
    barrier=tmp_path/"ready";pidfile=tmp_path/"child.pid"
    child="import time;time.sleep(30)"
    script=f"import subprocess,sys,time;from pathlib import Path\nwhile not Path({str(barrier)!r}).exists():time.sleep(.01)\np=subprocess.Popen([sys.executable,'-c',{child!r}]);Path({str(pidfile)!r}).write_text(str(p.pid));time.sleep({30 if timeout else .2})"
    result=run_process([sys.executable,"-c",script],cwd=cli.ROOT,env=cli.private_environment(tmp_path),timeout=1 if timeout else 10,ready_file=barrier)
    assert result.timed_out==timeout and pidfile.is_file()
    pid=int(pidfile.read_text());deadline=time.monotonic()+3
    while _alive(pid) and time.monotonic()<deadline:time.sleep(.02)
    assert not _alive(pid)

def test_subprocess_tail_is_bounded(tmp_path):
    result=run_process([sys.executable,"-c","print('x'*1000000)"],cwd=cli.ROOT,env=cli.private_environment(tmp_path),timeout=10)
    assert result.returncode==0 and len(result.tail)<=65536

def test_main_selective_report_schema(tmp_path,monkeypatch):
    called=[]
    def run(check,*a,**k):called.append(check.name);return dict(name=check.name,status="PASS",duration_seconds=.1)
    monkeypatch.setattr(cli,"run_check",run)
    output=tmp_path/"out"
    assert cli.main(["--check","groups","--output",str(output)])==0 and called==["groups"]
    data=json.loads((output/"report.json").read_text())
    assert data["schema_version"]==1 and data["app_version"]=="0.0.25" and data["format_version"]==22
    assert data["summary"]["PASS"]==1

@pytest.mark.parametrize("value",["0","-1","nan","inf"])
def test_invalid_timeout(value):
    with pytest.raises(SystemExit) as error:cli.main(["--timeout",value])
    assert error.value.code==2

def test_worker_group_integration_trace_is_metadata_only(tmp_path):
    output=tmp_path/"integration";output.mkdir()
    result=cli.run_check(REGISTRY["groups"],output,60,trace=True)
    assert result["status"]=="PASS",result
    assert result["tests"] and any(e["event"]=="selection_changed" for e in result["trace"])
    text=json.dumps(result["trace"])
    assert all(x not in text for x in ("layer_pixels","resource_composition_id","C:\\","username"))
