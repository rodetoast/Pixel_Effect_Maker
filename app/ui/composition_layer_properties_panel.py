"""Inspector for a Resource Composition placed in the Effect Composition."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.layer_parenting import would_create_parent_cycle
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from app.ui.tooltip_helper import apply_tooltip
from app.ui.resource_layer_transform_panel import ResourceLayerTransformPanel
from app.ui.hierarchy_display import layer_display_labels


class CompositionLayerPropertiesPanel(QScrollArea):
    changed = Signal(str, object)
    mode_changed = Signal(str, str)
    resource_changed = Signal(str, str)
    transform_changed = Signal(str, object)
    transform_keyframe_requested = Signal(str, str, int, float, str)
    transform_keyframe_delete_requested = Signal(str, str, int)
    transform_gizmo_changed = Signal(str, str)
    name_changed = Signal(str, str)
    parent_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True);self.setMinimumWidth(0);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.layer: EffectCompositionLayer | None = None
        self._loading = False
        body = QWidget();body.setObjectName("compositionLayerInspectorContent");body.setMinimumWidth(0);body.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred); layout = QVBoxLayout(body);layout.setContentsMargins(6,6,6,6);layout.setSpacing(5);layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.resource_layer_id = None
        self.title = QLabel("Resource Layer")
        self.title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.title.setMinimumWidth(0);self.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title)
        common=QGroupBox("Resource Layer");common.setMinimumWidth(0);common.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);self.common_form=QFormLayout(common);self.common_form.setContentsMargins(7,8,7,7);self.common_form.setHorizontalSpacing(6);self.common_form.setVerticalSpacing(4);self.common_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);self.common_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.name=QLineEdit();self.common_form.addRow("Layer Name",self.name);self.name.editingFinished.connect(self._name_changed)
        self.parent_layer=QComboBox();self.common_form.addRow("Parent Layer",self.parent_layer);self.parent_layer.currentIndexChanged.connect(self._parent_changed)
        self.resource = QComboBox();self.resource.setMinimumWidth(0);self.resource.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);self.common_form.addRow("Resource Composition",self.resource);self.resource.currentIndexChanged.connect(self._resource_changed)
        self.mode = QComboBox();self.mode.setMinimumWidth(0);self.mode.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed); self.mode.addItem("Single", "single"); self.mode.addItem("Particle Emission", "particle");self.common_form.addRow("Placement Mode",self.mode)
        for editor in (self.name,self.parent_layer,self.resource,self.mode):label=self.common_form.labelForField(editor);label.setWordWrap(True);label.setMinimumWidth(0);label.setMaximumWidth(110);label.setBuddy(editor);label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred)
        layout.addWidget(common)
        self.mode_help = QLabel("Place one resource directly in the Effect Composition."); self.mode_help.setWordWrap(True);self.mode_help.setMinimumWidth(0);self.mode_help.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); layout.addWidget(self.mode_help)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.transform_panel=ResourceLayerTransformPanel()
        self.transform_panel.transform_changed.connect(self.transform_changed)
        self.transform_panel.keyframe_requested.connect(self.transform_keyframe_requested)
        self.transform_panel.keyframe_delete_requested.connect(self.transform_keyframe_delete_requested)
        self.transform_panel.gizmo_mode_changed.connect(self.transform_gizmo_changed)
        group = QGroupBox("Path");group.setMinimumWidth(0);group.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred); self.form = QFormLayout(group);self.form.setContentsMargins(7,8,7,7);self.form.setHorizontalSpacing(6);self.form.setVerticalSpacing(4);self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
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
            widget.setMinimumWidth(70);widget.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
            field_label=self.form.labelForField(widget);field_label.setMinimumWidth(0);field_label.setMaximumWidth(88);field_label.setWordWrap(True)
            widget.valueChanged.connect(self._changed)
        layout.addWidget(group);layout.addWidget(self.transform_panel);layout.addStretch(); self.setWidget(body)

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
        self.parent_layer.clear();self.parent_layer.addItem("None",None)
        if layer is not None:
            labels=layer_display_labels(project.effect_resource_layers,project.effect_layer_groups)
            for item in project.effect_resource_layers:
                if item.id!=layer.id and not would_create_parent_cycle(project.effect_resource_layers,layer.id,item.id):self.parent_layer.addItem(labels.get(item.id,item.name),item.id)
            self.parent_layer.setCurrentIndex(max(0,self.parent_layer.findData(layer.parent_id)));self.name.setText(layer.name);self.mode.setCurrentIndex(max(0,self.mode.findData(layer.placement_mode)))
        self._loading = False
        self.transform_panel.set_layer(layer, getattr(project,"_current_effect_frame",0))
        self.set_layer(None if layer is None else layer.as_composition_layer(), project)

    def set_locked(self,locked: bool) -> None:
        if self.widget():self.widget().setEnabled(not bool(locked))

    def _mode_changed(self, *args) -> None:
        mode = self.mode.currentData()
        localization=getattr(self,"_localization",None);self.mode_help.setText(localization.text("resource_layer.single_help" if mode=="single" else "resource_layer.particle_help") if localization else ("Place one resource directly in the Effect Composition." if mode == "single" else "Emit multiple instances of the same resource with direction, speed, and lifetime."))
        if not self._loading and self.resource_layer_id:self.mode_changed.emit(self.resource_layer_id,str(mode))

    def _resource_changed(self,*args) -> None:
        if not self._loading and self.resource_layer_id and self.resource.currentData():self.resource_changed.emit(self.resource_layer_id,str(self.resource.currentData()))

    def _name_changed(self):
        if not self._loading and self.resource_layer_id and self.name.text().strip():self.name_changed.emit(self.resource_layer_id,self.name.text().strip())

    def _parent_changed(self,*args):
        if not self._loading and self.resource_layer_id:self.parent_changed.emit(self.resource_layer_id,self.parent_layer.currentData())

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
        self.common_form.labelForField(self.name).setText(localization.text("resource_layer.name"));self.common_form.labelForField(self.parent_layer).setText(localization.text("layer.parent"));self.common_form.labelForField(self.resource).setText(localization.text("resource_layer.resource_composition"));self.common_form.labelForField(self.mode).setText(localization.text("resource_layer.placement_mode"))
        self.mode.setItemText(0,localization.text("resource_layer.single"));self.mode.setItemText(1,localization.text("resource_layer.particle"));self.mode_help.setText(localization.text("resource_layer.single_help" if self.mode.currentData()=="single" else "resource_layer.particle_help"))
        apply_tooltip(self.mode,localization,"tooltip.resource_layer.mode",status=False);apply_tooltip(self.resource,localization,"tooltip.resource_layer.resource",status=False)
        self.transform_panel.retranslate_ui(localization)
        labels = ("effect.start_x", "effect.start_y", "effect.end_x", "effect.end_y", "particle.start_frame", "composition.end")
        for (widget, _), key in zip(self._fields, labels, strict=True):
            self.form.labelForField(widget).setText(localization.text(key))
            self.form.labelForField(widget).setBuddy(widget);self.form.labelForField(widget).setVisible(True)
            apply_tooltip(widget, localization, "tooltip.effect.composition_path", status=False)
