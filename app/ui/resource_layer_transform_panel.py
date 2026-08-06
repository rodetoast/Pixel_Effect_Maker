"""Shared Resource Layer 2.5D transform inspector section."""

from __future__ import annotations
from copy import deepcopy

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.models.effect_resource_layer import TRANSFORM_TRACK_PROPERTIES
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox


class ResourceLayerTransformPanel(QGroupBox):
    transform_changed = Signal(str, object)
    interactive_transform_changed = Signal(str, object, str)
    transform_edit_finished = Signal(str)
    keyframe_requested = Signal(str, str, int, float, str)
    gizmo_mode_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__("2.5D Transform", parent); self.layer=None;self.frame=0;self._loading=False;self._localization=None
        self.setMinimumWidth(0);self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        root=QVBoxLayout(self);root.setContentsMargins(8,10,8,8);self.description=QLabel("Transform the final Resource Layer output as a flat plane.");self.description.setWordWrap(True);self.description.setMinimumWidth(0);self.description.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);root.addWidget(self.description)
        tools=QGridLayout();tools.setColumnStretch(0,1);tools.setColumnStretch(1,1);self.gizmo_buttons={}
        for mode,label in (("move","Move XYZ"),("rotate_x","Rotate X"),("rotate_y","Rotate Y"),("rotate_z","Rotate Z"),("scale","Scale"),("pivot","Pivot")):
            button=QPushButton(label);button.setCheckable(True);button.setObjectName(f"resourceLayerGizmo_{mode}");button.setMinimumWidth(0);button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);button.clicked.connect(lambda checked=False,m=mode:self._select_mode(m));self.gizmo_buttons[mode]=button;index=len(self.gizmo_buttons)-1;tools.addWidget(button,index//2,index%2)
        self.gizmo_buttons["move"].setChecked(True);root.addLayout(tools)
        form=QFormLayout();self.form=form;form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop);root.addLayout(form);self.fields={};self.key_buttons={};self.easings={};self.easing_labels={};self.field_rows={}
        labels={"position_x":"Position X","position_y":"Position Y","position_z":"Position Z","rotation_x":"Rotation X","rotation_y":"Rotation Y","rotation_z":"Rotation Z","scale_x":"Scale X","scale_y":"Scale Y","opacity":"Opacity","pivot_x":"Pivot X","pivot_y":"Pivot Y","perspective_strength":"Perspective Strength"}
        for name in (*TRANSFORM_TRACK_PROPERTIES,"pivot_x","pivot_y"):
            spin=ScrollSafeDoubleSpinBox();spin.setObjectName(f"resourceLayer_{name}");spin.setDecimals(3);spin.setMinimumWidth(70);spin.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
            if name.startswith("rotation_"):spin.setRange(-36000,36000);spin.setSingleStep(1)
            elif name in {"scale_x","scale_y"}:spin.setRange(.01,100);spin.setSingleStep(.05)
            elif name in {"opacity","perspective_strength"}:spin.setRange(0,1);spin.setSingleStep(.05)
            elif name=="position_z":spin.setRange(-4096,4096)
            else:spin.setRange(-8192,8192)
            row=QWidget();row.setMinimumWidth(0);row.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);column=QVBoxLayout(row);column.setContentsMargins(0,0,0,0);column.setSpacing(3);column.addWidget(spin)
            if name in TRANSFORM_TRACK_PROPERTIES:
                footer=QWidget();footer.setMinimumWidth(0);footer.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);line=QHBoxLayout(footer);line.setContentsMargins(0,0,0,0);line.setSpacing(3);easing_label=QLabel("Easing");easing_label.setObjectName(f"resourceLayerEasingLabel_{name}");easing_label.setMinimumWidth(0);easing=QComboBox();[easing.addItem(v,v) for v in ("Linear","Ease In","Ease Out","Ease In/Out")];easing.setMinimumWidth(0);easing.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
                key=QPushButton("◆");key.setObjectName(f"resourceLayerKey_{name}");key.setFixedSize(30,28);key.clicked.connect(lambda checked=False,n=name:self._add_key(n));line.addWidget(easing_label);line.addWidget(easing,1);line.addWidget(key);column.addWidget(footer);self.key_buttons[name]=key;self.easings[name]=easing;self.easing_labels[name]=easing_label
            form.addRow(labels[name],row);label=form.labelForField(row);label.setWordWrap(True);label.setMinimumWidth(0);label.setMaximumWidth(88);label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred);self.field_rows[name]=row;self.fields[name]=spin;spin.valueChanged.connect(self._changed);spin.editingFinished.connect(self._editing_finished)
        self.reset=QPushButton("Reset 2.5D Transform");self.reset.setObjectName("resetResourceLayerTransform");self.reset.setMinimumWidth(0);self.reset.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);self.reset.clicked.connect(self._reset);root.addWidget(self.reset)

    def set_layer(self, layer, frame=0):
        self.layer=layer;self.frame=int(frame);self._loading=True
        if layer is not None:
            transform=layer.layer_transform
            for name,spin in self.fields.items():spin.setValue(transform.value(name,self.frame) if name in TRANSFORM_TRACK_PROPERTIES else getattr(transform,name))
            for name,button in self.key_buttons.items():button.setChecked(any(key.frame==self.frame for key in transform.tracks.get(name,()).keyframes) if name in transform.tracks else False)
        self.setEnabled(layer is not None);self._loading=False

    def set_transform_fields(self,layer,frame,names):
        self.layer=layer;self.frame=int(frame);self._loading=True
        try:
            transform=layer.layer_transform
            for name in names:
                if name not in self.fields:continue
                self.fields[name].setValue(transform.value(name,self.frame) if name in TRANSFORM_TRACK_PROPERTIES else getattr(transform,name))
                if name in self.key_buttons:
                    track=transform.tracks.get(name);self.key_buttons[name].setChecked(bool(track and any(key.frame==self.frame for key in track.keyframes)))
        finally:self._loading=False

    def _changed(self,*args):
        if self._loading or self.layer is None:return
        transform=deepcopy(self.layer.layer_transform)
        for name,spin in self.fields.items():
            track=transform.tracks.get(name)
            key=next((key for key in track.keyframes if key.frame==self.frame),None) if track else None
            if key is not None:key.value=float(spin.value())
            else:setattr(transform,name,float(spin.value()))
        transform.revision+=1
        name=next((name for name,field in self.fields.items() if field is self.sender()),"")
        if name:self.interactive_transform_changed.emit(self.layer.id,transform,name)
        else:self.transform_changed.emit(self.layer.id,transform)

    def _editing_finished(self):
        if not self._loading and self.layer is not None:self.transform_edit_finished.emit(self.layer.id)

    def _add_key(self,name):
        if self.layer is not None:self.keyframe_requested.emit(self.layer.id,name,self.frame,float(self.fields[name].value()),str(self.easings[name].currentData()))

    def _reset(self):
        if self.layer is None:return
        transform=deepcopy(self.layer.layer_transform);transform.reset_base();self.transform_changed.emit(self.layer.id,transform)

    def _select_mode(self,mode):
        for name,button in self.gizmo_buttons.items():button.setChecked(name==mode)
        if self.layer is not None:self.gizmo_mode_changed.emit(self.layer.id,mode)

    def retranslate_ui(self, localization):
        self._localization=localization;t=localization.text;self.setTitle(t("resource_layer.transform"));self.description.setText(t("resource_layer.transform_help"));self.reset.setText(t("resource_layer.transform_reset"))
        tips={"rotation_x":"tooltip.resource_layer.rotation_x","rotation_y":"tooltip.resource_layer.rotation_y","rotation_z":"tooltip.resource_layer.rotation_z","position_z":"tooltip.resource_layer.position_z","perspective_strength":"tooltip.resource_layer.perspective"}
        for name,field in self.fields.items():field.setToolTip(t(tips.get(name,"resource_layer.transform_help")))
        label_keys={"position_x":"field.position_x","position_y":"field.position_y","position_z":"resource_layer.position_z","rotation_x":"resource_layer.rotation_x","rotation_y":"resource_layer.rotation_y","rotation_z":"resource_layer.rotation_z","scale_x":"field.scale_x","scale_y":"field.scale_y","opacity":"field.opacity","pivot_x":"resource.pivot_x","pivot_y":"resource.pivot_y","perspective_strength":"resource_layer.perspective"}
        for name,field in self.fields.items():self.form.labelForField(field.parentWidget()).setText(t(label_keys[name]))
        mode_keys={"move":"resource_layer.move_xyz","rotate_x":"resource_layer.rotation_x","rotate_y":"resource_layer.rotation_y","rotate_z":"resource_layer.rotation_z","scale":"gizmo.scale","pivot":"composition.pivot"}
        for name,button in self.gizmo_buttons.items():button.setText(t(mode_keys[name]))
        for name,button in self.key_buttons.items():button.setToolTip(self.fields[name].toolTip()+"\n"+t("resource_layer.add_keyframe"))
        for label in self.easing_labels.values():label.setText(t("property.easing"));label.setVisible(True)
        for name,button in self.gizmo_buttons.items():button.setToolTip(t("tooltip.resource_layer.depth_handle") if name=="move" else t(tips.get(name,"resource_layer.transform_help")))
        self.reset.setToolTip(t("resource_layer.transform_reset")+". "+t("resource_layer.transform_help"))
