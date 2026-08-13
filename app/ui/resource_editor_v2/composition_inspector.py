from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QFormLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from app.models.property_registry import search_properties
from app.models.property_registry import NUMERIC_PROPERTY_SPECS
from app.ui.focus_wheel_widgets import RotationSpinBox, ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from app.ui.tooltip_helper import apply_tooltip


class PropertySearchDialog(QDialog):
    def __init__(self, tracks, localization, parent=None):
        super().__init__(parent); self.localization=localization; self.selected_id=None; layout=QVBoxLayout(self); self.search=QLineEdit(); self.list=QListWidget(); self.add=QPushButton(); self.cancel=QPushButton(); buttons=QHBoxLayout(); buttons.addStretch(); buttons.addWidget(self.cancel); buttons.addWidget(self.add); layout.addWidget(self.search); layout.addWidget(self.list); layout.addLayout(buttons); self.tracks=tracks
        self.search.textChanged.connect(self.refresh); self.list.itemDoubleClicked.connect(lambda item:self.accept_selected()); self.add.clicked.connect(self.accept_selected); self.cancel.clicked.connect(self.reject); self.retranslate(); self.refresh()

    def refresh(self,*args):
        self.list.clear(); language=self.localization.language
        for definition,added in search_properties(self.search.text(),"composition_layer",self.tracks):
            name=definition.name_ko if language=="ko" else definition.name_en; description=definition.description_ko if language=="ko" else definition.description_en; item=QListWidgetItem(f"{name}{' ✓' if added else ''}\n{description}"); item.setData(Qt.ItemDataRole.UserRole,definition.id)
            if added: item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEnabled)
            self.list.addItem(item)

    def accept_selected(self):
        item=self.list.currentItem()
        if item and item.flags()&Qt.ItemFlag.ItemIsEnabled: self.selected_id=str(item.data(Qt.ItemDataRole.UserRole)); self.accept()

    def retranslate(self):
        t=self.localization.text; self.setWindowTitle(t("composition.add_property")); self.search.setPlaceholderText(t("composition.search")); self.add.setText(t("composition.add")); self.cancel.setText(t("v2.cancel"))


class CompositionInspector(QWidget):
    changed=Signal(object,object); use_requested=Signal()

    def __init__(self,parent=None):
        super().__init__(parent); layout=QVBoxLayout(self); self.title=QLabel(); self.name=QLineEdit(); self.info=QLabel(); self.pivot_x=ScrollSafeDoubleSpinBox(); self.pivot_y=ScrollSafeDoubleSpinBox(); [widget.setRange(-4096,4096) for widget in (self.pivot_x,self.pivot_y)]; self.form=QFormLayout(); self.form.addRow(" ",self.name); self.form.addRow(" ",self.pivot_x); self.form.addRow(" ",self.pivot_y); self.center=QPushButton(); self.use=QPushButton(); self.use.setObjectName("useResourceInEffectButton"); self.use.setDefault(True)
        layout.addWidget(self.title); layout.addWidget(self.info); layout.addLayout(self.form); layout.addWidget(self.center); layout.addWidget(self.use); layout.addStretch(); self.composition=None; self._loading=False; self.localization=None
        self.name.editingFinished.connect(self._apply); self.pivot_x.valueChanged.connect(self._apply); self.pivot_y.valueChanged.connect(self._apply); self.center.clicked.connect(self._center); self.use.clicked.connect(self.use_requested)

    def set_composition(self,composition):
        self.composition=composition; self._loading=True
        if composition:
            self.name.setText(composition.name); playback=self.localization.text("v2.loop" if composition.loop else "v2.hold") if self.localization else ""; template=self.localization.text("v2.comp_info") if self.localization else "{width} × {height} · {fps} FPS · {frames}"; self.info.setText(template.format(width=composition.width,height=composition.height,fps=composition.fps,frames=composition.frame_count,playback=playback)); self.pivot_x.setValue(composition.pivot_x); self.pivot_y.setValue(composition.pivot_y)
        self._loading=False

    def _apply(self,*args):
        if self._loading or not self.composition:return
        before={"name":self.composition.name,"pivot_x":self.composition.pivot_x,"pivot_y":self.composition.pivot_y};after={"name":self.name.text().strip() or self.composition.name,"pivot_x":self.pivot_x.value(),"pivot_y":self.pivot_y.value()}
        for key,value in after.items():setattr(self.composition,key,value)
        if before!=after:self.changed.emit(before,after)

    def _center(self):
        if self.composition: self.pivot_x.setValue(self.composition.width/2); self.pivot_y.setValue(self.composition.height/2)

    def retranslate(self,localization):
        self.localization=localization;t=localization.text; self.title.setText(t("v2.composition_inspector")); self.form.labelForField(self.name).setText(t("composition.name")); self.form.labelForField(self.pivot_x).setText(t("v2.output_pivot_x")); self.form.labelForField(self.pivot_y).setText(t("v2.output_pivot_y")); self.center.setText(t("v2.center_output_pivot")); self.use.setText(t("v2.use_in_effect"));apply_tooltip(self.pivot_x,localization,"tooltip.resource.output_pivot",status=False);apply_tooltip(self.pivot_y,localization,"tooltip.resource.output_pivot",status=False);apply_tooltip(self.center,localization,"tooltip.resource.center_output");apply_tooltip(self.use,localization,"tooltip.resource.use");self.set_composition(self.composition)


class LayerInspector(QScrollArea):
    changed=Signal(object,object); mode_changed=Signal(str); add_property_requested=Signal(); full_rotation_requested=Signal(); center_pivot_requested=Signal(); use_requested=Signal(); keyframe_requested=Signal(str,object,str); keyframe_delete_requested=Signal(str); property_value_requested=Signal(str,object); remove_property_requested=Signal(str)

    def __init__(self,parent=None):
        super().__init__(parent); self.setWidgetResizable(True); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); body=QWidget(); body.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.MinimumExpanding); self.layout=QVBoxLayout(body); self.title=QLabel(); self.name=QLineEdit(); self.source=QLabel(); self.source.setWordWrap(True); self.source.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); self.start=ScrollSafeSpinBox(); self.end=ScrollSafeSpinBox(); self.visible=QCheckBox(); self.pivot_x=ScrollSafeDoubleSpinBox(); self.pivot_y=ScrollSafeDoubleSpinBox(); [widget.setRange(-4096,4096) for widget in (self.pivot_x,self.pivot_y)]; self.start.setRange(0,511);self.end.setRange(0,511); self.form=QFormLayout(); self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for widget in (self.name,self.source,self.start,self.end,self.visible,self.pivot_x,self.pivot_y): self.form.addRow(" ",widget)
        self.layout.addWidget(self.title); self.layout.addLayout(self.form); self.center=QPushButton(); self.layout.addWidget(self.center); modes=QGridLayout(); self.mode_buttons={}
        for index,mode in enumerate(("move","rotate_x","rotate_y","rotate","scale","pivot")):
            button=QPushButton();button.setCheckable(True);button.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);button.clicked.connect(lambda checked=False,value=mode:self.mode_changed.emit(value));self.mode_buttons[mode]=button;modes.addWidget(button,index//2,index%2)
        self.mode_buttons["move"].setChecked(True);self.layout.addLayout(modes);self.add_property=QPushButton();self.full_rotation=QPushButton();self.full_rotation.setObjectName("fullRotationButton");self.use=QPushButton();self.use.setObjectName("useResourceInEffectFromLayerButton");self.use.setDefault(True);self.use.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);self.use.setMinimumHeight(36);self.layout.addWidget(self.add_property);self.layout.addWidget(self.full_rotation);self.property_body=QWidget();self.property_body.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.MinimumExpanding);self.property_layout=QVBoxLayout(self.property_body);self.property_layout.setContentsMargins(0,4,0,4);self.layout.addWidget(self.property_body);self.layout.addWidget(self.use);self.layout.addStretch();self.setWidget(body);self.layer=None;self.frame=0;self._loading=False;self.localization=None;self.property_cards={}
        self.name.editingFinished.connect(self._apply);self.start.valueChanged.connect(self._apply);self.end.valueChanged.connect(self._apply);self.visible.toggled.connect(self._apply);self.pivot_x.valueChanged.connect(self._apply);self.pivot_y.valueChanged.connect(self._apply);self.center.clicked.connect(self.center_pivot_requested);self.add_property.clicked.connect(self.add_property_requested);self.full_rotation.clicked.connect(self.full_rotation_requested);self.use.clicked.connect(self.use_requested)

    def set_layer(self,layer,source,frame):
        self.layer,self.frame=layer,frame;self._loading=True
        if layer:
            self.name.setText(layer.name);self.source.setText(source.name if source else "");self.start.setValue(layer.start_frame);self.end.setValue(layer.end_frame);self.visible.setChecked(layer.visible);self.pivot_x.setValue(layer.pivot_x);self.pivot_y.setValue(layer.pivot_y)
        self._loading=False;self._update_visibility_tooltip();self._properties();self._set_locked(bool(layer and layer.locked))

    def _set_locked(self,locked):
        for widget in (self.name,self.start,self.end,self.pivot_x,self.pivot_y,self.center,self.add_property,self.full_rotation):widget.setEnabled(not locked)
        for button in self.mode_buttons.values():button.setEnabled(not locked)
        for values in self.property_cards.values():
            for widget in (*values["editors"],values["easing"],values["keyframe"],values["remove"]):widget.setEnabled(not locked)

    def _update_visibility_tooltip(self):
        if self.localization:apply_tooltip(self.visible,self.localization,"tooltip.visibility.hide" if self.visible.isChecked() else "tooltip.visibility.show",status=False)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.widget():self.widget().setMaximumWidth(max(0,self.viewport().width()))

    def set_mode(self,mode):
        for key,button in self.mode_buttons.items():button.setChecked(key==mode)

    def _apply(self,*args):
        if self._loading or not self.layer:return
        before={key:getattr(self.layer,key) for key in ("name","start_frame","end_frame","visible","pivot_x","pivot_y")};after={"name":self.name.text().strip() or self.layer.name,"start_frame":self.start.value(),"end_frame":max(self.start.value(),self.end.value()),"visible":self.visible.isChecked(),"pivot_x":self.pivot_x.value(),"pivot_y":self.pivot_y.value()}
        for key,value in after.items():setattr(self.layer,key,value)
        if before!=after:self.changed.emit(before,after)
        self._update_visibility_tooltip()

    def _properties(self):
        self.property_cards={}
        while self.property_layout.count():
            item=self.property_layout.takeAt(0);widget=item.widget()
            if widget:widget.deleteLater()
        if not self.layer:return
        for property_id,track in self.layer.tracks.items():
            card=QFrame();card.setObjectName("propertyCard_"+property_id);card.setFrameShape(QFrame.Shape.StyledPanel);card.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred);card_layout=QVBoxLayout(card);card_layout.setContentsMargins(8,6,8,8);header=QHBoxLayout();title=QLabel(self.localization.text("property."+property_id) if self.localization else property_id.title());title.setWordWrap(True);remove=QPushButton("×");remove.setObjectName("removePropertyButton");remove.setFixedSize(28,28);apply_tooltip(remove,self.localization,"tooltip.resource.remove_property");header.addWidget(title,1);header.addWidget(remove);card_layout.addLayout(header);value=track.evaluate(self.frame);editors=[];value_form=QFormLayout();value_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);value_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            values=value if isinstance(value,(list,tuple)) else [value]
            labels=("property.x","property.y") if property_id in {"position","scale"} else ("property.value",)
            for label_key,part in zip(labels,values):
                editor=RotationSpinBox() if property_id in {"rotation","rotation_x","rotation_y"} else ScrollSafeDoubleSpinBox()
                if property_id=="perspective_strength":spec=NUMERIC_PROPERTY_SPECS["composition.perspective"];editor.setRange(spec.minimum,spec.maximum);editor.setSingleStep(spec.step);editor.setProperty("numericSpec","composition.perspective")
                elif property_id=="opacity":spec=NUMERIC_PROPERTY_SPECS["composition.opacity_percent"];editor.setRange(spec.minimum,spec.maximum);editor.setSingleStep(spec.step);editor.setProperty("numericSpec","composition.opacity_percent")
                elif property_id in {"rotation","rotation_x","rotation_y"}:editor.setRange(-36000,36000);editor.setSingleStep(1)
                else:editor.setRange(-4096,4096)
                editor.setDecimals(3);editor.setMinimumWidth(0);editor.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);editor.setSuffix(" %" if property_id in {"scale","opacity"} else "" if property_id in {"rotation","rotation_x","rotation_y","perspective_strength"} else " px");editor.setValue(float(part)*(100 if property_id in {"scale","opacity"} else 1))
                sprite_tip={"rotation_x":"tooltip.resource.sprite_rotation_x","rotation_y":"tooltip.resource.sprite_rotation_y","rotation":"tooltip.resource.sprite_rotation_z","perspective_strength":"tooltip.resource.sprite_perspective"}.get(property_id)
                if sprite_tip and self.localization:apply_tooltip(editor,self.localization,sprite_tip,status=False)
                if property_id in {"rotation","rotation_x","rotation_y"} and self.localization:editor.setToolTip(editor.toolTip()+"\n"+self.localization.text("tooltip.rotation_revolutions"))
                value_form.addRow(self.localization.text(label_key) if self.localization else label_key,editor);editors.append(editor)
            card_layout.addLayout(value_form)
            easing=QComboBox()
            for name in ("Linear","Ease In","Ease Out","Ease In/Out"):easing.addItem(self.localization.text("easing."+name.lower().replace(" ","_").replace("/","_")) if self.localization else name,name)
            existing=track.keyframe_at(self.frame);animated=bool(track.keyframes);easing.setCurrentIndex(max(0,easing.findData(existing.easing if existing else "Linear")))
            easing.setMinimumWidth(0);easing.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);apply_tooltip(easing,self.localization,"tooltip.resource.easing",status=False);key=QPushButton("◆" if existing else "◇");key.setObjectName("addKeyframeButton");key.setFixedSize(34,28);state="current_key" if existing else "animated_no_key" if animated else "static";key.setProperty("keyState",state);key.setStyleSheet("font-weight: bold; color: #ffd43b;" if existing else "color: #74c0fc;" if animated else "");tip=("현재 프레임에 키가 있습니다. 클릭하면 이 키를 삭제합니다." if existing else "현재 프레임에는 키가 없습니다. 값을 변경하면 키가 자동으로 추가됩니다. 클릭하면 현재 값으로 키를 추가합니다." if animated else "정적 속성. 클릭하면 현재 값으로 키프레임을 추가합니다.") if self.localization and self.localization.language=="ko" else ("A keyframe exists at the current frame. Click to delete it." if existing else "This property is animated. Changing the value adds a keyframe at the current frame. Click to add the current value." if animated else "Static property. Click to add a keyframe with the current value.");key.setToolTip(tip);footer=QHBoxLayout();footer.addWidget(QLabel(self.localization.text("property.easing") if self.localization else "Easing"));footer.addWidget(easing,1);footer.addWidget(key);card_layout.addLayout(footer);key.clicked.connect(lambda checked=False,p=property_id,e=editors,c=easing,has=existing is not None:self._key_clicked(p,e,c,has));remove.clicked.connect(lambda checked=False,p=property_id:self.remove_property_requested.emit(p));[editor.valueChanged.connect(lambda value,p=property_id,e=editors:self.property_value_requested.emit(p,self._value(p,e))) for editor in editors];self.property_layout.addWidget(card);self.property_cards[property_id]={"card":card,"editors":editors,"easing":easing,"keyframe":key,"remove":remove,"key_state":state}

    def _key_clicked(self,property_id,editors,easing,has_current_key):
        if has_current_key:self.keyframe_delete_requested.emit(property_id)
        else:self.keyframe_requested.emit(property_id,self._value(property_id,editors),easing.currentData())

    @staticmethod
    def _value(property_id,editors):
        values=[editor.value()/(100 if property_id in {"scale","opacity"} else 1) for editor in editors];return values if property_id in {"position","scale"} else values[0]

    def retranslate(self,localization):
        self.localization=localization;t=localization.text;self.title.setText(t("v2.layer_inspector"))
        for widget,key in ((self.name,"v2.layer_name"),(self.source,"v2.source_asset"),(self.start,"composition.start"),(self.end,"composition.end"),(self.visible,"v2.visible"),(self.pivot_x,"v2.layer_pivot_x"),(self.pivot_y,"v2.layer_pivot_y")):self.form.labelForField(widget).setText(t(key))
        self.center.setText(t("v2.center_layer_pivot"));self.add_property.setText(t("composition.add_property"));self.full_rotation.setText(t("v2.full_rotation"));self.use.setText(t("v2.use_in_effect"))
        apply_tooltip(self.visible,localization,"tooltip.visibility.hide" if self.visible.isChecked() else "tooltip.visibility.show",status=False);apply_tooltip(self.pivot_x,localization,"tooltip.resource.layer_pivot",status=False);apply_tooltip(self.pivot_y,localization,"tooltip.resource.layer_pivot",status=False);apply_tooltip(self.center,localization,"tooltip.resource.center_layer");apply_tooltip(self.add_property,localization,"tooltip.resource.add_property");apply_tooltip(self.full_rotation,localization,"tooltip.resource.full_rotation");apply_tooltip(self.use,localization,"tooltip.resource.use")
        for mode,key in (("move","gizmo.move"),("rotate_x","gizmo.rotate_x"),("rotate_y","gizmo.rotate_y"),("rotate","gizmo.rotate_z"),("scale","gizmo.scale"),("pivot","composition.pivot")):self.mode_buttons[mode].setText(t(key));apply_tooltip(self.mode_buttons[mode],localization,"tooltip.resource.gizmo_"+mode)
        self._properties()
