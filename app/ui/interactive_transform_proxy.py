"""Canvas-only fast preview state for Resource Layer 2.5D editing."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QImage, QPixmap, QPolygonF, QTransform

from app.models.effect_resource_layer import EffectLayerTransform3D
from app.services.effect_layer_transform_3d_render_service import projected_quad


@dataclass
class ProxyBaseImage:
    key: tuple
    rgba: np.ndarray
    alpha_bounds: tuple[int, int, int, int] | None
    image: QImage | None
    pixmap: QPixmap | None


class ProxyBaseImageCache:
    """Own copied crop memory and its GUI representations once per base revision."""

    def __init__(self, maximum: int = 48, maximum_bytes: int = 32*1024*1024):
        self.maximum = maximum;self.maximum_bytes=max(1,int(maximum_bytes));self.current_bytes=0
        self._items: OrderedDict[tuple, ProxyBaseImage] = OrderedDict()
        self.qimage_creations = 0
        self.qpixmap_creations = 0
        self.alpha_bounds_scans = 0

    def get(self, key: tuple, frame: np.ndarray) -> ProxyBaseImage:
        cached = self._items.get(key)
        if cached is not None:
            self._items.move_to_end(key)
            return cached
        self.alpha_bounds_scans += 1
        alpha_y, alpha_x = np.nonzero(frame[..., 3])
        if not len(alpha_x):
            value = ProxyBaseImage(key, np.empty((0, 0, 4), dtype=np.uint8), None, None, None)
        else:
            left, right = int(alpha_x.min()), int(alpha_x.max())
            top, bottom = int(alpha_y.min()), int(alpha_y.max())
            rgba = np.ascontiguousarray(frame[top:bottom + 1, left:right + 1]).copy()
            image = QImage(
                rgba.data, rgba.shape[1], rgba.shape[0], rgba.strides[0],
                QImage.Format.Format_RGBA8888,
            ).copy()
            pixmap = QPixmap.fromImage(image)
            self.qimage_creations += 1; self.qpixmap_creations += 1
            value = ProxyBaseImage(key, rgba, (left, top, right, bottom), image, pixmap)
        return self.put(value)

    def peek(self,key: tuple) -> ProxyBaseImage | None:
        value=self._items.get(key)
        if value is not None:self._items.move_to_end(key)
        return value

    def put(self,value: ProxyBaseImage) -> ProxyBaseImage:
        previous=self._items.pop(value.key,None)
        if previous is not None:self.current_bytes-=int(previous.rgba.nbytes)
        if int(value.rgba.nbytes)>self.maximum_bytes:return value
        self._items[value.key]=value;self.current_bytes+=int(value.rgba.nbytes)
        while len(self._items)>self.maximum or self.current_bytes>self.maximum_bytes:
            _,removed=self._items.popitem(last=False);self.current_bytes-=int(removed.rgba.nbytes)
        return value

    def clear(self, layer_id: str | None = None) -> None:
        if layer_id is None:
            self._items.clear();self.current_bytes=0; return
        for key in list(self._items):
            if key and key[0] == layer_id:
                removed=self._items.pop(key,None)
                if removed is not None:self.current_bytes-=int(removed.rgba.nbytes)


@dataclass
class InteractiveTransformProxyState:
    resource_layer_id: str
    frame: int
    base_key: tuple
    base: ProxyBaseImage
    active: bool = True
    pending_transform: EffectLayerTransform3D | None = None
    applied_transform: EffectLayerTransform3D | None = None
    transform_revision: int = -1
    last_applied_revision: int = -1
    render_scheduled: bool = False
    render_in_progress: bool = False
    projected_quad: QPolygonF = field(default_factory=QPolygonF)
    previous_projected_bounds: QRect = field(default_factory=QRect)
    current_projected_bounds: QRect = field(default_factory=QRect)
    paint_signature: tuple | None = None
    depth_order_signature: tuple = field(default_factory=tuple)
    underlay_pixmap: QPixmap | None = None
    overlay_pixmap: QPixmap | None = None
    prewarm_token: object | None = None

    def queue(self, transform: EffectLayerTransform3D) -> None:
        self.pending_transform = deepcopy(transform)
        self.transform_revision = int(transform.revision)
        self.render_scheduled = True


def proxy_projected_quad(
    bounds: tuple[int, int, int, int] | None,
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
) -> tuple[np.ndarray | None, bool]:
    """Use the exact renderer's shared projection geometry for the alpha crop."""
    if bounds is None:
        return None, True
    left, top, right, bottom = bounds
    destination, valid = projected_quad(
        (left - .5, top - .5, right + .5, bottom + .5),
        transform, canvas_width, canvas_height,
    )
    return destination, bool(valid.all() and np.isfinite(destination).all())


def projective_pixmap_transform(pixmap: QPixmap, destination: QPolygonF) -> QTransform | None:
    if pixmap.isNull() or len(destination) != 4:
        return None
    source = QPolygonF((
        QPointF(0, 0), QPointF(pixmap.width(), 0),
        QPointF(pixmap.width(), pixmap.height()), QPointF(0, pixmap.height()),
    ))
    transform = QTransform.quadToQuad(source, destination)
    return transform if transform.isInvertible() else None
