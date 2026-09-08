"""Small, semantic building blocks shared by both Timeline command bars."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPalette, QPen
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QTableWidget, QWidget


def command_group(parent: QWidget, name: str, widgets) -> QWidget:
    group = QWidget(parent)
    group.setObjectName(f"timelineCommandGroup_{name}")
    group.setProperty("commandGroup", name)
    layout = QHBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    for widget in widgets:
        widget.setProperty("commandGroup", name)
        if isinstance(widget,QAbstractButton) and widget.property("commandRole") is None:
            widget.setProperty("commandRole","toggle" if widget.isCheckable() else "tool")
        layout.addWidget(widget)
    return group


def command_separator(parent: QWidget) -> QFrame:
    separator = QFrame(parent)
    separator.setObjectName("timelineCommandSeparator")
    separator.setFrameShape(QFrame.Shape.VLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    separator.setContentsMargins(3, 0, 3, 0)
    return separator


class InactiveTimelineTable(QTableWidget):
    """Paint the viewport beyond the last real frame as inactive time."""

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setProperty("outsideDurationTreatment","inactive")
        header=self.horizontalHeader();palette=header.palette();palette.setColor(QPalette.ColorRole.Window,self.palette().alternateBase().color().darker(108));header.setPalette(palette);header.setAutoFillBackground(True)

    def inactive_area_rect(self) -> QRect:
        viewport = self.viewport().rect()
        if self.columnCount() <= 0:
            return QRect(viewport)
        last = self.columnCount() - 1
        duration_right = self.columnViewportPosition(last) + self.columnWidth(last)
        left = max(viewport.left(), duration_right)
        return QRect(left, viewport.top(), max(0, viewport.right() - left + 1), viewport.height())

    def paintEvent(self, event):  # noqa: N802
        super().paintEvent(event)
        inactive = self.inactive_area_rect()
        if inactive.isEmpty():
            return
        painter = QPainter(self.viewport())
        base = self.palette().alternateBase().color().darker(112)
        painter.fillRect(inactive, base)
        painter.setPen(QPen(self.palette().mid().color(), 1))
        painter.drawLine(inactive.left(), inactive.top(), inactive.left(), inactive.bottom())
        for row in range(self.rowCount()):
            bottom = self.rowViewportPosition(row) + self.rowHeight(row) - 1
            if inactive.top() <= bottom <= inactive.bottom():
                painter.drawLine(inactive.left(), bottom, inactive.right(), bottom)

    def inactive_paint_complexity(self) -> str:
        return "one-rect-plus-visible-rows"
