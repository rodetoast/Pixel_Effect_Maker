"""Small Widgets inspector grammar; no project/service/Undo dependencies.

Expanded state is view-only. Feature switches remain ordinary editor widgets
owned by the caller. Rows wrap the existing ScrollSafe/Rotation editors rather
than reimplementing input, ranges, commit, or wheel semantics.
"""
from PySide6.QtCore import QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (QApplication, QAbstractSpinBox, QComboBox, QGroupBox, QHBoxLayout,
    QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from .layout_metrics import (INSPECTOR_ROW_SPACING, INSPECTOR_SECTION_MARGIN,
    INSPECTOR_SECTION_SPACING, SECTION_HEADER_HEIGHT, SPACING_SM, inspector_color)


class InspectorViewState:
    """Session-only, per selection kind/ID/section. Never serialized or QSettings."""
    def __init__(self):
        self._expanded = {}

    def expanded(self, kind, selection_id, section_id, default=True):
        return self._expanded.get((kind, selection_id, section_id), default)

    def remember(self, kind, selection_id, section_id, expanded):
        self._expanded[(kind, selection_id, section_id)] = bool(expanded)


class InspectorWarning(QLabel):
    message_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.severity = "warning"
        self.setWordWrap(True)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def set_message(self, text, severity="warning"):
        if severity not in {"info", "warning", "error"}:
            raise ValueError("unknown inspector message severity")
        self.severity = severity
        super().setText(text)
        self.setVisible(bool(text))
        self.setAccessibleDescription(text)
        self._apply_palette()
        self.message_changed.emit(text, severity)

    def setText(self, text):  # Existing panel rejection paths retain QLabel API.
        self.set_message(text)

    def clear(self):
        self.set_message("")

    def _apply_palette(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText,
                         inspector_color("state_" + self.severity, palette))
        self.setPalette(palette)


class _SectionLayout(QVBoxLayout):
    def activate(self):
        # Support explicit layout of an inspector embedded in a hidden stack,
        # as well as normal visible event-driven Qt layout.
        result = super().activate()
        for widget in self.parentWidget().findChildren(QWidget):
            if widget.layout() is not None:
                widget.layout().activate()
                widget.layout().setGeometry(widget.rect())
        return result


class InspectorSection(QGroupBox):
    """Header remains visible when body is collapsed; enable is never inferred."""
    expanded_changed = Signal(bool)

    def __init__(self, section_id, view_state, parent=None):
        super().__init__(parent)
        self.section_id = section_id
        self.view_state = view_state
        self._context = ("particle", None)
        self._expanded = True
        self._title = ""
        self._ko = False
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root = _SectionLayout(self)
        root.setContentsMargins(*(INSPECTOR_SECTION_MARGIN,) * 4)
        root.setSpacing(INSPECTOR_SECTION_SPACING)
        header = QHBoxLayout()
        header.setSpacing(SPACING_SM)
        self.disclosure = QToolButton()
        self.disclosure.setObjectName(section_id + "Disclosure")
        self.disclosure.setCheckable(True)
        self.disclosure.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.disclosure.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.disclosure.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.disclosure.setMinimumWidth(0)
        self.disclosure.toggled.connect(self.set_expanded)
        self.badge = QLabel()
        self.badge.setObjectName(section_id + "WarningBadge")
        self.badge.hide()
        header.addWidget(self.disclosure, 1)
        header.addWidget(self.badge)
        root.addLayout(header)
        self.summary = QLabel()
        self.summary.setObjectName(section_id + "Summary")
        self.summary.setWordWrap(True)
        self.summary.setMinimumWidth(0)
        self.summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root.addWidget(self.summary)
        self.body = QWidget()
        self.body.setMinimumWidth(0)
        self.body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root.addWidget(self.body)
        self.set_expanded(True)

    def title(self):
        return self._title

    def setTitle(self, title):
        self._title = title
        self.disclosure.setText(title)
        self._update_accessibility()

    def set_language(self, ko):
        self._ko = bool(ko)
        self._update_accessibility()

    def set_context(self, kind, selection_id):
        self._context = (kind, selection_id)
        # Loading a selection is not an edit and does not reset other contexts.
        self.set_expanded(self.view_state.expanded(kind, selection_id, self.section_id))

    def is_expanded(self):
        return self._expanded

    def set_expanded(self, expanded):
        # Hiding a focused spin can otherwise commit its pending text on focus
        # out. Keep the section open until the existing Enter/focus-out commit
        # finishes; never discard, commit, or rewrite text on a view-only action.
        if not expanded and self._has_pending_numeric():
            with QSignalBlocker(self.disclosure):
                self.disclosure.setChecked(self._expanded)
            self.disclosure.setToolTip("입력을 확정한 뒤 접으세요." if self._ko else "Finish editing before collapsing.")
            return
        changed = self._expanded != bool(expanded)
        self._expanded = bool(expanded)
        with QSignalBlocker(self.disclosure):
            self.disclosure.setChecked(self._expanded)
        self.disclosure.setArrowType(Qt.ArrowType.DownArrow if self._expanded else Qt.ArrowType.RightArrow)
        self.body.setVisible(self._expanded)
        self.view_state.remember(*self._context, self.section_id, self._expanded)
        self._update_accessibility()
        if changed:
            self.expanded_changed.emit(self._expanded)

    def _has_pending_numeric(self):
        spin = QApplication.focusWidget()
        while spin is not None and not isinstance(spin, QAbstractSpinBox):
            spin = spin.parentWidget()
        return spin is not None and self.body.isAncestorOf(spin) and spin.lineEdit().isModified()

    def set_summary(self, text):
        self.summary.setText(text)
        self.summary.setToolTip(text)
        self._update_accessibility()

    def set_warning(self, text, severity):
        # Info is a distinct badge, not a falsely reported configuration error.
        self.badge.setText({"info": "i", "warning": "!", "error": "×"}[severity])
        self.badge.setVisible(bool(text))
        self.badge.setToolTip(text)
        self.badge.setAccessibleName(text)
        self.setProperty("messageSeverity", severity if text else "")

    def _update_accessibility(self):
        action = ("접기" if self._expanded else "펼치기") if self._ko else ("Collapse" if self._expanded else "Expand")
        self.disclosure.setAccessibleName(f"{self._title} · {action}")
        self.disclosure.setToolTip(action)
        self.disclosure.setAccessibleDescription(self.summary.text())
        self.disclosure.setMinimumHeight(max(SECTION_HEADER_HEIGHT,
            self.disclosure.fontMetrics().height() + INSPECTOR_SECTION_MARGIN * 2))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange and hasattr(self, "disclosure"):
            self._update_accessibility()


class InspectorRow(QWidget):
    """Label/editor/near-field validation; no editor signals are intercepted."""
    def __init__(self, label, editor, parent=None, *, unit=None, tooltip=None):
        super().__init__(parent)
        self.editor = editor
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        self.label.setBuddy(editor)
        self.label.setMinimumWidth(0)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(INSPECTOR_ROW_SPACING)
        editor.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.label)
        layout.addWidget(editor)
        self.message = InspectorWarning()
        self.message.hide()
        layout.addWidget(self.message)
        if unit is not None:
            editor.setSuffix(unit)
        if tooltip:
            editor.setToolTip(tooltip)
            self.label.setToolTip(tooltip)

    def set_editor_enabled(self, enabled, reason=""):
        self.editor.setEnabled(enabled)
        self.message.set_message("" if enabled else reason, "info")

    def set_validation(self, message):
        self.message.set_message(message, "error")


class InspectorNumericRow(InspectorRow):
    def __init__(self, label, editor, *args, **kwargs):
        if not isinstance(editor, QAbstractSpinBox):
            raise TypeError("Numeric row wraps an existing spin editor")
        super().__init__(label, editor, *args, **kwargs)


class InspectorComboRow(InspectorRow):
    def __init__(self, label, editor, *args, **kwargs):
        if not isinstance(editor, QComboBox):
            raise TypeError("Combo row wraps an existing combo editor")
        super().__init__(label, editor, *args, **kwargs)


class InspectorForm(QVBoxLayout):
    """Pilot row collection with labelForField compatibility for current callers."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(INSPECTOR_ROW_SPACING)
        self.rows = {}

    def addRow(self, label, editor=None):
        if editor is None:
            self.addWidget(label)
            return
        row_class = InspectorNumericRow if isinstance(editor, QAbstractSpinBox) else InspectorComboRow if isinstance(editor, QComboBox) else InspectorRow
        row = row_class(label, editor)
        self.rows[editor] = row
        self.addWidget(row)

    def labelForField(self, editor):
        return self.rows[editor].label

    def set_field_visible(self, editor, visible):
        self.rows[editor].setVisible(visible)
