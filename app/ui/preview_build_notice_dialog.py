"""Early Preview notice and reusable project overview dialog."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.models.project import FORMAT_VERSION
from app.services.localization_service import LocalizationService
from app.services.runtime_diagnostics import log_exception
from app.version import PREVIEW_BUILD, PREVIEW_LABEL, PREVIEW_NOTICE_REVISION, VERSION_LABEL, __version__, get_display_name


def preview_notice_settings_key(
    version: str = __version__,
    format_version: int = FORMAT_VERSION,
    revision: int = PREVIEW_NOTICE_REVISION,
) -> str:
    """Return the acceptance key scoped to this exact preview contract."""
    return f"preview_notice/accepted/{version}-format{format_version}-revision{revision}"


def preview_notice_was_accepted(settings: QSettings) -> bool:
    """Fail safely toward showing the notice when settings cannot be read."""
    try:
        value = settings.value(preview_notice_settings_key(), False)
    except Exception as exc:
        log_exception("preview_notice_settings_read",exc)
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def should_show_preview_notice(settings: QSettings) -> bool:
    return PREVIEW_BUILD and not preview_notice_was_accepted(settings)


class PreviewBuildNoticeDialog(QDialog):
    """Scrollable localized Preview notice used at startup and from Help."""

    def __init__(
        self,
        localization: LocalizationService,
        settings: QSettings,
        parent: QWidget | None = None,
        *,
        manual_open: bool = False,
    ) -> None:
        super().__init__(parent)
        self.localization = localization
        self.settings = settings
        self.manual_open = manual_open
        self.setModal(True)
        self.setMinimumSize(560, 480)
        self._build_ui()
        self.localization.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._fit_available_screen()

    def _fit_available_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        width = min(680, max(560, available.width() - 48)) if available else 680
        height = min(620, max(480, available.height() - 48)) if available else 620
        self.resize(width, height)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        heading_row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning).pixmap(40, 40))
        icon.setAccessibleName("Preview build warning")
        heading_row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        heading_column = QVBoxLayout()
        self.title_label = QLabel()
        title_font = self.title_label.font(); title_font.setBold(True); title_font.setPointSize(title_font.pointSize() + 3)
        self.title_label.setFont(title_font); self.title_label.setWordWrap(True); self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.badge_label = QLabel(); self.badge_label.setObjectName("previewBuildBadge")
        self.badge_label.setStyleSheet("QLabel#previewBuildBadge { font-weight: 600; padding: 4px 8px; border: 1px solid palette(mid); border-radius: 4px; }")
        heading_column.addWidget(self.title_label); heading_column.addWidget(self.badge_label, 0, Qt.AlignmentFlag.AlignLeft)
        heading_row.addLayout(heading_column, 1); root.addLayout(heading_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(2, 2, 10, 2); self.content_layout.setSpacing(14)
        self.sections: list[tuple[QLabel, QLabel, str, str, bool]] = []
        self._add_section("preview.warning_heading", "preview.warning_body")
        self._add_section("preview.purpose_heading", "preview.purpose_body")
        self._add_section("preview.current_heading", "preview.current_items", bullets=True)
        self._add_section("preview.future_heading", "preview.future_items", bullets=True)
        self.build_info_label = self._body_label(); self.content_layout.addWidget(self.build_info_label)
        self.footer_label = self._body_label(); self.content_layout.addWidget(self.footer_label)
        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget); root.addWidget(self.scroll_area, 1)

        self.do_not_show_check = QCheckBox()
        self.do_not_show_check.setVisible(not self.manual_open)
        root.addWidget(self.do_not_show_check)
        self.button_box = QDialogButtonBox()
        if self.manual_open:
            self.close_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Close)
            self.close_button.clicked.connect(self.accept)
            self.exit_button = None; self.accept_button = None
        else:
            self.exit_button = QPushButton(); self.accept_button = QPushButton()
            self.button_box.addButton(self.exit_button, QDialogButtonBox.ButtonRole.RejectRole)
            self.button_box.addButton(self.accept_button, QDialogButtonBox.ButtonRole.AcceptRole)
            self.exit_button.clicked.connect(self.reject); self.accept_button.clicked.connect(self._accept_startup)
            self.accept_button.setDefault(True); self.accept_button.setAutoDefault(True)
        root.addWidget(self.button_box)

    def _body_label(self) -> QLabel:
        label = QLabel(); label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return label

    def _add_section(self, heading_key: str, body_key: str, *, bullets: bool = False) -> None:
        heading = QLabel(); font = heading.font(); font.setBold(True); font.setPointSize(font.pointSize() + 1); heading.setFont(font)
        heading.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body = self._body_label()
        self.content_layout.addWidget(heading); self.content_layout.addWidget(body)
        self.sections.append((heading, body, heading_key, body_key, bullets))

    def retranslate_ui(self, *args) -> None:
        t = self.localization.text
        title=t("preview.title",display_name=get_display_name(),preview_label=PREVIEW_LABEL)
        self.setWindowTitle(title); self.title_label.setText(title); self.badge_label.setText(t("preview.badge"))
        for heading, body, heading_key, body_key, bullets in self.sections:
            heading.setText(t(heading_key))
            raw = t(body_key)
            body.setText("\n".join(f"• {line}" for line in raw.splitlines() if line) if bullets else raw)
        self.build_info_label.setText(t("preview.build_info",version=VERSION_LABEL,format_version=FORMAT_VERSION,preview_label=PREVIEW_LABEL)); self.footer_label.setText(t("preview.footer"))
        self.do_not_show_check.setText(t("preview.do_not_show"))
        if self.manual_open:
            self.close_button.setText(t("preview.close"))
        else:
            self.exit_button.setText(t("preview.exit")); self.accept_button.setText(t("preview.accept"))

    def _accept_startup(self) -> None:
        if self.do_not_show_check.isChecked():
            try:
                self.settings.setValue(preview_notice_settings_key(), True)
                self.settings.sync()
            except Exception as exc:
                log_exception("preview_notice_settings_write",exc)
        self.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.accept() if self.manual_open else self._accept_startup()
            event.accept()
            return
        super().keyPressEvent(event)
