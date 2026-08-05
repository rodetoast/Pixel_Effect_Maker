"""Inspector for a Resource Composition placed in the Effect Composition."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.models.effect_composition_layer import EffectCompositionLayer
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from app.ui.tooltip_helper import apply_tooltip


class CompositionLayerPropertiesPanel(QScrollArea):
    changed = Signal(str, object)
    mode_changed = Signal(str, str)
    resource_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.layer: EffectCompositionLayer | None = None
        self._loading = False
        body = QWidget(); layout = QVBoxLayout(body)
        self.resource_layer_id = None
        self.title = QLabel("Resource Layer")
        self.title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(self.title)
        self.resource = QComboBox(); layout.addWidget(self.resource);self.resource.currentIndexChanged.connect(self._resource_changed)
        self.mode = QComboBox(); self.mode.addItem("Single", "single"); self.mode.addItem("Particle Emission", "particle"); layout.addWidget(self.mode)
        self.mode_help = QLabel("Place one resource directly in the Effect Composition."); self.mode_help.setWordWrap(True); layout.addWidget(self.mode_help)
        self.mode.currentIndexChanged.connect(self._mode_changed)
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
            if self.resource.count()==0 and composition is not None:self.resource.addItem(composition.name,composition.id)
            self.resource.setCurrentIndex(max(0,self.resource.findData(layer.resource_composition_id)))
            for widget, value in (
                (self.start_x, layer.start_x), (self.start_y, layer.start_y),
                (self.end_x, layer.end_x), (self.end_y, layer.end_y),
                (self.start_frame, layer.start_frame), (self.end_frame, layer.end_frame),
            ): widget.setValue(value)
        self._loading = False

    def set_resource_layer(self, layer, project) -> None:
        self.resource_layer_id = None if layer is None else layer.id
        self._loading = True
        self.resource.clear();[self.resource.addItem(item.name,item.id) for item in project.resource_compositions]
        if layer is not None:self.mode.setCurrentIndex(max(0,self.mode.findData(layer.placement_mode)))
        self._loading = False
        self.set_layer(None if layer is None else layer.as_composition_layer(), project)

    def _mode_changed(self, *args) -> None:
        mode = self.mode.currentData()
        localization=getattr(self,"_localization",None);self.mode_help.setText(localization.text("resource_layer.single_help" if mode=="single" else "resource_layer.particle_help") if localization else ("Place one resource directly in the Effect Composition." if mode == "single" else "Emit multiple instances of the same resource with direction, speed, and lifetime."))
        if not self._loading and self.resource_layer_id:self.mode_changed.emit(self.resource_layer_id,str(mode))

    def _resource_changed(self,*args) -> None:
        if not self._loading and self.resource_layer_id and self.resource.currentData():self.resource_changed.emit(self.resource_layer_id,str(self.resource.currentData()))

    def _changed(self, *args) -> None:
        if self._loading or self.layer is None: return
        value = deepcopy(self.layer)
        value.start_x = self.start_x.value(); value.start_y = self.start_y.value()
        value.end_x = self.end_x.value(); value.end_y = self.end_y.value()
        value.start_frame = self.start_frame.value(); value.end_frame = max(value.start_frame, self.end_frame.value())
        self.changed.emit(self.layer.id, value)

    def retranslate_ui(self, localization) -> None:
        self._localization=localization
        self.title.setText(localization.text("resource_layer.title"))
        self.mode.setItemText(0,localization.text("resource_layer.single"));self.mode.setItemText(1,localization.text("resource_layer.particle"));self.mode_help.setText(localization.text("resource_layer.single_help" if self.mode.currentData()=="single" else "resource_layer.particle_help"))
        apply_tooltip(self.mode,localization,"tooltip.resource_layer.mode",status=False);apply_tooltip(self.resource,localization,"tooltip.resource_layer.resource",status=False)
        labels = ("effect.start_x", "effect.start_y", "effect.end_x", "effect.end_y", "particle.start_frame", "composition.end")
        for (widget, _), key in zip(self._fields, labels, strict=True):
            self.form.labelForField(widget).setText(localization.text(key))
            apply_tooltip(widget, localization, "tooltip.effect.composition_path", status=False)
