"""Tests for application and project-format version separation."""

from app import __version__
from app.main import main
from app.models.project import FORMAT_VERSION, Project
from app.version import get_display_name


def test_application_version() -> None:
    assert __version__ == "0.0.04"


def test_display_name() -> None:
    assert get_display_name() == "Pixel Effect Maker v0.0.04"


def test_project_format_version_is_six_for_resource_layers() -> None:
    assert FORMAT_VERSION == 6
    assert Project.create_default().to_dict()["format_version"] == 6


def test_version_cli_does_not_start_gui(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == "Pixel Effect Maker v0.0.04\n"
