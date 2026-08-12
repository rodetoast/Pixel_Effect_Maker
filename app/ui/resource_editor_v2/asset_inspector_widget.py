from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QFormLayout, QVBoxLayout, QWidget

from app.models.source_asset import SourceAsset
from app.ui.focus_wheel_widgets import ScrollSafeDoubleSpinBox
from app.ui.tooltip_helper import apply_tooltip


def asset_frames(asset):
    return [asset.pixels] if isinstance(asset, SourceAsset) else asset.frames


def asset_durations(asset):
    if isinstance(asset, SourceAsset):
        return [100]
    fallback = max(1, round(1000 / max(1, asset.fps)))
    values = asset.frame_durations_ms or [fallback] * len(asset.frames)
    return values if len(values) == len(asset.frames) else [fallback] * len(asset.frames)


class AssetPreviewCanvas(QWidget):
    MIN_ZOOM=0.1;MAX_ZOOM=32.0;FIT_MARGIN=32
    def __init__(self, parent=None):
        super().__init__(parent)
        self.asset=None;self.frame=0;self.zoom=1.0;self.pan=QPointF();self.fit_mode=True;self._panning=False;self._pan_start=QPointF();self._pan_origin=QPointF();self.paint_calls=0
        self.setMinimumSize(320,260);self.setMouseTracking(True);self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_asset(self, asset, frame=0):
        changed=asset is not self.asset;self.asset,self.frame=asset,frame
        if changed:self.fit_to_view()
        else:self.update()

    def _pixels(self):return None if self.asset is None else asset_frames(self.asset)[self.frame]

    def _fit_zoom(self):
        pixels=self._pixels()
        if pixels is None:return 1.0
        raw=min(max(1,self.width()-self.FIT_MARGIN*2)/pixels.shape[1],max(1,self.height()-self.FIT_MARGIN*2)/pixels.shape[0],self.MAX_ZOOM)
        return max(self.MIN_ZOOM,float(max(1,int(raw))) if raw>=1 else float(raw))

    def fit_to_view(self):self.fit_mode=True;self.zoom=self._fit_zoom();self.pan=QPointF();self.update()
    def actual_pixels(self):self.fit_mode=False;self.zoom=1.0;self.pan=QPointF();self.update()

    def image_rect(self):
        pixels=self._pixels()
        if pixels is None:return QRectF()
        width=pixels.shape[1]*self.zoom;height=pixels.shape[0]*self.zoom;center=QPointF(self.width()/2,self.height()/2)+self.pan
        return QRectF(center.x()-width/2,center.y()-height/2,width,height)

    def source_to_widget(self,point):
        rect=self.image_rect();return QPointF(rect.left()+float(point.x())*self.zoom,rect.top()+float(point.y())*self.zoom)

    def pivot_marker_position(self):return QPointF() if self.asset is None else self.source_to_widget(QPointF(self.asset.pivot_x,self.asset.pivot_y))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.fit_mode:self.zoom=self._fit_zoom();self.pan=QPointF()

    def wheelEvent(self,event):
        if self.asset is None:return super().wheelEvent(event)
        delta=event.angleDelta().y()
        if delta==0:event.ignore();return
        old=self.zoom;new=max(self.MIN_ZOOM,min(self.MAX_ZOOM,old*(2.0 if delta>0 else .5)))
        if new==old:event.accept();return
        cursor=event.position();local=(cursor-(QPointF(self.width()/2,self.height()/2)+self.pan))/old;self.fit_mode=False;self.zoom=new;self.pan=cursor-QPointF(self.width()/2,self.height()/2)-local*new;self.update();event.accept()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:self._panning=True;self._pan_start=event.position();self._pan_origin=QPointF(self.pan);self.setCursor(Qt.CursorShape.ClosedHandCursor);event.accept();return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._panning:self.fit_mode=False;self.pan=self._pan_origin+(event.position()-self._pan_start);self.update();event.accept();return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if self._panning and event.button()==Qt.MouseButton.MiddleButton:self._panning=False;self.setCursor(Qt.CursorShape.ArrowCursor);event.accept();return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        self.paint_calls+=1
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#20242b"))
        if self.asset is None:
            return
        pixels=np.ascontiguousarray(self._pixels());rect=self.image_rect();tile=max(4,round(self.zoom*2))
        for y in range(int(rect.top()), int(rect.bottom()) + 1, tile):
            for x in range(int(rect.left()), int(rect.right()) + 1, tile):
                painter.fillRect(x, y, tile, tile, QColor("#dfe3e8") if ((x - int(rect.left())) // tile + (y - int(rect.top())) // tile) % 2 else QColor("#aeb4bc"))
        image = QImage(pixels.data, pixels.shape[1], pixels.shape[0], pixels.strides[0], QImage.Format.Format_RGBA8888).copy()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(rect, QPixmap.fromImage(image), QRectF(0, 0, pixels.shape[1], pixels.shape[0]))
        pivot=self.pivot_marker_position();painter.setRenderHint(QPainter.RenderHint.Antialiasing,True);painter.setPen(QPen(QColor("#ff6b6b"),2));painter.setBrush(QColor(32,36,43,210));painter.drawEllipse(pivot,7,7);painter.drawLine(pivot-QPointF(10,0),pivot+QPointF(10,0));painter.drawLine(pivot-QPointF(0,10),pivot+QPointF(0,10));painter.setPen(QColor("#ffffff"));painter.drawText(pivot+QPointF(10,-8),"P")


class AssetFrameStrip(QListWidget):
    frame_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setMaximumHeight(62)
        self.currentRowChanged.connect(lambda row: row >= 0 and self.frame_selected.emit(row))

    def set_asset(self, asset, frame=0):
        self.blockSignals(True)
        self.clear()
        if asset:
            for index in range(len(asset_frames(asset))):
                self.addItem(QListWidgetItem(str(index + 1)))
            self.setCurrentRow(frame)
        self.blockSignals(False)


class AssetInspectorWidget(QWidget):
    create_requested = Signal()
    reimport_requested = Signal()
    pivot_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.info = QLabel()
        self.pivot_x = ScrollSafeDoubleSpinBox(); self.pivot_y = ScrollSafeDoubleSpinBox()
        for widget in (self.pivot_x, self.pivot_y): widget.setRange(-4096, 4096)
        self.form = QFormLayout(); self.form.addRow(" ", self.pivot_x); self.form.addRow(" ", self.pivot_y)
        self.center_button = QPushButton(); self.reimport_button = QPushButton(); self.create_button = QPushButton()
        self.create_button.setObjectName("createResourceFromAssetButton")
        self.create_button.setDefault(True)
        layout.addWidget(self.title); layout.addWidget(self.info); layout.addLayout(self.form)
        for widget in (self.center_button, self.reimport_button, self.create_button): layout.addWidget(widget)
        layout.addStretch()
        self.create_button.clicked.connect(self.create_requested); self.reimport_button.clicked.connect(self.reimport_requested)
        self.center_button.clicked.connect(self._center)
        self.pivot_x.valueChanged.connect(self._pivot); self.pivot_y.valueChanged.connect(self._pivot)
        self.asset = None; self._loading = False

    def set_asset(self, asset):
        self.asset = asset; self._loading = True
        if asset:
            self.info.setText(f"{asset.source_format.upper()} · {asset.width} × {asset.height} · {len(asset_frames(asset))}")
            self.pivot_x.setValue(asset.pivot_x); self.pivot_y.setValue(asset.pivot_y)
        self._loading = False

    def _pivot(self, *args):
        if not self._loading and self.asset: self.pivot_changed.emit(self.pivot_x.value(), self.pivot_y.value())

    def _center(self):
        if self.asset:
            self.pivot_x.setValue(self.asset.width / 2); self.pivot_y.setValue(self.asset.height / 2)

    def retranslate(self, localization):
        t = localization.text
        self.title.setText(t("v2.asset_inspector"))
        self.form.labelForField(self.pivot_x).setText(t("v2.asset_pivot_x")); self.form.labelForField(self.pivot_y).setText(t("v2.asset_pivot_y"))
        self.center_button.setText(t("v2.center_asset_pivot")); self.reimport_button.setText(t("resource.reimport")); self.create_button.setText(t("v2.create_from_asset"))
        apply_tooltip(self.pivot_x,localization,"tooltip.resource.asset_pivot",status=False);apply_tooltip(self.pivot_y,localization,"tooltip.resource.asset_pivot",status=False)
        apply_tooltip(self.center_button,localization,"tooltip.resource.center_asset");apply_tooltip(self.reimport_button,localization,"tooltip.resource.reimport");apply_tooltip(self.create_button,localization,"tooltip.resource.create_from_asset")
