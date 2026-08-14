"""Shared Resource Layer 2.5D transform inspector section."""

from __future__ import annotations
from copy import deepcopy

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.models.effect_resource_layer import TRANSFORM_TRACK_PROPERTIES
from app.models.property_registry import NUMERIC_PROPERTY_SPECS
from app.ui.focus_wheel_widgets import RotationSpinBox, ScrollSafeDoubleSpinBox
from app.services.multi_transform_service import mixed_numeric_value, SUPPORTED_EFFECT_PROPERTIES


class ResourceLayerTransformPanel(QGroupBox):
    transform_changed = Signal(str, object)
    interactive_transform_changed = Signal(str, object, str)
    transform_edit_finished = Signal(str)
    keyframe_requested = Signal(str, str, int, float, str)
    keyframe_delete_requested = Signal(str, str, int)
    gizmo_mode_changed = Signal(str, str)
    surface_transform_changed = Signal(str, object)
    advanced_enabled_changed = Signal(str, bool)
    batch_transform_changed = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__("Advanced", parent); self.layer=None;self.multi_layers=[];self.frame=0;self._loading=False;self._localization=None
        self.setMinimumWidth(0);self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.setCheckable(True);self.setChecked(False)
        outer=QVBoxLayout(self);outer.setContentsMargins(8,6,8,8);self.advanced_status=QLabel("Surface Transform applied");self.advanced_status.setObjectName("surfaceTransformAppliedStatus");self.advanced_status.setWordWrap(True);self.advanced_status.hide();outer.addWidget(self.advanced_status)
        self.advanced_body=QWidget();root=QVBoxLayout(self.advanced_body);root.setContentsMargins(0,4,0,0);outer.addWidget(self.advanced_body);self.advanced_body.show();self.toggled.connect(self._advanced_toggled)
        self.system_group=QGroupBox("System Space Transform");system_root=QVBoxLayout(self.system_group);system_root.setContentsMargins(8,10,8,8);root.addWidget(self.system_group)
        self.description=QLabel("Transform the whole layer coordinate system, including particle spawn positions and motion paths.");self.description.setWordWrap(True);self.description.setMinimumWidth(0);self.description.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);system_root.addWidget(self.description);self.multi_help=QLabel();self.multi_help.setWordWrap(True);self.multi_help.hide();system_root.addWidget(self.multi_help)
        tools=QGridLayout();tools.setColumnStretch(0,1);tools.setColumnStretch(1,1);self.gizmo_buttons={}
        for mode,label in (("move","Move XYZ"),("rotate_x","Rotate X"),("rotate_y","Rotate Y"),("rotate_z","Rotate Z"),("scale","Scale"),("pivot","Pivot")):
            button=QPushButton(label);button.setCheckable(True);button.setObjectName(f"resourceLayerGizmo_{mode}");button.setMinimumWidth(0);button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);button.clicked.connect(lambda checked=False,m=mode:self._select_mode(m));self.gizmo_buttons[mode]=button;index=len(self.gizmo_buttons)-1;tools.addWidget(button,index//2,index%2)
        self.gizmo_buttons["move"].setChecked(True);system_root.addLayout(tools)
        form=QFormLayout();self.form=form;form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop);system_root.addLayout(form);self.fields={};self.key_buttons={};self.easings={};self.easing_labels={};self.field_rows={}
        labels={"position_x":"Position X","position_y":"Position Y","position_z":"Position Z","rotation_x":"Rotation X","rotation_y":"Rotation Y","rotation_z":"Rotation Z","scale_x":"Scale X","scale_y":"Scale Y","opacity":"Opacity","pivot_x":"Pivot X","pivot_y":"Pivot Y","perspective_strength":"Perspective Strength"}
        for name in (*TRANSFORM_TRACK_PROPERTIES,"pivot_x","pivot_y"):
            spin=(RotationSpinBox() if name.startswith("rotation_") else ScrollSafeDoubleSpinBox());spin.setObjectName(f"resourceLayer_{name}");spin.setDecimals(3);spin.setMinimumWidth(70);spin.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
            if name.startswith("rotation_"):spin.setRange(-36000,36000);spin.setSingleStep(1)
            elif name in {"scale_x","scale_y"}:spin.setRange(.01,100);spin.setSingleStep(.05)
            elif name in {"opacity","perspective_strength"}:
                spec=NUMERIC_PROPERTY_SPECS["normalized.opacity" if name=="opacity" else "normalized.perspective"];spin.setRange(spec.minimum,spec.maximum);spin.setSingleStep(spec.step)
            elif name=="position_z":spin.setRange(-4096,4096)
            else:spin.setRange(-8192,8192)
            row=QWidget();row.setMinimumWidth(0);row.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);column=QVBoxLayout(row);column.setContentsMargins(0,0,0,0);column.setSpacing(3);column.addWidget(spin)
            if name in TRANSFORM_TRACK_PROPERTIES:
                footer=QWidget();footer.setMinimumWidth(0);footer.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);line=QHBoxLayout(footer);line.setContentsMargins(0,0,0,0);line.setSpacing(3);easing_label=QLabel("Easing");easing_label.setObjectName(f"resourceLayerEasingLabel_{name}");easing_label.setMinimumWidth(0);easing=QComboBox();[easing.addItem(v,v) for v in ("Linear","Ease In","Ease Out","Ease In/Out")];easing.setMinimumWidth(0);easing.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
                key=QPushButton("◆");key.setObjectName(f"resourceLayerKey_{name}");key.setFixedSize(30,28);key.clicked.connect(lambda checked=False,n=name:self._add_key(n));line.addWidget(easing_label);line.addWidget(easing,1);line.addWidget(key);column.addWidget(footer);self.key_buttons[name]=key;self.easings[name]=easing;self.easing_labels[name]=easing_label
            form.addRow(labels[name],row);label=form.labelForField(row);label.setWordWrap(True);label.setMinimumWidth(0);label.setMaximumWidth(88);label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred);self.field_rows[name]=row;self.fields[name]=spin;spin.valueChanged.connect(self._changed);spin.editingFinished.connect(self._editing_finished)
        self.reset=QPushButton("Reset System Space Transform");self.reset.setObjectName("resetResourceLayerTransform");self.reset.setMinimumWidth(0);self.reset.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);self.reset.clicked.connect(self._reset);system_root.addWidget(self.reset)
        self.surface_group=QGroupBox("Surface Transform (Compatibility)");self.surface_form=QFormLayout(self.surface_group);surface_form=self.surface_form;self.surface_warning=QLabel("Applied after the layer has been rasterized. Retained for compatibility with migrated projects.");self.surface_warning.setWordWrap(True);surface_form.addRow(self.surface_warning);self.surface_fields={}
        for name in (*TRANSFORM_TRACK_PROPERTIES,"pivot_x","pivot_y"):
            spin=RotationSpinBox() if name.startswith("rotation_") else ScrollSafeDoubleSpinBox();spin.setDecimals(3);spin.setMinimumWidth(70)
            if name.startswith("rotation_"):spin.setRange(-36000,36000)
            elif name in {"scale_x","scale_y"}:spin.setRange(.01,100);spin.setSingleStep(.05)
            elif name in {"opacity","perspective_strength"}:
                spec=NUMERIC_PROPERTY_SPECS["normalized.opacity" if name=="opacity" else "normalized.perspective"];spin.setRange(spec.minimum,spec.maximum);spin.setSingleStep(spec.step)
            else:spin.setRange(-8192,8192)
            spin.valueChanged.connect(self._surface_changed);surface_form.addRow(labels[name],spin);self.surface_fields[name]=spin
        self.surface_reset=QPushButton("Reset Surface Transform");self.surface_reset.setToolTip("Reset the compatibility Surface Transform to identity.");self.surface_reset.clicked.connect(self._reset_surface);surface_form.addRow(self.surface_reset);root.addWidget(self.surface_group)

    def set_layer(self, layer, frame=0):
        self.layer=layer;self.multi_layers=[];self.frame=int(frame);self._loading=True
        if layer is not None:
            self.setChecked(bool(layer.advanced_transform_enabled))
            transform=layer.layer_transform
            for name,spin in self.fields.items():spin.setValue(transform.value(name,self.frame) if name in TRANSFORM_TRACK_PROPERTIES else getattr(transform,name))
            for name in self.key_buttons:self._sync_key_state(name,transform)
            for name,spin in self.surface_fields.items():spin.setValue(layer.surface_transform.value(name,self.frame) if name in TRANSFORM_TRACK_PROPERTIES else getattr(layer.surface_transform,name))
            for name,spin in self.surface_fields.items():
                track=layer.surface_transform.tracks.get(name);spin.setEnabled(not track or not track.keyframes or track.has_keyframe(self.frame))
            self.advanced_status.setVisible(not layer.advanced_transform_enabled or not layer.surface_transform.is_identity())
            self._sync_advanced_status(layer.advanced_transform_enabled)
        self.setEnabled(layer is not None);self.advanced_body.setVisible(True);self._loading=False

    def set_multi_layers(self,layers,frame=0):
        self.multi_layers=list(layers or []);self.frame=int(frame);multi=len(self.multi_layers)>1;self.multi_help.setVisible(multi);self._loading=True
        if multi:
            self.multi_help.setText(self._localization.text("multi_transform.inspector_local_help") if self._localization else "Multiple layers selected. Property edits apply to each layer's local transform.")
            for name,spin in self.fields.items():
                if name in SUPPORTED_EFFECT_PROPERTIES:
                    mixed=mixed_numeric_value(layer.layer_transform.value(name,self.frame) for layer in self.multi_layers)
                    if mixed is None:spin.lineEdit().setText("—");spin.setProperty("mixedValue",True)
                    else:spin.setValue(mixed);spin.setProperty("mixedValue",False)
                else:spin.setToolTip((spin.toolTip()+"\nPrimary only").strip())
        for mode in ("rotate_x","rotate_y","pivot"):self.gizmo_buttons[mode].setEnabled(not multi)
        self._loading=False

    def _advanced_toggled(self, enabled):
        self.advanced_body.setVisible(True)
        self._sync_advanced_status(bool(enabled))
        if not self._loading and self.layer is not None:
            self.advanced_enabled_changed.emit(self.layer.id, bool(enabled))

    def _sync_advanced_status(self, enabled):
        if self._localization:
            self.advanced_status.setText(self._localization.text("resource_layer.surface_applied" if enabled else "resource_layer.advanced_bypassed"))

    def set_transform_fields(self,layer,frame,names):
        self.layer=layer;self.frame=int(frame);self._loading=True
        try:
            transform=layer.layer_transform
            for name in names:
                if name not in self.fields:continue
                self.fields[name].setValue(transform.value(name,self.frame) if name in TRANSFORM_TRACK_PROPERTIES else getattr(transform,name))
                if name in self.key_buttons:
                    self._sync_key_state(name,transform)
        finally:self._loading=False

    def _sync_key_state(self,name,transform):
        track=transform.tracks.get(name);animated=bool(track and track.keyframes);current=bool(track and track.has_keyframe(self.frame));button=self.key_buttons[name];button.setText("◆" if current else "◇");state="current_key" if current else "animated_no_key" if animated else "static";button.setProperty("keyState",state);button.setStyleSheet("font-weight: bold; color: #ffd43b;" if current else "color: #74c0fc;" if animated else "");self.fields[name].setEnabled(True)
        if self._localization:
            ko=self._localization.language=="ko";button.setToolTip(("현재 프레임에 키가 있습니다. 클릭하면 이 키를 삭제합니다." if ko else "A keyframe exists at the current frame. Click to delete it.") if current else (("이 속성은 애니메이션 중입니다. 값을 변경하면 현재 프레임에 키프레임이 자동으로 추가됩니다. 클릭하면 현재 값으로 키를 추가합니다." if ko else "This property is animated. Changing the value adds a keyframe at the current frame. Click to add the current value.") if animated else ("클릭하면 현재 값으로 키를 추가합니다." if ko else "Click to add a key with the current value.")))

    def _changed(self,*args):
        if self._loading or self.layer is None:return
        name=next((name for name,field in self.fields.items() if field is self.sender()),"")
        if not name:return
        if len(self.multi_layers)>1 and name in SUPPORTED_EFFECT_PROPERTIES:
            self.batch_transform_changed.emit(name,float(self.fields[name].value()));return
        transform=deepcopy(self.layer.layer_transform)
        spin=self.fields[name];track=transform.tracks.get(name);current=transform.value(name,self.frame);value=float(spin.value())
        if current==value:return
        key=next((key for key in track.keyframes if key.frame==self.frame),None) if track else None
        if key is not None:key.value=float(spin.value());transform.revision+=1
        elif track and track.keyframes:transform.set_keyframe(name,self.frame,value,str(self.easings[name].currentData()))
        else:transform.set_property(name,float(spin.value()))
        if name:self.interactive_transform_changed.emit(self.layer.id,transform,name)
        else:self.transform_changed.emit(self.layer.id,transform)

    def _surface_changed(self,*args):
        if self._loading or self.layer is None:return
        name=next((name for name,field in self.surface_fields.items() if field is self.sender()),"")
        if not name:return
        transform=deepcopy(self.layer.surface_transform);track=transform.tracks.get(name);key=next((item for item in track.keyframes if item.frame==self.frame),None) if track else None
        if key is not None:key.value=float(self.surface_fields[name].value());transform.revision+=1
        elif track and track.keyframes:self.set_layer(self.layer,self.frame);return
        else:transform.set_property(name,float(self.surface_fields[name].value()))
        self.surface_transform_changed.emit(self.layer.id,transform)

    def _reset_surface(self):
        if self.layer is None:return
        transform=deepcopy(self.layer.surface_transform);transform.reset_base();self.surface_transform_changed.emit(self.layer.id,transform)

    def _editing_finished(self):
        if not self._loading and self.layer is not None:self.transform_edit_finished.emit(self.layer.id)

    def _add_key(self,name):
        if self.layer is None:return
        track=self.layer.layer_transform.tracks.get(name)
        if track and track.has_keyframe(self.frame):self.keyframe_delete_requested.emit(self.layer.id,name,self.frame)
        else:self.keyframe_requested.emit(self.layer.id,name,self.frame,float(self.fields[name].value()),str(self.easings[name].currentData()))

    def _reset(self):
        if self.layer is None:return
        transform=deepcopy(self.layer.layer_transform);transform.reset_base();self.transform_changed.emit(self.layer.id,transform)

    def _select_mode(self,mode):
        for name,button in self.gizmo_buttons.items():button.setChecked(name==mode)
        if self.layer is not None:self.gizmo_mode_changed.emit(self.layer.id,mode)

    def retranslate_ui(self, localization):
        self._localization=localization;t=localization.text;self.setTitle(t("resource_layer.advanced"));self.setToolTip(t("resource_layer.advanced_bypassed"));self.system_group.setTitle(t("resource_layer.transform"));self.description.setText(t("resource_layer.transform_help"));self.reset.setText(t("resource_layer.transform_reset"));self._sync_advanced_status(self.isChecked())
        self.surface_group.setTitle(t("resource_layer.surface_transform"));self.surface_warning.setText(t("resource_layer.surface_help"));self.surface_reset.setText(t("resource_layer.surface_reset"))
        self.surface_reset.setToolTip(t("resource_layer.surface_reset")+". "+t("resource_layer.surface_help"))
        tips={"rotation_x":"tooltip.resource_layer.rotation_x","rotation_y":"tooltip.resource_layer.rotation_y","rotation_z":"tooltip.resource_layer.rotation_z","position_z":"tooltip.resource_layer.position_z","perspective_strength":"tooltip.resource_layer.perspective"}
        for name,field in self.fields.items():field.setToolTip(t(tips.get(name,"resource_layer.transform_help"))+("\n"+t("tooltip.rotation_revolutions") if name.startswith("rotation_") else ""))
        label_keys={"position_x":"field.position_x","position_y":"field.position_y","position_z":"resource_layer.position_z","rotation_x":"resource_layer.rotation_x","rotation_y":"resource_layer.rotation_y","rotation_z":"resource_layer.rotation_z","scale_x":"field.scale_x","scale_y":"field.scale_y","opacity":"field.opacity","pivot_x":"resource.pivot_x","pivot_y":"resource.pivot_y","perspective_strength":"resource_layer.perspective"}
        for name,field in self.fields.items():self.form.labelForField(field.parentWidget()).setText(t(label_keys[name]))
        for name,field in self.surface_fields.items():
            label=self.surface_form.labelForField(field);label.setText(t("resource_layer.surface_perspective") if name=="perspective_strength" else t(label_keys[name]));field.setToolTip((t("tooltip.resource_layer.surface_perspective") if name=="perspective_strength" else t("resource_layer.surface_help"))+("\n"+t("tooltip.rotation_revolutions") if name.startswith("rotation_") else ""))
        mode_keys={"move":"resource_layer.move_xyz","rotate_x":"resource_layer.rotation_x","rotate_y":"resource_layer.rotation_y","rotate_z":"resource_layer.rotation_z","scale":"gizmo.scale","pivot":"composition.pivot"}
        for name,button in self.gizmo_buttons.items():button.setText(t(mode_keys[name]))
        if self.layer is not None:
            for name in self.key_buttons:self._sync_key_state(name,self.layer.layer_transform)
        else:
            for name,button in self.key_buttons.items():button.setToolTip(self.fields[name].toolTip()+"\n"+t("resource_layer.add_keyframe"))
        for label in self.easing_labels.values():label.setText(t("property.easing"));label.setVisible(True)
        for name,button in self.gizmo_buttons.items():button.setToolTip(t("tooltip.resource_layer.depth_handle") if name=="move" else t(tips.get(name,"resource_layer.transform_help")))
        self.reset.setToolTip(t("resource_layer.transform_reset")+". "+t("resource_layer.transform_help"))

    def set_advanced_expanded(self, expanded: bool) -> None:
        self.setChecked(bool(expanded))

    def is_advanced_expanded(self) -> bool:
        return self.isChecked()
