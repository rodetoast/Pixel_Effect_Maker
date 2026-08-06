"""Version-aware JSON project persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from app.models.project import Project, ProjectError


class ProjectIOError(RuntimeError):
    """Raised when a project cannot be saved or loaded."""

    def __init__(self,message: str,code: str="project_io"):
        super().__init__(message);self.code=code


class SavePerformanceCollector:
    """Optional test/diagnostic timings; normal saves do not print them."""

    def __init__(self):self.calls={};self.total_ms={};self.maximum_ms={};self.output_bytes=0
    def record(self,name,started):
        elapsed=(perf_counter()-started)*1000.0;self.calls[name]=self.calls.get(name,0)+1
        self.total_ms[name]=self.total_ms.get(name,0.0)+elapsed;self.maximum_ms[name]=max(self.maximum_ms.get(name,0.0),elapsed)
    def average(self,name):return self.total_ms.get(name,0.0)/max(1,self.calls.get(name,0))


def save_project(project: Project, path: str | Path, collector: SavePerformanceCollector|None=None) -> Path:
    """Atomically save a project as UTF-8 JSON."""
    destination = Path(path)
    if not destination.name.endswith(".peffect.json"):
        destination = destination.with_name(destination.name + ".peffect.json")
    profile=collector or SavePerformanceCollector();temp_path=None;stage="directory"
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage="serialize"
        started=perf_counter();data=project.to_dict();profile.record("project_to_dict",started)
        started=perf_counter();text=json.dumps(data,ensure_ascii=False,separators=(",",":"));profile.record("json_dumps",started)
        started=perf_counter();encoded=text.encode("utf-8");profile.record("utf8_encode",started);profile.output_bytes=len(encoded)
        stage="temporary"
        with NamedTemporaryFile(
            "wb", dir=destination.parent, delete=False, suffix=".tmp"
        ) as temporary:
            temp_path=Path(temporary.name)
            started=perf_counter();temporary.write(encoded);profile.record("temporary_write",started)
            started=perf_counter();temporary.flush();profile.record("flush",started)
            started=perf_counter();os.fsync(temporary.fileno());profile.record("fsync",started)
        stage="replace";started=perf_counter();os.replace(temp_path,destination);profile.record("atomic_replace",started)
    except (OSError, TypeError, ValueError) as exc:
        try:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        code={"directory":"save_directory","serialize":"save_serialize","temporary":"save_temporary","replace":"save_replace"}.get(stage,"save_failed")
        raise ProjectIOError(f"could not save project: {exc}",code) from exc
    return destination


def load_project(path: str | Path) -> Project:
    """Load and validate a project JSON file."""
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return Project.from_dict(data)
    except (OSError, json.JSONDecodeError, ProjectError) as exc:
        code="load_payload" if "pixel payload" in str(exc) else "load_failed"
        raise ProjectIOError(f"could not load project: {exc}",code) from exc
