"""Own only the launched process tree; Windows Job closes kill descendants too."""
from collections import deque
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

class WindowsJob:
    def __init__(self):
        import ctypes
        from ctypes import wintypes as w
        self.c=ctypes;self.k=ctypes.WinDLL("kernel32",use_last_error=True)
        class Basic(ctypes.Structure):
            _fields_=[("process_time",ctypes.c_int64),("job_time",ctypes.c_int64),("flags",w.DWORD),("min_work",ctypes.c_size_t),("max_work",ctypes.c_size_t),("active",w.DWORD),("affinity",ctypes.c_size_t),("priority",w.DWORD),("scheduling",w.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_uint64) for name in ("read_ops","write_ops","other_ops","read_bytes","write_bytes","other_bytes")]
        class Extended(ctypes.Structure):
            _fields_=[("basic",Basic),("io",IO),("process_mem",ctypes.c_size_t),("job_mem",ctypes.c_size_t),("peak_process",ctypes.c_size_t),("peak_job",ctypes.c_size_t)]
        self.k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];self.k.CreateJobObjectW.restype=w.HANDLE
        self.k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        self.k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        self.k.CloseHandle.argtypes=[w.HANDLE]
        self.handle=self.k.CreateJobObjectW(None,None)
        if not self.handle:raise OSError("Cannot create diagnostic process job")
        info=Extended();info.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.k.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            self.close();raise OSError("Cannot configure diagnostic process cleanup")
    def assign(self,process):
        if not self.k.AssignProcessToJobObject(self.handle,int(process._handle)):
            raise OSError("Cannot contain diagnostic process tree")
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None

@dataclass
class ProcessResult:
    returncode: int
    timed_out: bool
    tail: str
    elapsed_seconds: float
    cleanup: str

def run_process(command, *, cwd, env, timeout, ready_file=None):
    started=time.monotonic();job=None;process=None;reader=None;chunks=deque(maxlen=8)
    def drain(stream):
        try:
            while data:=stream.read(8192):chunks.append(data)
        except (OSError,ValueError):pass
    def terminate_tree():
        if job is not None:job.close()
        elif process is not None:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        if process is not None and process.poll() is None:process.kill()
    try:
        if os.name=="nt":job=WindowsJob()
        process=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0,start_new_session=os.name!="nt")
        if job is not None:job.assign(process)
        # Worker waits for this barrier before importing pytest/Qt or spawning.
        if ready_file is not None:Path(ready_file).touch(exist_ok=False)
        reader=threading.Thread(target=drain,args=(process.stdout,),daemon=True);reader.start()
        timed_out=False
        try:process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;terminate_tree();process.wait(timeout=5)
        terminate_tree()  # Also remove a descendant left behind after normal exit.
        reader.join(timeout=3)
        return ProcessResult(process.returncode,timed_out,b"".join(chunks).decode("utf-8",errors="replace"),time.monotonic()-started,"owned process tree closed")
    finally:
        if process is not None:
            terminate_tree()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            if reader is not None:reader.join(timeout=3)
            if process.stdout is not None:process.stdout.close()
        if job is not None:job.close()
