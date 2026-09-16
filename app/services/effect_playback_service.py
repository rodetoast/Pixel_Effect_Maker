"""Background exact Effect playback preparation and bounded GUI frame cache."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass,field
from math import ceil
from queue import Empty,SimpleQueue
from threading import Event
from threading import Lock
from time import perf_counter

import numpy as np
from PySide6.QtCore import QObject,QRunnable,QThreadPool,QTimer,Signal
from PySide6.QtGui import QImage,QPixmap

from app.models.effect_resource_layer import EffectLayerTransform3D, PLACEMENT_PARTICLE
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame
from app.services.alpha_composite_service import composite_rgba8_over_float32
from app.models.blend_mode import BLEND_NORMAL, project_layer_blend_mode
from app.services.runtime_diagnostics import log_exception


PLAYBACK_CACHE_MAX_BYTES=256*1024*1024
PLAYBACK_READY_AHEAD=4
PLAYBACK_FULL_PREBUFFER_MAX_FRAMES=30
PLAYBACK_READY_BUFFER_MIN_FRAMES=4
PLAYBACK_READY_BUFFER_MAX_FRAMES=15
PLAYBACK_READY_BUFFER_SECONDS=.5
PLAYBACK_INSTALL_BATCH_SIZE=4
PLAYBACK_PREPARATION_WORKERS=2
PLAYBACK_STATIC_LAYER_CACHE_MAX_BYTES=64*1024*1024

PLAYBACK_STOPPED="stopped"
PLAYBACK_PREPARING="preparing"
PLAYBACK_PLAYING="playing"


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


@dataclass(frozen=True)
class PlaybackPreparationPlan:
    keys:tuple[PlaybackFrameKey,...]
    required_keys:tuple[PlaybackFrameKey,...]
    full_prebuffer:bool
    frame_count:int
    estimated_bytes:int


class PlaybackPerformanceCollector:
    def __init__(self):
        self.calls={};self.total_ms={};self.maximum_ms={}
        self.render_calls=0;self.cache_hits=0;self.cache_misses=0
        self.qimage_creations=0;self.pixmap_creations=0;self.stale_results=0;self.cancelled_workers=0;self.cancelled_frames=0
        self.preparation_requests=0;self.warm_starts=0;self.clock_starts=0;self.underruns=0;self.frame_holds=0;self.frame_drops=0
        self.loop_ready_counts=[];self.static_layer_cache_hits=0;self.static_layer_cache_misses=0
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
    def contains(self,key):return key in self._items
    def __len__(self):return len(self._items)


def playback_relevant_revision(project) -> tuple:
    return (
        tuple((item.id,item.revision) for item in project.resource_compositions),
        tuple((item.id,item.parent_id,item.parent_offset,item.advanced_transform_enabled,item.layer_space_transform.revision,item.surface_transform.revision,item.particle_settings.motion.revision,item.particle_settings.blend_mode) for item in project.effect_resource_layers),
        tuple((layer.id,layer.visible,layer.opacity) for layer in project.layers),
        project.width,project.height,project.fps,project.loop,
    )


def _static_resource_layer_key(project,layer):
    if layer.parent_id is not None:return None
    if layer.placement_mode==PLACEMENT_PARTICLE:return None
    settings=layer.single_settings
    transform=layer.layer_space_transform if layer.advanced_transform_enabled else EffectLayerTransform3D()
    surface=layer.surface_transform if layer.advanced_transform_enabled else EffectLayerTransform3D()
    if settings.start_x!=settings.end_x or settings.start_y!=settings.end_y:return None
    if settings.start_frame>0 or settings.end_frame<len(project.frames)-1:return None
    if any(track.keyframes for track in transform.tracks.values()):return None
    if any(track.keyframes for track in surface.tracks.values()):return None
    composition=next((item for item in project.resource_compositions if item.id==layer.resource_composition_id),None)
    if composition is None or composition.frame_count!=1:return None
    return (layer.id,repr(settings.to_dict()),repr(transform.to_dict()),repr(surface.to_dict()),composition.id,composition.revision,project.width,project.height,project.fps)


class PlaybackStaticLayerCache:
    """Preparation-lifetime exact RGBA reuse for conservatively static layers."""
    def __init__(self,maximum_bytes=PLAYBACK_STATIC_LAYER_CACHE_MAX_BYTES):
        self.maximum_bytes=int(maximum_bytes);self.current_bytes=0;self._items={};self._lock=Lock()
    def get_or_render(self,key,renderer):
        if key is None:return renderer(),False
        with self._lock:
            value=self._items.get(key)
            if value is not None:return value,True
            value=renderer()
            if self.current_bytes+value.nbytes<=self.maximum_bytes:self._items[key]=value;self.current_bytes+=value.nbytes
            return value,False


def _composite(output,source,opacity,blend_mode=BLEND_NORMAL):
    if source is None or source.shape[:2]!=output.shape[:2]:return
    composite_rgba8_over_float32(output,source,opacity,blend_mode)


def render_exact_playback_frame(project,frame_index,preview_frames=None,preview_layer_id=None,static_layer_cache=None,collector=None,solo_preview=False):
    """Render one deterministic exact display frame without mutating Project pixels."""
    started=perf_counter();frame_index=max(0,int(frame_index));project_frame=project.frames[frame_index] if frame_index<len(project.frames) else None
    dynamic={};particle_ms=single_ms=0.0
    for layer in project.effect_resource_layers:
        phase=perf_counter();static_key=_static_resource_layer_key(project,layer)
        if static_layer_cache is None:pixels=render_effect_resource_layer_current_frame(project,layer,frame_index);hit=False
        else:pixels,hit=static_layer_cache.get_or_render(static_key,lambda:render_effect_resource_layer_current_frame(project,layer,frame_index))
        if collector is not None and static_key is not None:
            if hit:collector.static_layer_cache_hits+=1
            else:collector.static_layer_cache_misses+=1
        if layer.placement_mode==PLACEMENT_PARTICLE:particle_ms+=(perf_counter()-phase)*1000.0
        else:single_ms+=(perf_counter()-phase)*1000.0
        if layer.generated_layer_id is not None:dynamic[layer.generated_layer_id]=pixels
    resource_by_generated={item.generated_layer_id:item for item in project.effect_resource_layers}
    has_solo=solo_preview and project.effect_preview_solo_active()
    slots=[index for index,layer in enumerate(project.layers) if layer.id in resource_by_generated]
    ordered=list(project.layers);sorted_resources=sorted((project.layers[index] for index in slots),key=lambda layer:resource_by_generated[layer.id].layer_space_transform.value("position_z",frame_index) if resource_by_generated[layer.id].advanced_transform_enabled else 0.0)
    for slot,layer in zip(slots,sorted_resources,strict=True):ordered[slot]=layer
    composite_started=perf_counter();output=np.zeros((project.height,project.width,4),dtype=np.float32)
    preview=None if preview_frames is None or not 0<=frame_index<len(preview_frames) else preview_frames[frame_index]
    replacement_seen=False
    for layer in ordered:
        if not layer.visible:continue
        logical=resource_by_generated.get(layer.id)
        if logical is not None and not project.effect_effective_visible(logical):continue
        if has_solo and (logical is None or not project.effect_preview_soloed(logical)):continue
        if preview is not None and layer.id==preview_layer_id:source=preview;replacement_seen=True
        else:source=dynamic.get(layer.id,None if project_frame is None else project_frame.layer_pixels.get(layer.id))
        _composite(output,source,layer.opacity,project_layer_blend_mode(project,layer.id))
    if preview is not None and not replacement_seen and not has_solo:_composite(output,preview,1.0,project_layer_blend_mode(project,preview_layer_id))
    rgba=np.ascontiguousarray(np.clip(output*255.0,0,255).astype(np.uint8));total=(perf_counter()-started)*1000.0
    return rgba,{"particle_exact_render":particle_ms,"single_exact_render":single_ms,"layer_alpha_composite":(perf_counter()-composite_started)*1000.0,"exact_frame_generation":total}


class _PlaybackWorker(QRunnable):
    def __init__(self,generation,project,keys,preview_frames,preview_layer_id,queue,cancelled,static_cache,collector):
        super().__init__();self.generation=generation;self.project=project;self.keys=keys;self.preview_frames=preview_frames;self.preview_layer_id=preview_layer_id;self.queue=queue;self.cancelled=cancelled;self.static_cache=static_cache;self.collector=collector
    def run(self):
        try:
            for offset,key in enumerate(self.keys):
                if self.cancelled.is_set():
                    self.queue.put((self.generation,None,None,{"cancelled_frames":len(self.keys)-offset},"cancelled"));return
                rgba,timings=render_exact_playback_frame(self.project,key.frame_index,self.preview_frames,self.preview_layer_id,self.static_cache,self.collector,True)
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
    def cancel_preparation(self):self._cancelled.set();self._generation+=1
    def close(self):self._cancelled.set();self._generation+=1;self._poll.stop();self.cache.clear()
    def key(self,project,render_revision,frame_index,preview_identity=()):
        return PlaybackFrameKey(id(project),int(render_revision),int(frame_index),(project.width,project.height),playback_relevant_revision(project),tuple(preview_identity))
    def get(self,key):
        value=self.cache.get(key)
        if value is None:self.collector.cache_misses+=1
        else:self.collector.cache_hits+=1
        return value
    def ready_count(self,keys):return sum(1 for key in keys if self.cache.contains(key))
    def all_ready(self,keys):return all(self.cache.contains(key) for key in keys)
    def prepare(self,project,render_revision,start_frame=0,preview_frames=None,preview_layer_id=None,preview_identity=()):
        self._cancelled.set();self._cancelled=Event();self._generation+=1;generation=self._generation
        count=len(preview_frames) if preview_frames is not None else len(project.frames)
        if count<1:return PlaybackPreparationPlan((),(),True,0,0)
        start=max(0,min(start_frame,count-1));order=list(range(start,count))
        if project.loop:order+=list(range(0,start))
        estimated=int(project.width)*int(project.height)*4*2*len(order)
        full=count<=PLAYBACK_FULL_PREBUFFER_MAX_FRAMES and estimated<=self.cache.maximum_bytes
        required_count=count if full else min(count,max(PLAYBACK_READY_BUFFER_MIN_FRAMES,min(PLAYBACK_READY_BUFFER_MAX_FRAMES,ceil(project.fps*PLAYBACK_READY_BUFFER_SECONDS))))
        keys=tuple(self.key(project,render_revision,index,preview_identity) for index in order)
        required=keys if full else keys[:required_count]
        missing=[key for key in keys if self.cache.get(key) is None]
        self.collector.preparation_requests+=1
        if not missing:self.collector.warm_starts+=1
        if missing:
            snapshot_started=perf_counter();snapshot=deepcopy(project);preview_snapshot=None if preview_frames is None else [np.ascontiguousarray(frame).copy() for frame in preview_frames]
            self.collector.record("snapshot_copy",(perf_counter()-snapshot_started)*1000.0)
            worker_count=min(PLAYBACK_PREPARATION_WORKERS,len(missing))
            static_cache=PlaybackStaticLayerCache()
            for worker_index in range(worker_count):
                assigned=missing[worker_index::worker_count]
                self._pool.start(_PlaybackWorker(generation,snapshot,assigned,preview_snapshot,preview_layer_id,self._queue,self._cancelled,static_cache,self.collector),-1)
        return PlaybackPreparationPlan(keys,tuple(required),full,count,estimated)
    def _drain(self):
        for _ in range(PLAYBACK_INSTALL_BATCH_SIZE):
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
