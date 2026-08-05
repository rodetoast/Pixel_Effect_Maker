"""Wheel-safe editor widgets.

Numeric inputs ignore an unmodified wheel so an enclosing scroll area can keep
scrolling. Ctrl+Wheel is an explicit, focus-independent numeric adjustment. The
old class names remain as aliases for project/plugin compatibility.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class _ScrollSafeWheelMixin:
    def wheelEvent(self, event) -> None:  # noqa: N802
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._wheel_delta = 0
            event.ignore()
            return
        if not self.isEnabled() or self.isReadOnly():
            event.ignore()
            return
        delta = event.angleDelta().y() or event.pixelDelta().y()
        self._wheel_delta = getattr(self, "_wheel_delta", 0) + delta
        steps = int(self._wheel_delta / 120)
        if steps:
            self.stepBy(steps)
            self._wheel_delta -= steps * 120
        event.accept()


class ScrollSafeSpinBox(_ScrollSafeWheelMixin, QSpinBox):
    pass


class ScrollSafeDoubleSpinBox(_ScrollSafeWheelMixin, QDoubleSpinBox):
    pass


class FocusWheelComboBox(QComboBox):
    """Keep the historical focus-only wheel policy for non-numeric choices."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


# Compatibility imports used by older panels and third-party extensions.
FocusWheelSpinBox = ScrollSafeSpinBox
FocusWheelDoubleSpinBox = ScrollSafeDoubleSpinBox
