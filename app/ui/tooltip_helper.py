"""Localized Qt tooltip helpers shared by actions and editor controls."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QAbstractSpinBox


def _shortcut_labels(shortcuts: QAction | Iterable[str | QKeySequence] | None) -> list[str]:
    if shortcuts is None:
        return []
    values = shortcuts.shortcuts() if isinstance(shortcuts, QAction) else shortcuts
    labels: list[str] = []
    for value in values:
        sequence = value if isinstance(value, QKeySequence) else QKeySequence(str(value))
        label = sequence.toString(QKeySequence.SequenceFormat.NativeText)
        if label and label not in labels:
            labels.append(label)
    return labels


def tooltip_text(localization, key: str, shortcuts=None) -> str:
    """Return a localized behavior description with current shortcut labels."""
    description = localization.text(key)
    labels = _shortcut_labels(shortcuts)
    if labels:
        description += "\n" + localization.text(
            "tooltip.shortcut", shortcut=" / ".join(labels)
        )
    return description


def apply_tooltip(target, localization, key: str, shortcuts=None, *, status=True) -> str:
    """Apply localized help through Qt's native tooltip/status-tip properties."""
    text = tooltip_text(localization, key, shortcuts)
    if isinstance(target, QAbstractSpinBox):
        text += "\n" + localization.text("tooltip.spinbox.ctrl_wheel")
    target.setToolTip(text)
    if status and hasattr(target, "setStatusTip"):
        target.setStatusTip(text)
    return text
