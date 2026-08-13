"""Small hierarchy-only inspector shared by Resource and Effect editors."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox,QFormLayout,QLabel,QLineEdit,QVBoxLayout,QWidget


class GroupInspector(QWidget):
    rename_requested=Signal(str,str);state_requested=Signal(str,str,bool)

    def __init__(self,parent=None):
        super().__init__(parent);layout=QVBoxLayout(self);self.title=QLabel();self.title.setStyleSheet("font-size: 15px; font-weight: bold;");self.help=QLabel();self.help.setWordWrap(True);self.name=QLineEdit();self.children=QLabel();self.visible=QCheckBox();self.locked=QCheckBox();self.solo=QCheckBox();self.labels=[QLabel() for _ in range(5)];form=QFormLayout()
        for label,field in zip(self.labels,(self.name,self.children,self.visible,self.locked,self.solo)):form.addRow(label,field)
        layout.addWidget(self.title);layout.addWidget(self.help);layout.addLayout(form);layout.addStretch();self.form=form;self.group=None;self.loading=False;self.localization=None;self.name.editingFinished.connect(self._rename);self.visible.toggled.connect(lambda value:self._state("visible",value));self.locked.toggled.connect(lambda value:self._state("locked",value));self.solo.toggled.connect(lambda value:self._state("solo",value))

    def set_group(self,group):
        self.group=group;self.loading=True
        if group:self.name.setText(group.name);self.children.setText(str(len(group.children)));self.visible.setChecked(group.visible);self.locked.setChecked(group.locked);self.solo.setChecked(group.solo);self.name.setEnabled(not group.locked)
        self.loading=False

    def _rename(self):
        if not self.loading and self.group:self.rename_requested.emit(self.group.id,self.name.text())

    def _state(self,field,value):
        if not self.loading and self.group:self.state_requested.emit(self.group.id,field,bool(value))

    def retranslate(self,localization):
        self.localization=localization;t=localization.text;self.title.setText(t("group.inspector"));self.help.setText(t("group.no_transform_help"))
        for label,key in zip(self.labels,("group.name","group.children","group.visible","group.locked","group.solo")):label.setText(t(key))
        self.visible.setToolTip(t("tooltip.group.visibility"));self.locked.setToolTip(t("tooltip.group.lock"));self.solo.setToolTip(t("tooltip.group.solo"))
