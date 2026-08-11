"""Low-priority preparation for the interactive Resource Layer proxy."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from threading import Event
from time import perf_counter
from typing import Callable

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtGui import QPixmap
from app.services.runtime_diagnostics import log_exception
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_base_frame


def alpha_composite_layers(
    size: tuple[int, int], layers: tuple[tuple[np.ndarray, float], ...]
) -> np.ndarray:
    """Composite an immutable layer snapshot into an RGBA8 canvas."""
    width,height=size
    output=np.zeros((height,width,4),dtype=np.float32)
    for pixels,opacity in layers:
        source=pixels.astype(np.float32)/255.0
        source_alpha=source[...,3:4]*float(opacity)
        destination_alpha=output[...,3:4]
        combined=source_alpha+destination_alpha*(1.0-source_alpha)
        numerator=source[...,:3]*source_alpha+output[...,:3]*destination_alpha*(1.0-source_alpha)
        output[...,:3]=np.divide(numerator,combined,out=np.zeros_like(numerator),where=combined>0)
        output[...,3:4]=combined
    return np.ascontiguousarray(np.clip(output*255.0,0,255).astype(np.uint8))


def prefix_suffix_composite(
    size: tuple[int, int],
    before: tuple[tuple[np.ndarray, float], ...],
    after: tuple[tuple[np.ndarray, float], ...],
) -> tuple[np.ndarray, np.ndarray]:
    """Return the selected layer's prefix and suffix composites.

    The cache stores the resulting prefix/suffix pair.  Building only the pair
    needed by the current selection avoids retaining every intermediate canvas.
    """
    return alpha_composite_layers(size,before),alpha_composite_layers(size,after)


@dataclass(frozen=True)
class ProxyPrewarmToken:
    project_identity: int
    resource_layer_id: str
    effect_frame: int
    canvas_size: tuple[int, int]
    placement_mode: str
    particle_base_revision: tuple
    resource_revision: tuple
    transform_revision: int
    layer_render_revisions: tuple
    visibility_signature: tuple
    depth_signature: tuple
    request_revision: int = 0

    @property
    def composite_key(self) -> tuple:
        return (
            self.project_identity,self.effect_frame,self.canvas_size,
            self.resource_layer_id,self.layer_render_revisions,
            self.visibility_signature,self.depth_signature,
        )

    def with_request_revision(self, revision: int) -> "ProxyPrewarmToken":
        values=dict(self.__dict__);values["request_revision"]=int(revision)
        return ProxyPrewarmToken(**values)


@dataclass
class ProxyPrewarmPayload:
    token: ProxyPrewarmToken
    base_frame: np.ndarray
    before: tuple[tuple[np.ndarray, float], ...]
    after: tuple[tuple[np.ndarray, float], ...]
    cached_underlay: QPixmap | None = None
    cached_overlay: QPixmap | None = None
    cached_crop: np.ndarray | None = None
    cached_bounds: tuple[int, int, int, int] | None = None
    project: object | None = None
    layer: object | None = None
    frame_index: int = 0


@dataclass
class ProxyPrewarmComputed:
    token: ProxyPrewarmToken
    cropped_rgba: np.ndarray
    alpha_bounds: tuple[int, int, int, int] | None
    underlay_rgba: np.ndarray | None
    overlay_rgba: np.ndarray | None
    cached_underlay: QPixmap | None
    cached_overlay: QPixmap | None
    timings_ms: dict[str, float]

@dataclass(frozen=True)
class ProxyPrewarmFailure:
    token: ProxyPrewarmToken

@dataclass(frozen=True)
class ProxyPrewarmCancelled:
    token: ProxyPrewarmToken


@dataclass
class CompositePixmapEntry:
    key: tuple
    underlay: QPixmap
    overlay: QPixmap
    byte_size: int


class InteractiveCompositeCache:
    """Memory-bounded LRU for full-canvas underlay/overlay pixmaps."""

    def __init__(self, maximum_bytes: int = 64*1024*1024):
        self.maximum_bytes=max(1,int(maximum_bytes));self.current_bytes=0
        self._items: OrderedDict[tuple,CompositePixmapEntry]=OrderedDict()
        self.hits=0;self.misses=0;self.evictions=0

    def get(self,key: tuple) -> CompositePixmapEntry | None:
        value=self._items.get(key)
        if value is None:self.misses+=1;return None
        self._items.move_to_end(key);self.hits+=1;return value

    def put(self,key: tuple,underlay: QPixmap,overlay: QPixmap,byte_size: int) -> CompositePixmapEntry:
        previous=self._items.pop(key,None)
        if previous is not None:self.current_bytes-=previous.byte_size
        value=CompositePixmapEntry(key,underlay,overlay,max(0,int(byte_size)))
        if value.byte_size>self.maximum_bytes:return value
        self._items[key]=value;self.current_bytes+=value.byte_size
        while self.current_bytes>self.maximum_bytes:
            _,removed=self._items.popitem(last=False);self.current_bytes-=removed.byte_size;self.evictions+=1
        return value

    def clear(self, project_identity: int | None = None) -> None:
        if project_identity is None:self._items.clear();self.current_bytes=0;return
        for key in list(self._items):
            if key and key[0]==project_identity:
                self.current_bytes-=self._items.pop(key).byte_size

    def __len__(self) -> int:return len(self._items)


class PrewarmPerformanceCollector:
    def __init__(self):
        self.calls: dict[str,int]={};self.total_ms: dict[str,float]={};self.maximum_ms: dict[str,float]={}
        self.cache_hits=0;self.cache_misses=0;self.stale_rejections=0;self.cancellations=0;self.failures=0

    def record(self,name: str,elapsed_ms: float) -> None:
        self.calls[name]=self.calls.get(name,0)+1
        self.total_ms[name]=self.total_ms.get(name,0.0)+float(elapsed_ms)
        self.maximum_ms[name]=max(self.maximum_ms.get(name,0.0),float(elapsed_ms))

    def average(self,name: str) -> float:
        return self.total_ms.get(name,0.0)/max(1,self.calls.get(name,0))


class _PrewarmWorker(QRunnable):
    def __init__(self,payload: ProxyPrewarmPayload,output: SimpleQueue,cancelled: Event | None=None):
        super().__init__();self.payload=payload;self.output=output;self.cancelled=cancelled or Event()

    def run(self) -> None:
        try:
            self._run_guarded()
        except Exception as exc:
            log_exception("interactive_proxy_prewarm", exc)
            self.output.put(ProxyPrewarmFailure(self.payload.token))

    def _run_guarded(self) -> None:
        timings={};started=perf_counter();frame=self.payload.base_frame
        if self.cancelled.is_set():self.output.put(ProxyPrewarmCancelled(self.payload.token));return
        if frame is None and self.payload.cached_crop is None:
            frame=render_effect_resource_layer_current_base_frame(self.payload.project,self.payload.layer,self.payload.frame_index)
            timings["current_base_render"]=(perf_counter()-started)*1000.0;started=perf_counter()
        if self.cancelled.is_set():self.output.put(ProxyPrewarmCancelled(self.payload.token));return
        if self.payload.cached_crop is not None:
            crop=self.payload.cached_crop;bounds=self.payload.cached_bounds
        else:
            alpha_y,alpha_x=np.nonzero(frame[...,3])
            if len(alpha_x):
                left,right=int(alpha_x.min()),int(alpha_x.max());top,bottom=int(alpha_y.min()),int(alpha_y.max())
                bounds=(left,top,right,bottom);crop=np.ascontiguousarray(frame[top:bottom+1,left:right+1]).copy()
            else:bounds=None;crop=np.empty((0,0,4),dtype=np.uint8)
            timings["proxy_base_alpha_crop"]=(perf_counter()-started)*1000.0
        underlay=overlay=None
        if self.payload.cached_underlay is None or self.payload.cached_overlay is None:
            if self.cancelled.is_set():self.output.put(ProxyPrewarmCancelled(self.payload.token));return
            started=perf_counter();underlay=alpha_composite_layers(self.payload.token.canvas_size,self.payload.before)
            timings["underlay_alpha_composite"]=(perf_counter()-started)*1000.0
            if self.cancelled.is_set():self.output.put(ProxyPrewarmCancelled(self.payload.token));return
            started=perf_counter();overlay=alpha_composite_layers(self.payload.token.canvas_size,self.payload.after)
            timings["overlay_alpha_composite"]=(perf_counter()-started)*1000.0
        self.output.put(ProxyPrewarmComputed(
            self.payload.token,crop,bounds,underlay,overlay,
            self.payload.cached_underlay,self.payload.cached_overlay,timings,
        ))


class InteractiveProxyPrewarmManager(QObject):
    """Debounce requests, compute off-thread, and emit only the latest result."""

    ready=Signal(object)

    def __init__(self,payload_factory: Callable[[ProxyPrewarmToken],ProxyPrewarmPayload|None],parent=None,delay_ms: int=80):
        super().__init__(parent);self.payload_factory=payload_factory;self.delay_ms=int(delay_ms)
        self.collector=PrewarmPerformanceCollector();self._revision=0;self._pending: ProxyPrewarmToken|None=None
        self._queue=SimpleQueue();self._pool=QThreadPool.globalInstance();self._active_revisions:set[int]=set();self._cancelled=Event()
        self._timer=QTimer(self);self._timer.setSingleShot(True);self._timer.timeout.connect(self._start)
        self._poll=QTimer(self);self._poll.timeout.connect(self._drain);self._poll.start(10)

    @property
    def request_revision(self) -> int:return self._revision

    def schedule(self,token: ProxyPrewarmToken,delay_ms: int | None = None) -> ProxyPrewarmToken:
        self._cancelled.set();self._cancelled=Event();self._revision+=1;token=token.with_request_revision(self._revision);self._pending=token
        self._timer.start(self.delay_ms if delay_ms is None else max(0,int(delay_ms)));return token

    def cancel(self) -> None:
        if self._pending is not None or self._active_revisions:self.collector.cancellations+=1
        self._cancelled.set();self._revision+=1;self._pending=None;self._timer.stop()

    def _start(self) -> None:
        token=self._pending;self._pending=None
        if token is None or token.request_revision!=self._revision:return
        started=perf_counter();payload=self.payload_factory(token)
        self.collector.record("payload_prepare",(perf_counter()-started)*1000.0)
        if payload is None:return
        self._active_revisions.add(token.request_revision);self._pool.start(_PrewarmWorker(payload,self._queue,self._cancelled),-1)

    def _drain(self) -> None:
        while True:
            try:result=self._queue.get_nowait()
            except Empty:return
            self._active_revisions.discard(result.token.request_revision)
            if isinstance(result,ProxyPrewarmCancelled):
                self.collector.cancellations+=1;continue
            if isinstance(result,ProxyPrewarmFailure):
                self.collector.failures+=1;continue
            if result.token.request_revision!=self._revision:
                self.collector.stale_rejections+=1;continue
            for name,value in result.timings_ms.items():self.collector.record(name,value)
            self.ready.emit(result)
