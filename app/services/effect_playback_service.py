"""Background exact Effect playback preparation and bounded GUI frame cache."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass,field
from queue import Empty,SimpleQueue
from threading import Event
from time import perf_counter

import numpy as np
from PySide6.QtCore import QObject,QRunnable,QThreadPool,QTimer,Signal
from PySide6.QtGui import QImage,QPixmap

from app.models.effect_resource_layer import PLACEMENT_PARTICLE
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame
from app.services.runtime_diagnostics import log_exception


PLAYBACK_CACHE_MAX_BYTES=256*1024*1024
PLAYBACK_READY_AHEAD=4


@dataclass(frozen=True)
class PlaybackFrameKey:
    project_identity:int
    render_revision:int
    frame_index:int
    canvas_size:tuple[int,int]
    relevant_revision:tuple
    preview_identity:tuple


@dataclass
class PlaybackFrame:
    key:PlaybackFrameKey
    rgba:np.ndarray
    pixmap:QPixmap
    byte_size:int
    render_timings_ms:dict[str,float]=field(default_factory=dict)


class PlaybackPerformanceCollector:
    def __init__(self):
        self.calls={};self.total_ms={};self.maximum_ms={}
        self.render_calls=0;self.cache_hits=0;self.cache_misses=0
        self.qimage_creations=0;self.pixmap_creations=0;self.stale_results=0;self.cancelled_workers=0;self.cancelled_frames=0
    def record(self,name,value):
        value=float(value);self.calls[name]=self.calls.get(name,0)+1
        self.total_ms[name]=self.total_ms.get(name,0.0)+value
        self.maximum_ms[name]=max(self.maximum_ms.get(name,0.0),value)
    def average(self,name):return self.total_ms.get(name,0.0)/max(1,self.calls.get(name,0))


class PlaybackFrameCache:
    """GUI-thread-owned exact RGBA/QPixmap LRU with a hard byte limit."""
    def __init__(self,maximum_bytes=PLAYBACK_CACHE_MAX_BYTES):
        self.maximum_bytes=max(1,int(maximum_bytes));self.current_bytes=0;self.evictions=0
        self._items:OrderedDict[PlaybackFrameKey,PlaybackFrame]=OrderedDict()
    def get(self,key):
        value=self._items.get(key)
        if value is not None:self._items.move_to_end(key)
        return value
    def put(self,value):
        previous=self._items.pop(value.key,None)
        if previous is not None:self.current_bytes-=previous.byte_size
        if value.byte_size>self.maximum_bytes:return value
        self._items[value.key]=value;self.current_bytes+=value.byte_size
        while self.current_bytes>self.maximum_bytes:
            _,removed=self._items.popitem(last=False);self.current_bytes-=removed.byte_size;self.evictions+=1
        return value
    def clear(self):self._items.clear();self.current_bytes=0
    def __len__(self):return len(self._items)


def playback_relevant_revision(project) -> tuple:
    return (
        tuple((item.id,item.revision) for item in project.resource_compositions),
        tuple((item.id,item.layer_transform.revision,item.particle_settings.motion.revision) for item in project.effect_resource_layers),
        tuple((layer.id,layer.visible,layer.opacity) for layer in project.layers),
        project.width,project.height,project.fps,project.loop,
    )


def _composite(output,source,opacity):
    if source is None or source.shape[:2]!=output.shape[:2]:return
    src=source.astype(np.float32)/255.0;src_alpha=src[...,3:4]*max(0.0,min(1.0,float(opacity)));dst_alpha=output[...,3:4]
    combined=src_alpha+dst_alpha*(1.0-src_alpha);safe=np.where(combined==0,1.0,combined)
    output[...,:3]=(src[...,:3]*src_alpha+output[...,:3]*dst_alpha*(1.0-src_alpha))/safe;output[...,3:4]=combined


def render_exact_playback_frame(project,frame_index,preview_frames=None,preview_layer_id=None):
    """Render one deterministic exact display frame without mutating Project pixels."""
    started=perf_counter();frame_index=max(0,int(frame_index));project_frame=project.frames[frame_index] if frame_index<len(project.frames) else None
    dynamic={};particle_ms=single_ms=0.0
    for layer in project.effect_resource_layers:
        phase=perf_counter();pixels=render_effect_resource_layer_current_frame(project,layer,frame_index)
        if layer.placement_mode==PLACEMENT_PARTICLE:particle_ms+=(perf_counter()-phase)*1000.0
        else:single_ms+=(perf_counter()-phase)*1000.0
        if layer.generated_layer_id is not None:dynamic[layer.generated_layer_id]=pixels
    resource_by_generated={item.generated_layer_id:item for item in project.effect_resource_layers}
    slots=[index for index,layer in enumerate(project.layers) if layer.id in resource_by_generated]
    ordered=list(project.layers);sorted_resources=sorted((project.layers[index] for index in slots),key=lambda layer:resource_by_generated[layer.id].layer_transform.value("position_z",frame_index))
    for slot,layer in zip(slots,sorted_resources,strict=True):ordered[slot]=layer
    composite_started=perf_counter();output=np.zeros((project.height,project.width,4),dtype=np.float32)
    preview=None if preview_frames is None or not 0<=frame_index<len(preview_frames) else preview_frames[frame_index]
    replacement_seen=False
    for layer in ordered:
        if not layer.visible:continue
        if preview is not None and layer.id==preview_layer_id:source=preview;replacement_seen=True
        else:source=dynamic.get(layer.id,None if project_frame is None else project_frame.layer_pixels.get(layer.id))
        _composite(output,source,layer.opacity)
    if preview is not None and not replacement_seen:_composite(output,preview,1.0)
    rgba=np.ascontiguousarray(np.clip(output*255.0,0,255).astype(np.uint8));total=(perf_counter()-started)*1000.0
    return rgba,{"particle_exact_render":particle_ms,"single_exact_render":single_ms,"layer_alpha_composite":(perf_counter()-composite_started)*1000.0,"exact_frame_generation":total}


class _PlaybackWorker(QRunnable):
    def __init__(self,generation,project,keys,preview_frames,preview_layer_id,queue,cancelled):
        super().__init__();self.generation=generation;self.project=project;self.keys=keys;self.preview_frames=preview_frames;self.preview_layer_id=preview_layer_id;self.queue=queue;self.cancelled=cancelled
    def run(self):
        try:
            for offset,key in enumerate(self.keys):
                if self.cancelled.is_set():
                    self.queue.put((self.generation,None,None,{"cancelled_frames":len(self.keys)-offset},"cancelled"));return
                rgba,timings=render_exact_playback_frame(self.project,key.frame_index,self.preview_frames,self.preview_layer_id)
                if self.cancelled.is_set():
                    self.queue.put((self.generation,None,None,{"cancelled_frames":len(self.keys)-offset-1},"cancelled"));return
                self.queue.put((self.generation,key,rgba,timings,None))
        except Exception as exc:
            log_exception("effect_playback_prepare",exc);self.queue.put((self.generation,None,None,{},exc))


class EffectPlaybackManager(QObject):
    frame_ready=Signal(object)
    preparation_failed=Signal(str)
    def __init__(self,parent=None,maximum_bytes=PLAYBACK_CACHE_MAX_BYTES):
        super().__init__(parent);self.cache=PlaybackFrameCache(maximum_bytes);self.collector=PlaybackPerformanceCollector();self._generation=0;self._queue=SimpleQueue();self._pool=QThreadPool.globalInstance();self._cancelled=Event()
        self._poll=QTimer(self);self._poll.timeout.connect(self._drain);self._poll.start(5)
    @property
    def generation(self):return self._generation
    def invalidate(self):self._cancelled.set();self._generation+=1;self.cache.clear()
    def close(self):self._cancelled.set();self._generation+=1;self._poll.stop();self.cache.clear()
    def key(self,project,render_revision,frame_index,preview_identity=()):
        return PlaybackFrameKey(id(project),int(render_revision),int(frame_index),(project.width,project.height),playback_relevant_revision(project),tuple(preview_identity))
    def get(self,key):
        value=self.cache.get(key)
        if value is None:self.collector.cache_misses+=1
        else:self.collector.cache_hits+=1
        return value
    def prepare(self,project,render_revision,start_frame=0,preview_frames=None,preview_layer_id=None,preview_identity=()):
        self._cancelled.set();self._cancelled=Event();self._generation+=1;generation=self._generation
        count=len(preview_frames) if preview_frames is not None else len(project.frames)
        order=list(range(max(0,min(start_frame,count-1)),count))+list(range(0,max(0,min(start_frame,count-1))))
        # Keep the current frame and the configured ready-ahead window at the
        # front of the single deterministic render queue.  Playback does not
        # block waiting for the rest of a long sequence.
        near=order[:PLAYBACK_READY_AHEAD+1];later=order[PLAYBACK_READY_AHEAD+1:]
        keys=[self.key(project,render_revision,index,preview_identity) for index in near+later]
        missing=[key for key in keys if self.cache.get(key) is None]
        if missing:
            snapshot_started=perf_counter();snapshot=deepcopy(project);preview_snapshot=None if preview_frames is None else [np.ascontiguousarray(frame).copy() for frame in preview_frames]
            self.collector.record("snapshot_copy",(perf_counter()-snapshot_started)*1000.0)
            self._pool.start(_PlaybackWorker(generation,snapshot,missing,preview_snapshot,preview_layer_id,self._queue,self._cancelled),-1)
        return keys
    def _drain(self):
        while True:
            try:generation,key,rgba,timings,error=self._queue.get_nowait()
            except Empty:return
            if error=="cancelled":
                self.collector.cancelled_workers+=1;self.collector.cancelled_frames+=int(timings.get("cancelled_frames",0));continue
            if generation!=self._generation:self.collector.stale_results+=1;continue
            if error is not None:self.preparation_failed.emit(str(error));continue
            self.collector.render_calls+=1
            for name,value in timings.items():self.collector.record(name,value)
            qimage_started=perf_counter();image=QImage(rgba.data,rgba.shape[1],rgba.shape[0],rgba.strides[0],QImage.Format.Format_RGBA8888).copy();self.collector.qimage_creations+=1;self.collector.record("numpy_to_qimage",(perf_counter()-qimage_started)*1000.0)
            pixmap_started=perf_counter();pixmap=QPixmap.fromImage(image);self.collector.pixmap_creations+=1;self.collector.record("qimage_to_qpixmap",(perf_counter()-pixmap_started)*1000.0)
            value=PlaybackFrame(key,rgba,pixmap,int(rgba.nbytes)*2,timings);self.cache.put(value);self.frame_ready.emit(value)
