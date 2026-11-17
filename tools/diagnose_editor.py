"""Isolated console diagnostics. --list is cheap and starts neither Qt nor pytest."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.diagnostics.registry import REGISTRY,TOOLS,select_checks
from tools.diagnostics.process import run_process

SCHEMA_VERSION=1

def fresh_output(value=None):
    if value is None:
        output=Path(tempfile.mkdtemp(prefix="pem-diagnostics-"))
        if output.is_relative_to(ROOT):raise ValueError("Temporary directory must be outside repository")
        return output
    output=Path(value).expanduser().resolve()
    if output==ROOT or output.is_relative_to(ROOT) or ROOT.is_relative_to(output):raise ValueError("Output must be a NEW directory outside repository and its ancestors")
    output.mkdir(parents=True,exist_ok=False)
    return output

def private_environment(directory):
    env=dict(os.environ)
    for name in ("APPDATA","LOCALAPPDATA","XDG_CONFIG_HOME","XDG_CACHE_HOME","TEMP","TMP","TMPDIR"):
        target=directory/name.lower();target.mkdir(exist_ok=True);env[name]=str(target)
    env.update(QT_QPA_PLATFORM="offscreen",PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("PYTEST_ADDOPTS",None);env.pop("PYTEST_PLUGINS",None)
    count=int(env.get("GIT_CONFIG_COUNT","0"))
    env[f"GIT_CONFIG_KEY_{count}"]="safe.directory";env[f"GIT_CONFIG_VALUE_{count}"]=ROOT.as_posix();env["GIT_CONFIG_COUNT"]=str(count+1)
    return env

def redact(value,output):
    """Trace is opt-in but never needs usernames, absolute source/temp paths."""
    if isinstance(value,dict):return {k:redact(v,output) for k,v in value.items()}
    if isinstance(value,list):return [redact(v,output) for v in value]
    if not isinstance(value,str):return value
    for path,label in ((ROOT,"<repo>"),(output,"<diagnostics>"),(Path.home(),"<home>")):
        value=re.sub(re.escape(str(path)),lambda _:label,value,flags=re.IGNORECASE)
        value=re.sub(re.escape(path.as_posix()),lambda _:label,value,flags=re.IGNORECASE)
    value=re.sub(r"[A-Za-z]:[\\/][^\s\"'<>]+","<path>",value)
    # Avoid persisting arbitrary exception/payload repr by default (worker
    # reports generic reasons); this sanitizes optional trace details further.
    return value

def exit_code(results):
    if any(r["status"] in {"ERROR","SKIP"} for r in results):return 2
    return 1 if any(r["status"]=="FAIL" for r in results) else 0

def run_check(check,output,timeout,trace=False,screenshots=False,runner=run_process):
    directory=output/check.name;directory.mkdir(exist_ok=False)
    result=dict(name=check.name,title=check.title,check_version=check.version,status="ERROR",reason="",conditions=list(check.conditions),related_tests=list(check.tests),evidence=[],duration_seconds=0.0)
    try:
        command=[sys.executable,"-m","tools.diagnostics.worker","--name",check.name,"--run-dir",str(directory)]
        if trace:command.append("--trace")
        if screenshots:command.append("--screenshots")
        process=runner(command,cwd=ROOT,env=private_environment(directory),timeout=timeout or check.timeout,ready_file=directory/"ready")
        result.update(duration_seconds=round(process.elapsed_seconds,6),child_exit_code=process.returncode,cleanup=process.cleanup)
        if process.timed_out:result["reason"]="Diagnostic timeout; owned child process tree closed"
        elif not (directory/"worker.json").is_file():result["reason"]="Worker exited without a valid report"
        else:
            data=json.loads((directory/"worker.json").read_text("utf-8"))
            if data.get("status") not in {"PASS","FAIL","SKIP","ERROR"} or not isinstance(data.get("tests"),list):raise ValueError("Invalid worker schema")
            if data["status"]=="PASS" and (not data["tests"] or any(t.get("status")!="PASS" for t in data["tests"])):raise ValueError("Empty/skipped result cannot PASS")
            expected=0 if data["status"]=="PASS" else 1 if data["status"]=="FAIL" else 2
            if process.returncode!=expected:raise ValueError("Worker exit/report mismatch")
            for evidence in data.get("evidence",[]):
                target=(directory/evidence).resolve()
                if not target.is_relative_to(directory.resolve()) or not target.is_file():raise ValueError("Invalid evidence path")
            result.update(data)
            result["evidence"]=[f"{check.name}/{p}" for p in data.get("evidence",[])]
        if trace:result["child_output_captured_chars"]=len(process.tail)
    except (Exception,KeyboardInterrupt) as exc:
        result.update(status="ERROR",reason=f"Diagnostic execution error: {type(exc).__name__}")
    result=redact(result,output)
    # Never leave unsanitized optional traces in the private raw worker report.
    raw=directory/"worker.json"
    if raw.exists():raw.unlink()  # only this run's generated intermediate file
    with (directory/"result.json").open("x",encoding="utf-8") as handle:json.dump(result,handle,indent=2,ensure_ascii=True)
    return result

def run_tool(name,output,timeout,trace=False):
    directory=output/name;directory.mkdir(exist_ok=False)
    script,purpose=TOOLS[name]
    result=dict(name=name,title=purpose,check_version=1,status="ERROR",reason="",conditions=["Explicit opt-in tool; not a core UI quality verdict"],related_tests=[],evidence=[],duration_seconds=0)
    try:
        process=run_process([sys.executable,str(ROOT/script),"--output",str(directory/"artifacts")],cwd=ROOT,env=private_environment(directory),timeout=timeout or 300)
        result.update(status="ERROR" if process.timed_out or process.returncode else "PASS",reason="Tool execution completed; inspect observations, not a visual quality approval" if not process.returncode else "Tool failed or timed out",child_exit_code=process.returncode,cleanup=process.cleanup,duration_seconds=round(process.elapsed_seconds,6))
        result["evidence"]=[str(p.relative_to(output)).replace("\\","/") for p in (directory/"artifacts").glob("*.json")]
        if trace:result["child_output_captured_chars"]=len(process.tail)
    except Exception as exc:result["reason"]=f"Tool execution error: {type(exc).__name__}"
    return redact(result,output)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list",action="store_true");parser.add_argument("--check",action="append",choices=[*REGISTRY,"all"])
    parser.add_argument("--tool",choices=list(TOOLS),help="Explicit extended legacy adapter; excluded from all")
    parser.add_argument("--output",type=Path);parser.add_argument("--timeout",type=float,help="Seconds per diagnostic")
    parser.add_argument("--trace",action="store_true",help="Opt-in bounded metadata trace and sanitized failure detail")
    parser.add_argument("--screenshots",action="store_true",help="Optional UI probe evidence only")
    args=parser.parse_args(argv)
    if args.list:
        for check in REGISTRY.values():print(f"{check.name}: {check.title} - {check.purpose} (v{check.version}; timeout {check.timeout:g}s)")
        for name,(_,purpose) in TOOLS.items():print(f"--tool {name}: {purpose} [explicit; excluded from all]")
        return 0
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout<=0):parser.error("timeout must be finite and positive")
    if args.tool and args.check:parser.error("Use --tool or --check, not both")
    try:
        checks=select_checks(args.check)
        output=fresh_output(args.output)
    except (ValueError,OSError) as exc:
        print(f"Diagnostics setup error: {type(exc).__name__}; use a fresh outside-repo directory",file=sys.stderr);return 2
    try:
        from app.version import __version__
        from app.models.project import FORMAT_VERSION
    except ImportError:
        error=dict(schema_version=SCHEMA_VERSION,app_version="unavailable",format_version=None,checks=[dict(name="prerequisites",status="ERROR",reason="Required application dependency unavailable")],exit_code=2)
        with (output/"report.json").open("x",encoding="utf-8") as handle:json.dump(error,handle,indent=2)
        print("[ERROR] Application prerequisites unavailable",file=sys.stderr);return 2
    report=dict(schema_version=SCHEMA_VERSION,app_version=__version__,format_version=FORMAT_VERSION,started_utc=datetime.now(timezone.utc).isoformat(),runtime=dict(python=platform.python_version(),os=platform.system(),qt_platform="offscreen",trace=args.trace,screenshots=args.screenshots,synthetic_only=True),checks=[])
    print("Pixel Effect Maker Diagnostics",flush=True)
    try:
        if args.tool:report["checks"].append(run_tool(args.tool,output,args.timeout,args.trace))
        else:
            for check in checks:
                item=run_check(check,output,args.timeout,args.trace,args.screenshots)
                report["checks"].append(item);print(f"[{item['status']}] {check.title} ({item['duration_seconds']:.2f}s)",flush=True)
    except (Exception,KeyboardInterrupt) as exc:report["checks"].append(dict(name="runner",status="ERROR",reason=type(exc).__name__))
    report["exit_code"]=exit_code(report["checks"])
    report["summary"]={state:sum(c["status"]==state for c in report["checks"]) for state in ("PASS","FAIL","SKIP","ERROR")}
    with (output/"report.json").open("x",encoding="utf-8") as handle:json.dump(report,handle,indent=2,ensure_ascii=True)
    print("Summary: "+", ".join(f"{count} {state.lower()}" for state,count in report["summary"].items()))
    print(f"JSON: {output / 'report.json'}")
    return report["exit_code"]

if __name__=="__main__":raise SystemExit(main())
