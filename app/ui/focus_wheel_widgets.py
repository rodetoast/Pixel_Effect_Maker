"""Wheel-safe editor widgets.

Numeric inputs ignore an unmodified wheel so an enclosing scroll area can keep
scrolling. Ctrl+Wheel is an explicit, focus-independent numeric adjustment. The
old class names remain as aliases for project/plugin compatibility.
"""

from __future__ import annotations

import math
import re

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSizePolicy, QSpinBox


class _ScrollSafeWheelMixin:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Keep text entry local to the line edit until Qt accepts it on Enter
        # or focus-out. Button, arrow-key, and explicit Ctrl+Wheel steps still
        # update immediately through QAbstractSpinBox.stepBy().
        self.setKeyboardTracking(False)

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


class RotationSpinBox(ScrollSafeDoubleSpinBox):
    """Edit continuous total degrees while displaying turns plus residual degrees."""

    _TURN_PATTERN = re.compile(
        r"^\s*([+-]?\d+)\s*[xX](?:\s*([+-])?\s*(\d+(?:\.\d*)?|\.\d+))?\s*°?\s*$"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedWidth(self.fontMetrics().horizontalAdvance("-100x - 359.000°") + 32)

    def sizeHint(self) -> QSize:  # noqa: N802
        hint = super().sizeHint()
        stable_width = self.fontMetrics().horizontalAdvance("-100x - 359.000°") + 32
        return QSize(max(hint.width(), stable_width), hint.height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(self.fontMetrics().horizontalAdvance("-1x - 90.000°") + 28, hint.height())

    @staticmethod
    def decompose(value: float) -> tuple[int, float]:
        turns = math.trunc(float(value) / 360.0)
        residual = float(value) - turns * 360.0
        if abs(residual) < 0.5e-12:
            residual = 0.0
        return turns, residual

    def textFromValue(self, value: float) -> str:  # noqa: N802
        turns, residual = self.decompose(value)
        sign = "-" if residual < 0.0 else "+"
        return f"{turns}x {sign} {abs(residual):.{self.decimals()}f}°"

    def valueFromText(self, text: str) -> float:  # noqa: N802
        cleaned = str(text).strip().replace(" ", "")
        match = self._TURN_PATTERN.match(cleaned)
        if match:
            turns = int(match.group(1))
            residual = float(match.group(3) or 0.0)
            if match.group(2) == "-":
                residual = -residual
            return turns * 360.0 + residual
        return float(cleaned.removesuffix("°"))

    def validate(self, text: str, position: int):  # noqa: N802
        cleaned = str(text).strip()
        try:
            value = self.valueFromText(cleaned)
        except (TypeError, ValueError):
            partial = re.fullmatch(r"[+\-]?\d*\s*[xX]?\s*[+\-]?\s*\d*(?:\.\d*)?\s*°?", cleaned)
            return (QValidator.State.Intermediate if partial else QValidator.State.Invalid, text, position)
        state = QValidator.State.Acceptable if self.minimum() <= value <= self.maximum() else QValidator.State.Invalid
        return state, text, position


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
