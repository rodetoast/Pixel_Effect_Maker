import logging
from pathlib import Path

from app.models.project import FORMAT_VERSION
from app.services import runtime_diagnostics as diagnostics


def _flush_runtime_handlers():
    for handler in diagnostics.runtime_logger().handlers:
        handler.flush()


def test_logging_failure_does_not_block_startup(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("log directory unavailable")

    monkeypatch.setattr(diagnostics, "RotatingFileHandler", fail)
    state = diagnostics.configure_runtime_logging(tmp_path)
    assert state.log_path is None
    assert "OSError" in state.initialization_error


def test_log_rotation_is_bounded(tmp_path):
    state = diagnostics.configure_runtime_logging(tmp_path, max_bytes=1024, backup_count=3)
    for index in range(80):
        diagnostics.runtime_logger().info("event=%s %s", index, "x" * 200)
    _flush_runtime_handlers()
    files = list(tmp_path.glob("pixel_effect_maker.log*"))
    assert state.log_path == tmp_path / "pixel_effect_maker.log"
    assert 1 <= len(files) <= 4


def test_uncaught_exception_is_logged(tmp_path, monkeypatch):
    diagnostics.configure_runtime_logging(tmp_path)
    monkeypatch.setattr(diagnostics.sys, "excepthook", diagnostics.sys.excepthook)
    diagnostics.install_exception_hooks()
    try:
        raise RuntimeError("diagnostic sentinel")
    except RuntimeError as exc:
        diagnostics.sys.excepthook(type(exc), exc, exc.__traceback__)
    _flush_runtime_handlers()
    assert "diagnostic sentinel" in (tmp_path / diagnostics.LOG_FILE_NAME).read_text("utf-8")


def test_diagnostics_text_is_versioned_and_contains_no_project_payload(tmp_path):
    diagnostics.configure_runtime_logging(tmp_path)
    text = diagnostics.build_diagnostic_text()
    assert "Pixel Effect Maker v0.0.21" in text
    assert f"Project Format: {FORMAT_VERSION}" in text
    assert "Build Channel: Early Preview" in text
    assert "layer_pixels" not in text and "rgba8-zlib-base64" not in text


def test_safe_path_label_omits_parent_directories():
    value = diagnostics.safe_path_label(Path("C:/private/account/project.peffect.json"))
    assert value == "project.peffect.json"
    assert "private" not in value
