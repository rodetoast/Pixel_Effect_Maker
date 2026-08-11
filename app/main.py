"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from app.version import APP_NAME, get_display_name


def preview_notice_enabled_for_arguments(arguments: list[str]) -> bool:
    """Diagnostics never enter the modal Preview startup flow."""
    return "--version" not in arguments and "--check" not in arguments


def confirm_preview_start(window) -> bool:
    """Show the current Preview notice when this build/revision requires it."""
    from PySide6.QtWidgets import QDialog

    from app.ui.preview_build_notice_dialog import PreviewBuildNoticeDialog, should_show_preview_notice

    settings = window.settings_service.settings
    from app.services.runtime_diagnostics import runtime_logger

    if not should_show_preview_notice(settings):
        runtime_logger().info("preview_notice skipped=previously_accepted")
        return True
    dialog = PreviewBuildNoticeDialog(window.localization, settings)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    runtime_logger().info("preview_notice result=%s", "accepted" if accepted else "rejected")
    return accepted


def prepare_normal_startup(
    window,
    arguments: list[str],
    *,
    notice_runner=None,
    startup_factory=None,
    project_loader=None,
    error_handler=None,
) -> bool:
    """Run Preview acceptance before project loading or the Startup dialog."""
    from PySide6.QtWidgets import QDialog

    from PySide6.QtWidgets import QMessageBox

    from app.services.project_io import ProjectIOError, load_project
    from app.services.runtime_diagnostics import log_exception, runtime_logger, safe_path_label
    from app.ui.startup_dialog import StartupDialog

    runner = notice_runner or confirm_preview_start
    if not runner(window):
        return False
    project_paths = [value for value in arguments if not value.startswith("-")]
    if project_paths:
        loader = project_loader or load_project
        project_path = Path(project_paths[0])
        runtime_logger().info("open_project start source=%s", safe_path_label(project_path))
        try:
            loaded = loader(project_path)
        except (ProjectIOError, OSError, ValueError) as exc:
            log_exception("startup_open_project", exc)
            if error_handler is not None:
                error_handler(exc)
            else:
                code = getattr(exc, "code", "")
                key = {
                    "load_payload": "error.load_payload",
                    "load_future_format": "error.load_future_format",
                }.get(code, "error.load_failed_body")
                QMessageBox.critical(
                    window,
                    window.localization.text("error.open"),
                    window.localization.text(key, reason=str(exc)),
                )
            return False
        window.project = loaded
        window.project_path = project_path
        window._refresh_all()
        runtime_logger().info("open_project success source=%s", safe_path_label(project_path))
        return True
    factory = startup_factory or StartupDialog
    startup = factory(None, window.localization)
    if startup.exec() != QDialog.DialogCode.Accepted:
        return False
    if startup.opened_project is not None:
        window.project = startup.opened_project
        window.project_path = startup.opened_path
        window._refresh_all()
    else:
        window.apply_new_project_settings(startup.settings())
    return True


def main(argv: list[str] | None = None) -> int:
    """Handle lightweight CLI options, then create and run the Qt application."""
    arguments = sys.argv[1:] if argv is None else argv
    if "--version" in arguments:
        print(get_display_name())
        return 0

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox

    from app.ui.main_window import MainWindow
    from app.services.runtime_diagnostics import (
        DiagnosticApplication,
        configure_runtime_logging,
        install_exception_hooks,
        log_runtime_startup,
        runtime_logger,
    )

    application = DiagnosticApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("SOUTHPAW GAMES")
    state = configure_runtime_logging()
    install_exception_hooks()
    log_runtime_startup()
    if state.initialization_error:
        runtime_logger().warning("logging_unavailable reason=%s", state.initialization_error)
    if "--check" in arguments:
        window = MainWindow()
        window.show()
        QTimer.singleShot(0, application.quit)
        return application.exec()
    window = MainWindow()
    def report_unhandled(reason: str) -> None:
        QMessageBox.critical(
            window,
            window.localization.text("error.unhandled"),
            window.localization.text("error.unhandled_body", reason=reason),
        )
    application.set_exception_reporter(report_unhandled)
    install_exception_hooks(report_unhandled)
    if preview_notice_enabled_for_arguments(arguments) and not prepare_normal_startup(window, arguments):
        window.deleteLater()
        return 0
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
