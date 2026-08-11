"""Bounded runtime logging and privacy-safe bug-report diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler
import platform
from pathlib import Path
import sys
import threading
import traceback
from typing import Callable

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import QStandardPaths, qVersion
from PySide6.QtWidgets import QApplication

from app.models.project import FORMAT_VERSION
from app.version import BUILD_COMMIT, PREVIEW_BUILD, PREVIEW_LABEL, get_display_name


LOGGER_NAME = "pixel_effect_maker"
LOG_FILE_NAME = "pixel_effect_maker.log"
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3


@dataclass(frozen=True)
class RuntimeDiagnosticsState:
    log_path: Path | None
    initialization_error: str = ""


_state = RuntimeDiagnosticsState(None)


def runtime_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def _default_log_directory() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not base:
        raise OSError("the OS did not provide an application data directory")
    return Path(base) / "logs"


def configure_runtime_logging(
    log_directory: str | Path | None = None,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> RuntimeDiagnosticsState:
    """Configure a bounded UTF-8 log; failure must never block startup."""
    global _state
    logger = runtime_logger()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        if getattr(handler, "_pem_runtime_handler", False):
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    try:
        directory = Path(log_directory) if log_directory is not None else _default_log_directory()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / LOG_FILE_NAME
        handler = RotatingFileHandler(
            path,
            maxBytes=max(1024, int(max_bytes)),
            backupCount=max(0, min(3, int(backup_count))),
            encoding="utf-8",
        )
        handler._pem_runtime_handler = True
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        _state = RuntimeDiagnosticsState(path)
    except Exception as exc:
        _state = RuntimeDiagnosticsState(None, f"{type(exc).__name__}: {exc}")
        try:
            print(f"Pixel Effect Maker logging initialization failed: {_state.initialization_error}", file=sys.stderr)
        except Exception:
            pass
    return _state


def diagnostics_state() -> RuntimeDiagnosticsState:
    return _state


def safe_path_label(path: str | Path | None) -> str:
    """Return only a filename for logs; never expose a full user path."""
    if path is None:
        return "<none>"
    try:
        return Path(path).name or "<unnamed>"
    except Exception:
        return "<invalid-path>"


def log_runtime_startup() -> None:
    runtime_logger().info(
        "startup app=%s preview=%s format=%s build_commit=%s python=%s pyside=%s qt=%s os=%s",
        get_display_name(),
        PREVIEW_BUILD,
        FORMAT_VERSION,
        BUILD_COMMIT or "unavailable",
        platform.python_version(),
        PYSIDE_VERSION,
        qVersion(),
        platform.platform(),
    )


def build_diagnostic_text() -> str:
    state = diagnostics_state()
    return "\n".join(
        (
            get_display_name(),
            f"Build Channel: {PREVIEW_LABEL if PREVIEW_BUILD else 'Production'}",
            f"Project Format: {FORMAT_VERSION}",
            f"Build Commit: {BUILD_COMMIT or 'Unavailable'}",
            f"OS: {platform.platform()}",
            f"Python Runtime: {platform.python_version()}",
            f"PySide6/Qt: {PYSIDE_VERSION} / {qVersion()}",
            f"Log Path: {state.log_path if state.log_path is not None else 'Unavailable'}",
        )
    )


def log_exception(operation: str, exc: BaseException) -> None:
    runtime_logger().error(
        "operation_failed operation=%s exception=%s message=%s",
        operation,
        type(exc).__name__,
        str(exc),
        exc_info=(type(exc), exc, exc.__traceback__),
    )


def install_exception_hooks(reporter: Callable[[str], None] | None = None) -> None:
    """Record uncaught main-thread and Python-thread exceptions centrally."""
    def main_hook(exc_type, exc, tb):
        runtime_logger().critical("unhandled_main_thread_exception", exc_info=(exc_type, exc, tb))
        if reporter is not None:
            try:
                reporter(f"{exc_type.__name__}: {exc}")
            except Exception:
                runtime_logger().exception("unhandled_exception_reporter_failed")

    def thread_hook(args):
        runtime_logger().critical(
            "unhandled_background_thread_exception thread=%s",
            getattr(args.thread, "name", "unknown"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = main_hook
    threading.excepthook = thread_hook


class DiagnosticApplication(QApplication):
    """Qt application boundary that records exceptions escaping event handlers."""

    def __init__(self, arguments) -> None:
        super().__init__(arguments)
        self._exception_reporter: Callable[[str], None] | None = None
        self._reporting_exception = False

    def set_exception_reporter(self, reporter: Callable[[str], None] | None) -> None:
        self._exception_reporter = reporter

    def notify(self, receiver, event) -> bool:
        try:
            return super().notify(receiver, event)
        except Exception as exc:
            runtime_logger().error(
                "unhandled_qt_event_exception receiver=%s event=%s\n%s",
                type(receiver).__name__,
                type(event).__name__,
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            )
            if self._exception_reporter is not None and not self._reporting_exception:
                self._reporting_exception = True
                try:
                    self._exception_reporter(f"{type(exc).__name__}: {exc}")
                except Exception:
                    runtime_logger().exception("qt_exception_reporter_failed")
                finally:
                    self._reporting_exception = False
            return False
