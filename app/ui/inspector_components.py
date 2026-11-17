"""Small Widgets inspector grammar; no project/service/Undo dependencies.

Expanded state is view-only. Feature switches remain ordinary editor widgets
owned by the caller. Rows wrap the existing ScrollSafe/Rotation editors rather
than reimplementing input, ranges, commit, or wheel semantics.
"""
from PySide6.QtCore import QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (QApplication, QAbstractSpinBox, QComboBox, QGroupBox, QHBoxLayout,
    QLabel, QLayout, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

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
        self.setWordWrap(True)  # Set after policy: retain Qt's height-for-width flag.

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
        if getattr(self,"_applying_palette",False):return
        self._applying_palette=True
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText,
                         inspector_color("state_" + self.severity, palette))
        self.setPalette(palette)
        self._applying_palette=False

    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type()==QEvent.Type.PaletteChange:self._apply_palette()


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
        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        root.setContentsMargins(*(INSPECTOR_SECTION_MARGIN,) * 4)
        root.setSpacing(INSPECTOR_SECTION_SPACING)
        header = QHBoxLayout()
        header.setSpacing(SPACING_SM)
        self.disclosure = QToolButton()
        self.disclosure.setObjectName(section_id + "Disclosure")
        self.disclosure.setCheckable(False)  # Disclosure is not a selected/enabled feature.
        self.disclosure.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.disclosure.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.disclosure.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.disclosure.setMinimumWidth(0)
        self.disclosure.setAutoRaise(True)
        self.disclosure.clicked.connect(lambda: self.set_expanded(not self._expanded))
        self.badge = QLabel()
        self.badge.setObjectName(section_id + "WarningBadge")
        self.badge.hide()
        header.addWidget(self.disclosure, 1)
        header.addWidget(self.badge)
        root.addLayout(header)
        self.summary = QLabel()
        self.summary.setObjectName(section_id + "Summary")
        self.summary.setWordWrap(True)
        self.summary.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self.summary.setMinimumWidth(0)
        self.summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.summary.setWordWrap(True)
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
        self.disclosure.setText({"Transform / Advanced":"Transform", "Lifetime / Look":"Lifetime", "Sub-emitter":"Events"}.get(title,title))
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
        self._reflow()
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
        self._reflow()
        self._update_accessibility()

    def _reflow(self):
        # Qt owns content rectangles, title insets and height-for-width. Never
        # overwrite descendant layouts with widget.rect() or cache pixel heights.
        if self.body.layout() is not None:self.body.layout().invalidate()
        self.layout().invalidate()
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None and parent.layout() is not None:
            owner = parent.layout()
            index = owner.indexOf(self)
            if index >= 0 and hasattr(owner, "insertWidget"):
                # Reparenting/disclosure can leave QWidgetItemV2's HFW cache
                # describing the old body. Rebuild only this layout item, not
                # the editor, values or signal bindings.
                owner.removeWidget(self)
                owner.insertWidget(index, self)
            owner.invalidate()

    def heightForWidth(self, width):
        # QGroupBox's inherited HFW cache can still describe a collapsed body.
        # Expose the live layout contract to the owning QBoxLayout instead.
        layout = self.layout()
        return max(self.minimumSizeHint().height(), layout.totalHeightForWidth(width)) if layout else super().heightForWidth(width)

    def event(self, event):
        result = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest:
            # Child show/hide reaches us asynchronously. Notify our owner after
            # Qt has recomputed this layout, not just before the child request.
            self.updateGeometry()
        return result

    def set_warning(self, text, severity):
        # Info is a distinct badge, not a falsely reported configuration error.
        self.badge.setText({"info": "i", "warning": "!", "error": "×"}[severity])
        self.badge.setVisible(bool(text))
        self.badge.setToolTip(text)
        self.badge.setAccessibleName(text)
        self.setProperty("messageSeverity", severity if text else "")
        self._reflow()

    def _update_accessibility(self):
        # A stylesheet can otherwise freeze QToolButton's application font and
        # stop it following the Inspector's per-widget font/DPI scale.
        self.disclosure.setFont(self.font())
        action = ("접기" if self._expanded else "펼치기") if self._ko else ("Collapse" if self._expanded else "Expand")
        self.disclosure.setAccessibleName(f"{self._title} · {action}")
        self.disclosure.setToolTip(self._title + " · " + action)
        self.disclosure.setAccessibleDescription(self.summary.text())
        self.disclosure.setMinimumHeight(max(SECTION_HEADER_HEIGHT,
            self.disclosure.fontMetrics().height() + INSPECTOR_SECTION_MARGIN * 2))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange and hasattr(self, "disclosure"):
            self._update_accessibility()
            if hasattr(self, "summary"):
                self._reflow()


class InspectorRow(QWidget):
    """Label/editor/near-field validation; no editor signals are intercepted."""
    def __init__(self, label, editor, parent=None, *, unit=None, tooltip=None):
        super().__init__(parent)
        self.editor = editor
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        self.label.setBuddy(editor)
        self.label.setMinimumWidth(0)
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.label.setWordWrap(True)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
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
        self.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
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
