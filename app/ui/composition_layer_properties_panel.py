"""Inspector for a Resource Composition placed in the Effect Composition."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.models.effect_composition_layer import EffectCompositionLayer
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from app.ui.tooltip_helper import apply_tooltip


class CompositionLayerPropertiesPanel(QScrollArea):
    changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.layer: EffectCompositionLayer | None = None
        self._loading = False
        body = QWidget(); layout = QVBoxLayout(body)
        self.title = QLabel("Composition Layer")
        self.title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(self.title)
        self.resource = QLabel(); self.resource.setWordWrap(True); layout.addWidget(self.resource)
        group = QGroupBox("Path"); self.form = QFormLayout(group)
        self.start_x = self._number(); self.start_y = self._number()
        self.end_x = self._number(); self.end_y = self._number()
        self.start_frame = self._integer(); self.end_frame = self._integer()
        self._fields = (
            (self.start_x, "Start X"), (self.start_y, "Start Y"),
            (self.end_x, "End X"), (self.end_y, "End Y"),
            (self.start_frame, "Start Frame"), (self.end_frame, "End Frame"),
        )
        for widget, label in self._fields:
            self.form.addRow(label, widget)
            widget.valueChanged.connect(self._changed)
        layout.addWidget(group); layout.addStretch(); self.setWidget(body)

    @staticmethod
    def _number():
        widget = ScrollSafeDoubleSpinBox(); widget.setRange(-4096, 4096); widget.setDecimals(2); return widget

    @staticmethod
    def _integer():
        widget = ScrollSafeSpinBox(); widget.setRange(0, 511); return widget

    def set_layer(self, layer: EffectCompositionLayer | None, project) -> None:
        self.layer = layer; self._loading = True
        if layer is not None:
            composition = next((item for item in project.resource_compositions if item.id == layer.resource_composition_id), None)
            self.resource.setText("" if composition is None else composition.name)
            for widget, value in (
                (self.start_x, layer.start_x), (self.start_y, layer.start_y),
                (self.end_x, layer.end_x), (self.end_y, layer.end_y),
                (self.start_frame, layer.start_frame), (self.end_frame, layer.end_frame),
            ): widget.setValue(value)
        self._loading = False

    def _changed(self, *args) -> None:
        if self._loading or self.layer is None: return
        value = deepcopy(self.layer)
        value.start_x = self.start_x.value(); value.start_y = self.start_y.value()
        value.end_x = self.end_x.value(); value.end_y = self.end_y.value()
        value.start_frame = self.start_frame.value(); value.end_frame = max(value.start_frame, self.end_frame.value())
        self.changed.emit(self.layer.id, value)

    def retranslate_ui(self, localization) -> None:
        self.title.setText(localization.text("effect.composition_layer"))
        labels = ("effect.start_x", "effect.start_y", "effect.end_x", "effect.end_y", "particle.start_frame", "composition.end")
        for (widget, _), key in zip(self._fields, labels, strict=True):
            self.form.labelForField(widget).setText(localization.text(key))
            apply_tooltip(widget, localization, "tooltip.effect.composition_path", status=False)
