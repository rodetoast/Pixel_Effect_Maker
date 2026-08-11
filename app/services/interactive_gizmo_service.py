"""Latest-wins current-frame rendering for Effect Canvas direct manipulation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from time import perf_counter

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from app.services.effect_layer_transform_3d_render_service import transform_rgba_frame
from app.services.effect_resource_layer_render_service import (
    effect_resource_layer_base_frame_key,
    render_effect_resource_layer_current_base_frame,
)
from app.services.runtime_diagnostics import log_exception


@dataclass(frozen=True)
class GizmoRenderRequest:
    revision: int
    project_identity: int
    layer: object
    frame: int
    final: bool


@dataclass
class GizmoRenderResult:
    request: GizmoRenderRequest
    base_rgba: object
    exact_rgba: object
    base_key: tuple
    timings_ms: dict[str, float]
    error: Exception | None = None


class GizmoPerformanceCollector:
    def __init__(self):
        self.calls={};self.total_ms={};self.maximum_ms={}
        self.requests=0;self.submitted=0;self.installed=0;self.stale_results=0;self.cancellations=0
        self.final_exact_installs=0

    def record(self,name,value):
        value=float(value);self.calls[name]=self.calls.get(name,0)+1;self.total_ms[name]=self.total_ms.get(name,0.0)+value
        self.maximum_ms[name]=max(self.maximum_ms.get(name,0.0),value)

    def average(self,name):return self.total_ms.get(name,0.0)/max(1,self.calls.get(name,0))


class _GizmoRenderWorker(QRunnable):
    def __init__(self,project,request,queue):super().__init__();self.project=project;self.request=request;self.queue=queue

    def run(self):
        try:
            started=perf_counter();base=render_effect_resource_layer_current_base_frame(self.project,self.request.layer,self.request.frame)
            base_ms=(perf_counter()-started)*1000.0;started=perf_counter();exact=transform_rgba_frame(base,self.request.layer.layer_transform,self.request.frame)
            self.queue.put(GizmoRenderResult(self.request,base,exact,effect_resource_layer_base_frame_key(self.project,self.request.layer,self.request.frame),
                {"interactive_current_base_render":base_ms,"interactive_current_transform":(perf_counter()-started)*1000.0}))
        except Exception as exc:
            log_exception("interactive_gizmo_render",exc);self.queue.put(GizmoRenderResult(self.request,None,None,(),{},exc))


class InteractiveGizmoRenderManager(QObject):
    """Debounce mouse input and prioritize one-frame previews over background work."""

    ready=Signal(object)
    failed=Signal(str)

    def __init__(self,parent=None,delay_ms=33):
        super().__init__(parent);self.delay_ms=int(delay_ms);self.collector=GizmoPerformanceCollector();self._revision=0;self._pending=None
        self._project=None;self._queue=SimpleQueue();self._pool=QThreadPool.globalInstance()
        self._timer=QTimer(self);self._timer.setSingleShot(True);self._timer.timeout.connect(self._submit_pending)
        self._poll=QTimer(self);self._poll.timeout.connect(self._drain);self._poll.start(4)

    @property
    def revision(self):return self._revision

    def schedule(self,project,layer,frame,final=False,immediate=False):
        self._revision+=1;request=GizmoRenderRequest(self._revision,id(project),deepcopy(layer),int(frame),bool(final));self._pending=request;self._project=project
        self.collector.requests+=1
        if final or immediate:self._timer.stop();self._submit_pending()
        elif not self._timer.isActive():self._timer.start(self.delay_ms)
        return request

    def cancel(self):
        if self._pending is not None:self.collector.cancellations+=1
        self._revision+=1;self._pending=None;self._project=None;self._timer.stop()

    def close(self):self.cancel();self._poll.stop()

    def _submit_pending(self):
        request=self._pending;project=self._project;self._pending=None
        if request is None or project is None:return
        self.collector.submitted+=1
        # Positive priority places direct manipulation ahead of Playback and
        # idle Prewarm workers, both of which use negative priority.
        self._pool.start(_GizmoRenderWorker(project,request,self._queue),1)

    def _drain(self):
        while True:
            try:result=self._queue.get_nowait()
            except Empty:return
            if result.request.revision!=self._revision:
                self.collector.stale_results+=1;continue
            if result.error is not None:self.failed.emit(str(result.error));continue
            for name,value in result.timings_ms.items():self.collector.record(name,value)
            self.collector.installed+=1;self.ready.emit(result)
