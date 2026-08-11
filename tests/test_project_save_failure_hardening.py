from pathlib import Path

import pytest

from app.models.project import Project
from app.services import project_io
from app.services.project_io import ProjectIOError, save_project


@pytest.mark.parametrize("failure", [OSError("I/O error"), PermissionError("denied")])
def test_fsync_failure_preserves_existing_project(tmp_path, monkeypatch, failure):
    target = tmp_path / "existing.peffect.json"
    target.write_bytes(b"known-good")
    monkeypatch.setattr(project_io.os, "fsync", lambda descriptor: (_ for _ in ()).throw(failure))
    with pytest.raises(ProjectIOError) as caught:
        save_project(Project.create_default(), target)
    assert caught.value.code == "save_temporary"
    assert target.read_bytes() == b"known-good"
    assert list(tmp_path.glob("*.tmp")) == []


def test_serialization_failure_does_not_create_destination(tmp_path, monkeypatch):
    target = tmp_path / "new.peffect.json"
    monkeypatch.setattr(project_io.json, "dumps", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad model")))
    with pytest.raises(ProjectIOError) as caught:
        save_project(Project.create_default(), target)
    assert caught.value.code == "save_serialize"
    assert not target.exists()


def test_non_finite_model_value_is_not_serialized(tmp_path):
    project = Project.create_default()
    project.name = float("nan")
    with pytest.raises(ProjectIOError) as caught:
        save_project(project, tmp_path / "nonfinite.peffect.json")
    assert caught.value.code == "save_serialize"
