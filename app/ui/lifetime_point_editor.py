"""Bounded lifetime point authoring, separate from composition timeline keys."""
from copy import deepcopy
from dataclasses import replace

from PySide6.QtCore import Signal, QSignalBlocker
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QPushButton, QLabel, QColorDialog, QSizePolicy

from app.models.particle_emitter import LifetimeScalarModulation, LifetimeColorModulation, LifetimeScalarPoint, LifetimeColorPoint, LIFETIME_POINT_MAX
from app.models.resource_composition import EASINGS
from app.services.lifetime_modulation_service import evaluate_scalar_points, evaluate_lifetime_color_component
from .focus_wheel_widgets import ScrollSafeDoubleSpinBox, FocusWheelComboBox


class LifetimePointEditor(QWidget):
    changed = Signal()

    def __init__(self, channel, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._loading = False
        self.curve = LifetimeColorModulation(True) if channel == "color" else LifetimeScalarModulation(True)
        self._ko = False
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 4, 0, 4)
        self.title = QLabel(); layout.addWidget(self.title)
        self.list = QListWidget(); self.list.setMinimumWidth(0); self.list.setMaximumHeight(112)
        self.list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.list)
        self.form = QFormLayout(); self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.time = ScrollSafeDoubleSpinBox(); self.time.setRange(0, 100); self.time.setDecimals(4); self.time.setSingleStep(.1); self.time.setSuffix(" %")
        self.value = ScrollSafeDoubleSpinBox(); self.value.setRange(0, 1 if channel == "opacity" else 16); self.value.setDecimals(6)
        self.color = QPushButton()
        self.easing = FocusWheelComboBox()
        for easing in ("Linear", "Ease In", "Ease Out", "Ease In/Out"): self.easing.addItem(easing, easing)
        for widget in (self.time, self.value, self.color, self.easing):
            widget.setMinimumWidth(0); widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.form.addRow("Time", self.time); self.form.addRow("Color" if channel == "color" else "Value", self.color if channel == "color" else self.value); self.form.addRow("Easing →", self.easing)
        layout.addLayout(self.form)
        buttons = QHBoxLayout(); self.add = QPushButton(); self.remove = QPushButton()
        for button in (self.add, self.remove): button.setMinimumWidth(0); button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed); buttons.addWidget(button)
        layout.addLayout(buttons)
        self.status = QLabel(); self.status.setWordWrap(True); self.status.setMinimumWidth(0); layout.addWidget(self.status)
        self.list.currentRowChanged.connect(self._select)
        self.time.valueChanged.connect(lambda value: self.edit_point("time", value / 100))
        self.value.valueChanged.connect(lambda value: self.edit_point("value", value))
        self.easing.currentIndexChanged.connect(lambda *_: self.edit_point("easing_to_next", self.easing.currentData()))
        self.color.clicked.connect(self.choose_color); self.add.clicked.connect(self.add_point); self.remove.clicked.connect(self.remove_point)
        self.retranslate(False)
        self.set_curve(self.curve)

    def retranslate(self, ko):
        self._ko = ko
        labels={"Linear":"선형","Ease In":"가속","Ease Out":"감속","Ease In/Out":"느리게 시작/종료"}
        with QSignalBlocker(self.easing):
            for index in range(self.easing.count()):
                value=self.easing.itemData(index);self.easing.setItemText(index,labels[value] if ko else value)
        names = {"scale": ("Scale over Lifetime", "수명별 크기"), "opacity": ("Opacity over Lifetime", "수명별 불투명도"), "color": ("Color over Lifetime", "수명별 RGB 색상")}
        self.title.setText(names[self.channel][int(ko)])
        self.add.setText("+ 지점" if ko else "+ Point"); self.remove.setText("− 지점" if ko else "− Point")
        self.form.labelForField(self.time).setText("시간" if ko else "Time")
        self.form.labelForField(self.color if self.channel == "color" else self.value).setText(("RGB 색상" if ko else "RGB Color") if self.channel == "color" else ("값" if ko else "Value"))
        self.form.labelForField(self.easing).setText("다음 구간 보간 →" if ko else "Easing →")
        self.time.setToolTip("내부 지점만 수정 가능. 이웃 시간 사이여야 합니다." if ko else "Internal points only. Time must stay strictly between neighbors.")
        self.add.setToolTip("가장 큰 간격의 중간에 현재 평가값과 Linear 보간으로 추가합니다." if ko else "Insert at the largest gap midpoint using its evaluated value and Linear easing.")
        self.remove.setToolTip("선택한 내부 지점을 제거합니다. 끝점은 제거할 수 없습니다." if ko else "Remove the selected internal point. Endpoints cannot be removed.")
        self.easing.setToolTip("선택한 지점에서 다음 지점까지의 보간입니다. 마지막 지점에는 적용되지 않습니다." if ko else "Outgoing segment easing. Not used on the last point.")
        self.value.setToolTip("타임라인 키가 아닌 입자 수명 내 값입니다." if ko else "Particle lifetime value, not a composition timeline key.")
        self.color.setToolTip("RGB 곱셈 색조만 편집합니다. 알파는 불투명도 곡선에서 편집합니다." if ko else "RGB multiplication tint only. Alpha is edited in the opacity curve.")
        self.list.setToolTip("지점을 선택하여 시간, 값, 다음 구간 보간을 편집합니다." if ko else "Select a point to edit its time, value, and outgoing easing.")

    def set_curve(self, curve, selected=None):
        self._loading = True
        row = self.list.currentRow() if selected is None else selected
        self.curve = deepcopy(curve)
        with QSignalBlocker(self.list):
            self.list.clear()
            for i, point in enumerate(curve.points):
                value = "#%02X%02X%02X" % point.rgb if self.channel == "color" else f"{point.value:g}"
                self.list.addItem(f"{point.time * 100:g}%   {value}   {point.easing_to_next if i < len(curve.points)-1 else '—'}")
            self.list.setCurrentRow(min(max(0, row), len(curve.points)-1))
        self._select(self.list.currentRow())
        self.add.setEnabled(len(curve.points) < LIFETIME_POINT_MAX)
        self._loading = False

    def _select(self, row):
        if row < 0 or row >= len(self.curve.points):
            self.remove.setEnabled(False); return
        point = self.curve.points[row]
        for control in (self.time, self.value, self.easing):
            with QSignalBlocker(control):
                if control is self.time: control.setValue(point.time * 100)
                elif control is self.value and self.channel != "color": control.setValue(point.value)
                elif control is self.easing: control.setCurrentIndex(control.findData(point.easing_to_next))
        self.time.setEnabled(0 < row < len(self.curve.points)-1)
        self.easing.setEnabled(row < len(self.curve.points)-1)
        self.remove.setEnabled(0 < row < len(self.curve.points)-1)
        if self.channel == "color":
            hex_value = "#%02X%02X%02X" % point.rgb
            self.color.setText("■ " + hex_value)
            self.color.setStyleSheet(f"background-color:{hex_value};color:{'#000000' if sum(point.rgb)>420 else '#FFFFFF'}")

    def _accept(self, points, row):
        candidate = deepcopy(self.curve); candidate.points = tuple(points)
        try:
            candidate.validate()
            if self.channel == "opacity" and any(p.value > 1 for p in candidate.points): raise ValueError("opacity must be 0..1")
        except (ValueError, TypeError):
            self.status.setText("입력이 거부되었습니다. 끝점, 범위, 이웃 시간 순서를 확인하세요." if self._ko else "Rejected: check endpoints, value range, and strictly increasing neighbor times.")
            self.set_curve(self.curve, row)
            return False
        if candidate == self.curve:
            self.set_curve(self.curve, row); return False
        self.status.clear(); self.set_curve(candidate, row); self.changed.emit(); return True

    def edit_point(self, name, value):
        if self._loading: return False
        row = self.list.currentRow()
        if row < 0: return False
        if name == "time" and row in (0, len(self.curve.points)-1): return False
        if name == "easing_to_next" and row == len(self.curve.points)-1: return False
        points = list(self.curve.points); points[row] = replace(points[row], **{name: value})
        return self._accept(points, row)

    def add_point(self):
        if len(self.curve.points) >= LIFETIME_POINT_MAX: return False
        points = self.curve.points
        index = max(range(len(points)-1), key=lambda i: points[i+1].time-points[i].time)
        time = (points[index].time+points[index+1].time)/2
        if self.channel == "color":
            channel = deepcopy(self.curve); channel.enabled = True
            rgb = tuple(round(evaluate_lifetime_color_component(channel, time, c)*255) for c in range(3))
            point = LifetimeColorPoint(time, rgb)
        else: point = LifetimeScalarPoint(time, evaluate_scalar_points(points, time))
        return self._accept((*points[:index+1], point, *points[index+1:]), index+1)

    def remove_point(self):
        row = self.list.currentRow()
        if not 0 < row < len(self.curve.points)-1: return False
        points = self.curve.points
        return self._accept((*points[:row], *points[row+1:]), row-1)

    def choose_color(self):
        row = self.list.currentRow()
        if row < 0 or self.channel != "color": return
        selected = QColorDialog.getColor(QColor(*self.curve.points[row].rgb), self, "RGB 색상" if self._ko else "RGB Color")
        if selected.isValid(): self.edit_point("rgb", (selected.red(), selected.green(), selected.blue()))
