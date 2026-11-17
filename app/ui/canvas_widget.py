"""Integer-scaled pixel canvas widget."""

from __future__ import annotations

import numpy as np
from copy import deepcopy
import math
from time import perf_counter
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF, QWheelEvent
from PySide6.QtWidgets import QWidget
from .layout_metrics import GIZMO_OUTLINE_WIDTH, GIZMO_HANDLE_RADIUS, GIZMO_ACTIVE_HANDLE_RADIUS, GIZMO_HIT_RADIUS

from app.models.project import Project
from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.effect_resource_layer import EffectLayerTransform3D,PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings
from app.models.blend_mode import BLEND_NORMAL, project_layer_blend_mode
from app.services.alpha_composite_service import composite_rgba8_over_float32
from app.services.particle_render_service import particle_motion_guide, project_particle_billboard, representative_particle_guide
from app.services.layer_parenting_service import effect_local_affine, resolve_world_affines


RESOURCE_TRANSFORM_HANDLE_PROPERTIES={
    "center":("position_x","position_y"),"x":("position_x",),"y":("position_y",),"z":("position_z",),
    "rotate_x":("rotation_x",),"rotate_y":("rotation_y",),"rotate_z":("rotation_z",),
    "scale":("scale_x","scale_y"),"pivot":("pivot_x","pivot_y"),
}
from app.services.resource_composition_render_service import render_composition_frames
from app.services.layer_space_transform_service import project_local_point,project_local_points,projected_local_axes,transform_layer_space_rgba_frame,unproject_layer_space_point
from app.services.effect_render_service import render_transformed_source
from app.models.frame import empty_pixels
from app.models.source_asset import SourceAsset
from app.ui.interactive_transform_proxy import (
    InteractiveTransformProxyState, ProxyBaseImage, ProxyBaseImageCache,
    projective_pixmap_transform, proxy_projected_quad,
)
from app.ui.interactive_proxy_prewarm import (
    InteractiveCompositeCache, ProxyPrewarmComputed, ProxyPrewarmPayload,
    ProxyPrewarmToken,
)


class CanvasWidget(QWidget):
    """Render the current frame over a checkerboard without pixel smoothing."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self._project_size: tuple[int, int] | None = None
        self.frame_index = 0
        self.layer_index = 0
        self.zoom = 8
        self.pan_offset = QPointF()
        self._panning = False
        self._pan_last = QPointF()
        self.preview_frames: list[np.ndarray] | None = None
        self.preview_layer_id: str | None = None
        self.preview_badge_text = "PREVIEW"
        self.gizmo_generator_id: str | None = None
        self.gizmo_settings = None
        self.gizmo_mode = "move"
        self.gizmo_edit_end = False
        self.gizmo_locked = False
        self._gizmo_drag = False
        self._gizmo_before = None
        self.effect_guide_id: str | None = None
        self.effect_guide_kind: str | None = None
        self.effect_guide_settings = None
        self._guide_identifier: str | None = None
        self.effect_guide_locked = False
        self.show_effect_guides = True
        self._guide_handle: str | None = None
        self._guide_hover: str | None = None
        self._guide_before = None
        self._guide_last_canvas_point: tuple[int, int] | None = None
        self._ghost_cache: dict[tuple, list[QPixmap]] = {}
        self.resource_transform_id=None;self.resource_transform=None;self.resource_transform_mode="move";self._resource_transform_drag=None;self._resource_transform_before=None;self._resource_transform_start=None;self._resource_transform_hover=None;self._resource_rotation_last_angle=None;self._resource_rotation_accumulated=None;self._resource_parent_prefix=None;self.resource_transform_tooltips={};self.multi_resource_transform_context=None;self._resource_multi_start_angle=0.0
        self.resource_transform_changed_fields: tuple[str,...] = ()
        self.interactive_transform_proxy: InteractiveTransformProxyState | None = None
        self.playback_pixmap:QPixmap|None=None;self.playback_pixmap_frame:int|None=None;self.playback_pixmap_key=None;self.playback_mode=False
        self.playback_display_stats={"cached_paints":0,"fallback_paints":0,"cached_draw_ms":0.0,"cached_draw_max_ms":0.0}
        self.interaction_stats={"calls":{},"total_ms":{},"maximum_ms":{},"full_updates_without_rect":0,"partial_paints":0,"full_paints":0}
        self.proxy_base_image_cache=ProxyBaseImageCache()
        self.proxy_composite_cache=InteractiveCompositeCache()
        self.proxy_stats={"apply_calls":0,"motion_apply_calls":0,"motion_composite_waits":0,"paint_calls":0,"paint_skips":0,"depth_rebuilds":0,"partial_updates":0,"full_updates":0,"overlap_rejections":0,"prewarm_installs":0,"prewarm_hits":0,"prewarm_misses":0}
        self.last_proxy_dirty_rect=QRect()
        self.last_prewarm_install_timings={}
        self.last_prewarm_payload_timings={}
        self.setMinimumSize(320, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def _record_interaction(self,name,started):
        elapsed=(perf_counter()-started)*1000.0;stats=self.interaction_stats
        stats["calls"][name]=stats["calls"].get(name,0)+1;stats["total_ms"][name]=stats["total_ms"].get(name,0.0)+elapsed
        stats["maximum_ms"][name]=max(stats["maximum_ms"].get(name,0.0),elapsed);return elapsed

    def set_project(self, project: Project) -> None:
        size = (project.width, project.height)
        context_changed = self.project is not project or self._project_size != size
        self.project = project
        self._project_size = size
        self.frame_index = 0
        self.layer_index = 0
        if context_changed:
            self.clear_playback_frame(update=False)
            self.clear_interactive_transform_proxy(update=False)
            self.proxy_base_image_cache.clear()
            self.proxy_composite_cache.clear()
            self.pan_offset = QPointF()
            self._ghost_cache.clear()
            self._fit_initial_zoom()
        self.update()

    def set_preview(
        self, frames: list[np.ndarray], generated_layer_id: str | None
    ) -> None:
        """Display transient frames without writing them into the project."""
        self.clear_interactive_transform_proxy(update=False)
        self.preview_frames = frames or None
        self.preview_layer_id = generated_layer_id
        if self.preview_frames is not None:
            self.frame_index = min(self.frame_index, len(self.preview_frames) - 1)
        self.update()

    def clear_preview(self) -> None:
        self.clear_interactive_transform_proxy(update=False)
        self.preview_frames = None
        self.preview_layer_id = None
        if self.project is not None:
            self.frame_index = min(self.frame_index, len(self.project.frames) - 1)
        self.update()

    def set_gizmo(self, generator_id: str | None, settings=None, *, mode: str = "move", edit_end: bool = False, locked: bool = False) -> None:
        self.gizmo_generator_id = generator_id
        self.gizmo_settings = deepcopy(settings)
        self.gizmo_mode = mode
        self.gizmo_edit_end = edit_end
        self.gizmo_locked = locked
        self.update()

    def set_effect_guide(self, identifier: str | None, kind: str | None = None, settings=None, *, locked: bool = False) -> None:
        # A render/inspector refresh may arrive while a drag is active.  The
        # gesture owns its press-time target and settings until release/cancel.
        if self._guide_identifier is not None:return
        self.effect_guide_id = identifier
        self.effect_guide_kind = kind
        self.effect_guide_settings = deepcopy(settings)
        self.effect_guide_locked = bool(locked)
        self._guide_handle = self._guide_hover = None
        self.update()

    def set_effect_guides_visible(self, visible: bool) -> None:
        self.show_effect_guides = bool(visible)
        if not visible:self._guide_hover=None;self._resource_transform_hover=None;self.setToolTip("")
        self.update()

    def set_resource_layer_transform(self, identifier=None, transform=None, *, mode="move") -> None:
        if self.interactive_transform_proxy is not None and self.interactive_transform_proxy.resource_layer_id!=identifier:
            self.clear_interactive_transform_proxy(update=False)
        self.resource_transform_id=identifier;self.resource_transform=deepcopy(transform);self.resource_transform_mode=mode;self._resource_transform_drag=None;self._resource_parent_prefix=None;self.multi_resource_transform_context=None
        if identifier and self.project is not None:
            layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
            if layer is not None and layer.parent_id is not None:
                worlds=resolve_world_affines(self.project.effect_resource_layers,self.frame_index,lambda item,frame:effect_local_affine(item,frame,self.project));local=effect_local_affine(layer,self.frame_index,self.project)
                try:self._resource_parent_prefix=worlds[layer.id]@np.linalg.inv(local)
                except np.linalg.LinAlgError:self._resource_parent_prefix=None
        for key in list(self._ghost_cache):
            if isinstance(key,tuple) and key and key[0]=="2.5d":self._ghost_cache.pop(key,None)
        self.update()

    def set_multi_resource_layer_transform(self,context,*,mode="move",gizmo_enabled=True):
        self.clear_interactive_transform_proxy(update=False);self.multi_resource_transform_context=context;self.resource_transform_mode=mode;self.resource_transform_id="__multi__" if context and gizmo_enabled else None;self._resource_transform_drag=None;self._resource_parent_prefix=None
        if context and self.project is not None:
            self.resource_transform=EffectLayerTransform3D(position_x=context.pivot[0]-self.project.width/2,position_y=context.pivot[1]-self.project.height/2)
        else:self.resource_transform=None
        self.update()

    def set_resource_transform_tooltips(self,values) -> None:
        self.resource_transform_tooltips=dict(values)

    def resource_transform_handle_positions(self) -> dict[str,QPointF]:
        if self.project is None or self.resource_transform is None:return {}
        projected,valid=projected_local_axes(self.resource_transform,self.project.width,self.project.height,self.frame_index,42/max(.001,self.zoom),post_affine=self._resource_parent_prefix)
        if not valid.all():return {}
        points=[self.canvas_to_widget(float(x),float(y)) for x,y in projected]
        center,x_axis,y_axis,z_axis=points
        z_handle=z_axis
        if math.hypot(z_axis.x()-center.x(),z_axis.y()-center.y())<18:z_handle=center+QPointF(30,-30)
        t=self.resource_transform.evaluated(self.frame_index);pivot=np.array((self.project.width/2+t.pivot_x,self.project.height/2+t.pivot_y,0.0));r=42/max(.001,self.zoom)
        z_ring=project_local_point(pivot[0]+r/math.sqrt(2),pivot[1]+r/math.sqrt(2),0,self.resource_transform,self.project.width,self.project.height,self.frame_index)
        rotate_z=self.canvas_to_widget(z_ring.x,z_ring.y) if z_ring.valid else center+QPointF(30,30)
        # Scale and pivot remain screen-space affordances; all XYZ/rotation
        # handles are exact projections of the canonical local axes.
        return {"center":center,"x":x_axis,"y":y_axis,"z":z_handle,"projected_z":z_axis,"rotate_x":y_axis,"rotate_y":x_axis,"rotate_z":rotate_z,"scale":center+QPointF(38,38),"pivot":center+QPointF(-14,-14)}

    def _resource_rotation_ring(self,axis):
        if self.project is None or self.resource_transform is None:return QPolygonF()
        t=self.resource_transform.evaluated(self.frame_index);pivot=np.array((self.project.width/2+t.pivot_x,self.project.height/2+t.pivot_y,0.0));radius=38/max(.001,self.zoom);points=[]
        for index in range(49):
            angle=index*math.tau/48;c=math.cos(angle)*radius;s=math.sin(angle)*radius
            offset=(0,c,s) if axis=="x" else (c,0,s) if axis=="y" else (c,s,0)
            points.append(pivot+offset)
        projected,_,_,valid=project_local_points(np.asarray(points),self.resource_transform,self.project.width,self.project.height,self.frame_index)
        if not valid.all():return QPolygonF()
        return QPolygonF(tuple(self.canvas_to_widget(float(x),float(y)) for x,y in projected))

    def canvas_to_widget(self, x: float, y: float) -> QPointF:
        if self.project is None: return QPointF()
        origin = self._canvas_origin()
        return QPointF(origin.x() + x * self.zoom, origin.y() + y * self.zoom)

    def widget_to_canvas(self, point: QPointF) -> QPointF:
        origin = self._canvas_origin()
        return QPointF((point.x() - origin.x()) / self.zoom, (point.y() - origin.y()) / self.zoom)

    def _canvas_origin(self) -> QPoint:
        if self.project is None: return QPoint()
        return QPoint(round((self.width() - self.project.width * self.zoom) / 2 + self.pan_offset.x()),
                      round((self.height() - self.project.height * self.zoom) / 2 + self.pan_offset.y()))

    def set_frame(self, index: int) -> None:
        if not self.playback_mode and self.playback_pixmap_frame!=index:self.clear_playback_frame(update=False)
        if index!=self.frame_index:self.clear_interactive_transform_proxy(update=False)
        self.frame_index = index
        self.update()

    def begin_playback(self) -> None:self.playback_mode=True
    def end_playback(self,keep_current=True) -> None:
        self.playback_mode=False
        if not keep_current:self.clear_playback_frame(update=False)
    def set_playback_frame(self,pixmap,frame_index,key=None) -> None:
        self.playback_pixmap=pixmap;self.playback_pixmap_frame=int(frame_index);self.playback_pixmap_key=key;self.update()
    def clear_playback_frame(self,update=True) -> None:
        had=self.playback_pixmap is not None;self.playback_pixmap=None;self.playback_pixmap_frame=None;self.playback_pixmap_key=None
        if update and had:self.update()

    def set_layer(self, index: int) -> None:
        self.layer_index = index
        self.update()

    def _fit_initial_zoom(self) -> None:
        if self.project:
            self.zoom = max(1, min(16, 512 // max(self.project.width, self.project.height)))

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        self.clear_interactive_transform_proxy(update=False)
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.zoom = max(1, min(32, self.zoom + delta))
        self.update()
        event.accept()

    def _ordered_proxy_layers(self, selected, transform=None):
        resource_by_generated={item.generated_layer_id:item for item in self.project.effect_resource_layers}
        slots=[index for index,item in enumerate(self.project.layers) if item.id in resource_by_generated]
        ordered=list(self.project.layers)
        def depth(item):
            resource=resource_by_generated[item.id]
            value=transform if selected is resource and transform is not None else resource.layer_transform if resource.advanced_transform_enabled else EffectLayerTransform3D()
            return value.value("position_z",self.frame_index)
        resources=sorted((self.project.layers[index] for index in slots),key=depth)
        for slot,item in zip(slots,resources,strict=True):ordered[slot]=item
        return ordered

    def _proxy_depth_signature(self,layer,transform):
        generated=next((item for item in self.project.layers if item.id==layer.generated_layer_id),None)
        if generated is None:return (),[],[]
        ordered=self._ordered_proxy_layers(layer,transform);index=ordered.index(generated)
        before=[item for item in ordered[:index] if item.visible]
        after=[item for item in ordered[index+1:] if item.visible]
        return (tuple(item.id for item in before),tuple(item.id for item in after)),before,after

    def _proxy_layers_pixmap(self,layers):
        output=np.zeros((self.project.height,self.project.width,4),dtype=np.float32)
        frame=self.project.frames[self.frame_index]
        for layer in layers:
            source=frame.layer_pixels.get(layer.id)
            if source is not None:self._composite(output,source,layer.opacity,project_layer_blend_mode(self.project,layer.id))
        pixels=np.ascontiguousarray(np.clip(output*255.0,0,255).astype(np.uint8))
        image=QImage(pixels.data,self.project.width,self.project.height,pixels.strides[0],QImage.Format.Format_RGBA8888).copy()
        return QPixmap.fromImage(image)

    def _proxy_layer_revision(self,layer) -> tuple:
        frame=self.project.frames[self.frame_index];source=frame.layer_pixels.get(layer.id)
        return (layer.id,id(source),round(float(layer.opacity),6),project_layer_blend_mode(self.project,layer.id),None if source is None else source.shape)

    def proxy_prewarm_token(self,layer,base_key,request_revision=0) -> ProxyPrewarmToken:
        signature,before,after=self._proxy_depth_signature(layer,layer.layer_transform)
        visible=tuple((item.id,bool(item.visible)) for item in self.project.layers)
        revisions=(tuple(self._proxy_layer_revision(item) for item in before),tuple(self._proxy_layer_revision(item) for item in after))
        resources=tuple((item.id,int(item.revision)) for item in self.project.resource_compositions)
        return ProxyPrewarmToken(
            id(self.project),layer.id,self.frame_index,(self.project.width,self.project.height),
            layer.placement_mode,tuple(base_key),resources,int(layer.layer_transform.revision),
            revisions,visible,signature,int(request_revision),
        )

    def proxy_prewarm_payload(self,token,base_frame) -> ProxyPrewarmPayload | None:
        if self.project is None or self.preview_frames is not None:return None
        self.last_prewarm_payload_timings={};started=perf_counter()
        layer=next((item for item in self.project.effect_resource_layers if item.id==token.resource_layer_id),None)
        self.last_prewarm_payload_timings["selected_layer_lookup"]=(perf_counter()-started)*1000.0
        if layer is None:return None
        current=self.proxy_prewarm_token(layer,token.particle_base_revision,token.request_revision)
        if current!=token:return None
        started=perf_counter();layer_list=list(self.project.layers)
        self.last_prewarm_payload_timings["layer_list_collection"]=(perf_counter()-started)*1000.0
        started=perf_counter();visible_layers=tuple(item.id for item in layer_list if item.visible)
        self.last_prewarm_payload_timings["visibility_filter"]=(perf_counter()-started)*1000.0
        started=perf_counter();_,before,after=self._proxy_depth_signature(layer,layer.layer_transform)
        self.last_prewarm_payload_timings["z_evaluation_stable_sort"]=(perf_counter()-started)*1000.0
        started=perf_counter();selected_partition=(len(before),len(after),visible_layers)
        self.last_prewarm_payload_timings["selected_index_partition"]=(perf_counter()-started)*1000.0
        frame=self.project.frames[self.frame_index]
        def sources(items):
            return tuple((frame.layer_pixels[item.id],float(item.opacity),project_layer_blend_mode(self.project,item.id)) for item in items if item.id in frame.layer_pixels)
        started=perf_counter();before_sources=sources(before);after_sources=sources(after)
        self.last_prewarm_payload_timings["exact_rgba_cache_lookup"]=(perf_counter()-started)*1000.0
        started=perf_counter()
        cached=self.proxy_composite_cache.get(token.composite_key)
        cached_base=self.proxy_base_image_cache.peek(token.particle_base_revision)
        self.last_prewarm_payload_timings["composite_and_base_cache_lookup"]=(perf_counter()-started)*1000.0
        if cached is None:self.proxy_stats["prewarm_misses"]+=1
        else:self.proxy_stats["prewarm_hits"]+=1
        del selected_partition
        return ProxyPrewarmPayload(
            token,base_frame,before_sources,after_sources,
            None if cached is None else cached.underlay,
            None if cached is None else cached.overlay,
            None if cached_base is None else cached_base.rgba,
            None if cached_base is None else cached_base.alpha_bounds,
            self.project,deepcopy(layer),self.frame_index,
        )

    def _proxy_pixmap_from_rgba(self,pixels,prefix="proxy"):
        started=perf_counter()
        image=QImage(pixels.data,pixels.shape[1],pixels.shape[0],pixels.strides[0],QImage.Format.Format_RGBA8888).copy()
        self.last_prewarm_install_timings[f"{prefix}_numpy_to_qimage"]=(perf_counter()-started)*1000.0
        started=perf_counter();pixmap=QPixmap.fromImage(image)
        self.last_prewarm_install_timings[f"{prefix}_qimage_to_qpixmap"]=(perf_counter()-started)*1000.0
        return image,pixmap

    def install_proxy_prewarm(self,result: ProxyPrewarmComputed) -> bool:
        if self.project is None or self.preview_frames is not None:return False
        self.last_prewarm_install_timings={};install_started=perf_counter()
        token=result.token;layer=next((item for item in self.project.effect_resource_layers if item.id==token.resource_layer_id),None)
        if layer is None or self.proxy_prewarm_token(layer,token.particle_base_revision,token.request_revision)!=token:return False
        base=self.proxy_base_image_cache.peek(token.particle_base_revision)
        if base is None:
            image=pixmap=None
            if result.alpha_bounds is not None:image,pixmap=self._proxy_pixmap_from_rgba(result.cropped_rgba,"base")
            base=self.proxy_base_image_cache.put(ProxyBaseImage(token.particle_base_revision,result.cropped_rgba,result.alpha_bounds,image,pixmap))
            if image is not None:self.proxy_base_image_cache.qimage_creations+=1;self.proxy_base_image_cache.qpixmap_creations+=1
            self.proxy_base_image_cache.alpha_bounds_scans+=1
        entry=self.proxy_composite_cache.get(token.composite_key)
        if entry is None:
            if result.underlay_rgba is None or result.overlay_rgba is None:return False
            _,underlay=self._proxy_pixmap_from_rgba(result.underlay_rgba,"underlay");_,overlay=self._proxy_pixmap_from_rgba(result.overlay_rgba,"overlay")
            entry=self.proxy_composite_cache.put(token.composite_key,underlay,overlay,result.underlay_rgba.nbytes+result.overlay_rgba.nbytes)
        dragging=self._resource_transform_drag is not None and self.resource_transform_id==layer.id and layer.placement_mode!=PLACEMENT_PARTICLE
        transform=deepcopy(self.resource_transform if dragging and self.resource_transform is not None else layer.layer_transform);polygon,valid=self._proxy_widget_quad(base.alpha_bounds,transform.evaluated(self.frame_index))
        state=InteractiveTransformProxyState(layer.id,self.frame_index,token.particle_base_revision,base,active=dragging,applied_transform=transform)
        state.prewarm_token=token;state.depth_order_signature=token.depth_signature;state.underlay_pixmap=entry.underlay;state.overlay_pixmap=entry.overlay
        if valid:
            state.projected_quad=polygon;state.previous_projected_bounds=self._proxy_polygon_bounds(polygon);state.current_projected_bounds=state.previous_projected_bounds
        if dragging:state.queue(transform)
        self.interactive_transform_proxy=state;self.proxy_stats["prewarm_installs"]+=1
        self.last_prewarm_install_timings["proxy_state_install"]=(perf_counter()-install_started)*1000.0
        return True

    def activate_proxy_prewarm(self,layer,base_key) -> bool:
        state=self.interactive_transform_proxy
        if state is None or state.active or state.resource_layer_id!=layer.id or state.frame!=self.frame_index or state.base_key!=tuple(base_key):return False
        token=state.prewarm_token
        if token is None or self.proxy_prewarm_token(layer,base_key,token.request_revision)!=token:
            self.interactive_transform_proxy=None;return False
        state.active=True;state.applied_transform=deepcopy(layer.layer_transform);state.queue(layer.layer_transform)
        self.proxy_stats["prewarm_hits"]+=1
        return True

    def _rebuild_proxy_depth_buffers(self,state,layer,transform):
        signature,before,after=self._proxy_depth_signature(layer,transform)
        if signature==state.depth_order_signature and state.underlay_pixmap is not None:return False
        token=self.proxy_prewarm_token(layer,state.base_key)
        cached=self.proxy_composite_cache.get(token.composite_key)
        if cached is not None:
            state.depth_order_signature=signature;state.underlay_pixmap=cached.underlay;state.overlay_pixmap=cached.overlay
            return True
        state.depth_order_signature=signature
        state.underlay_pixmap=self._proxy_layers_pixmap(before)
        state.overlay_pixmap=self._proxy_layers_pixmap(after)
        self.proxy_composite_cache.put(token.composite_key,state.underlay_pixmap,state.overlay_pixmap,self.project.width*self.project.height*8)
        self.proxy_stats["depth_rebuilds"]+=1
        return True

    def _proxy_widget_quad(self,bounds,transform):
        destination,valid=proxy_projected_quad(bounds,transform,self.project.width,self.project.height)
        if not valid or destination is None:return QPolygonF(),False
        return QPolygonF(tuple(self.canvas_to_widget(float(x),float(y)) for x,y in destination)),True

    @staticmethod
    def _proxy_polygon_bounds(polygon):
        return polygon.boundingRect().toAlignedRect() if len(polygon)==4 else QRect()

    def queue_interactive_transform_proxy(self,layer,base_frame,base_key) -> bool:
        if self.project is None or self.preview_frames is not None or base_frame is None:return False
        cache_key=tuple(base_key);base=self.proxy_base_image_cache.get(cache_key,base_frame)
        state=self.interactive_transform_proxy
        if state is not None and not state.active and self.activate_proxy_prewarm(layer,cache_key):
            state=self.interactive_transform_proxy
        if state is None or state.resource_layer_id!=layer.id or state.frame!=self.frame_index or state.base_key!=cache_key:
            if self._resource_transform_drag and self._resource_transform_before is not None:
                previous=deepcopy(self._resource_transform_before)
            else:
                previous=deepcopy(self.resource_transform) if self.resource_transform_id==layer.id and self.resource_transform is not None else deepcopy(layer.layer_transform)
            state=InteractiveTransformProxyState(layer.id,self.frame_index,cache_key,base,applied_transform=previous)
            state.blend_mode=project_layer_blend_mode(self.project,layer.generated_layer_id)
            previous_quad,valid=self._proxy_widget_quad(base.alpha_bounds,previous.evaluated(self.frame_index))
            if valid:state.previous_projected_bounds=self._proxy_polygon_bounds(previous_quad)
            old_signature,_,_=self._proxy_depth_signature(layer,previous)
            self._rebuild_proxy_depth_buffers(state,layer,layer.layer_transform)
            if old_signature!=state.depth_order_signature:self.proxy_stats["full_updates"]+=1
            self.interactive_transform_proxy=state
        state.queue(layer.layer_transform)
        return True

    def _resource_transform_gizmo_bounds(self):
        points=self.resource_transform_handle_positions().values()
        if not points:return QRect()
        left=min(point.x() for point in points);right=max(point.x() for point in points)
        top=min(point.y() for point in points);bottom=max(point.y() for point in points)
        return QRectF(left,top,right-left,bottom-top).toAlignedRect().adjusted(-16,-16,16,16)

    def _motion_guide_bounds(self):
        if not isinstance(self.effect_guide_settings,ParticleEmitterSettings) or self.effect_guide_settings.motion.mode not in {"orbit","helix"}:return QRect()
        points=list(self._guide_points().values())+list(getattr(self,"_motion_guide_path",()))
        if not points:return QRect()
        left=min(point.x() for point in points);right=max(point.x() for point in points)
        top=min(point.y() for point in points);bottom=max(point.y() for point in points)
        return QRectF(left,top,right-left,bottom-top).toAlignedRect().adjusted(-16,-16,16,16)

    def _effect_guide_bounds(self):
        points=list(self._guide_points().values())
        if isinstance(self.effect_guide_settings,ParticleEmitterSettings) and self.effect_guide_settings.motion.mode in {"orbit","helix"}:points+=list(getattr(self,"_motion_guide_path",()))
        if not points:return QRect()
        left=min(point.x() for point in points);right=max(point.x() for point in points);top=min(point.y() for point in points);bottom=max(point.y() for point in points)
        return QRectF(left,top,right-left,bottom-top).toAlignedRect().adjusted(-16,-16,16,16)

    def apply_interactive_motion_proxy(self,layer,base_frame,base_key,motion_revision,*,already_transformed=False) -> bool:
        """Replace only the selected particle image and reuse cached composites."""
        interaction_started=perf_counter()
        if self.project is None or self.preview_frames is not None or base_frame is None:return False
        cache_key=tuple(base_key);token=self.proxy_prewarm_token(layer,cache_key)
        previous=self.interactive_transform_proxy
        old_bounds=QRect()
        reusable=False
        if previous is not None and previous.resource_layer_id==layer.id and previous.frame==self.frame_index:
            old_bounds=previous.current_projected_bounds if not previous.current_projected_bounds.isNull() else previous.previous_projected_bounds
            old_token=previous.prewarm_token
            reusable=old_token is not None and old_token.composite_key==token.composite_key and previous.underlay_pixmap is not None and previous.overlay_pixmap is not None
        if previous is not None and previous.render_in_progress:
            self.proxy_stats["overlap_rejections"]+=1;return False
        base=self.proxy_base_image_cache.get(cache_key,base_frame);transform=EffectLayerTransform3D() if already_transformed else deepcopy(layer.layer_transform)
        state=InteractiveTransformProxyState(layer.id,self.frame_index,cache_key,base,active=True,applied_transform=transform)
        state.blend_mode=project_layer_blend_mode(self.project,layer.generated_layer_id)
        state.render_in_progress=True
        try:
            state.prewarm_token=token;state.depth_order_signature=token.depth_signature
            if reusable:
                state.underlay_pixmap=previous.underlay_pixmap;state.overlay_pixmap=previous.overlay_pixmap
            else:
                entry=self.proxy_composite_cache.get(token.composite_key)
                if entry is not None:
                    state.underlay_pixmap=entry.underlay;state.overlay_pixmap=entry.overlay
                else:
                    # Cold guide drags prewarm these depth buffers on the worker
                    # pool.  Keep the handle responsive until that result lands;
                    # never rebuild every visible project layer on the GUI thread.
                    self.proxy_stats["motion_composite_waits"]+=1
                    return False
            evaluated=transform.evaluated(self.frame_index);polygon,valid=self._proxy_widget_quad(base.alpha_bounds,evaluated)
            current=self._proxy_polygon_bounds(polygon) if valid and evaluated.opacity>0 else QRect()
            state.projected_quad=polygon if valid else QPolygonF();state.previous_projected_bounds=old_bounds;state.current_projected_bounds=current
            state.paint_signature=(cache_key,int(motion_revision),token.depth_signature);state.last_applied_revision=int(motion_revision)
            self.interactive_transform_proxy=state;self.proxy_stats["motion_apply_calls"]+=1;self.proxy_stats["partial_updates"]+=1
            dirty=old_bounds.united(current).united(self._motion_guide_bounds()).united(self._resource_transform_gizmo_bounds()).adjusted(-12,-12,12,12).intersected(self.rect())
            self.last_proxy_dirty_rect=dirty;self.update(dirty if not dirty.isNull() else current)
            self._record_interaction("motion_proxy_apply",interaction_started);return True
        finally:
            state.render_in_progress=False

    def finish_interactive_motion_proxy(self,identifier) -> None:
        state=self.interactive_transform_proxy
        if state is not None and state.resource_layer_id==identifier:self.clear_interactive_transform_proxy(update=True)

    def apply_interactive_transform_proxy(self,layer) -> bool:
        interaction_started=perf_counter()
        state=self.interactive_transform_proxy
        if state is None or not state.active or state.resource_layer_id!=layer.id or state.frame!=self.frame_index:return False
        if state.render_in_progress:
            self.proxy_stats["overlap_rejections"]+=1;return False
        pending=state.pending_transform
        if pending is None:return False
        state.render_in_progress=True
        try:
            evaluated=pending.evaluated(self.frame_index)
            polygon,valid=self._proxy_widget_quad(state.base.alpha_bounds,evaluated)
            current=self._proxy_polygon_bounds(polygon) if valid and evaluated.opacity>0 else QRect()
            depth_changed=self._rebuild_proxy_depth_buffers(state,layer,pending)
            signature=(tuple(round(value*16) for point in polygon for value in (point.x(),point.y())),round(evaluated.opacity*255),state.depth_order_signature) if valid else ("invalid",state.depth_order_signature)
            state.pending_transform=None;state.render_scheduled=False
            if signature==state.paint_signature and not depth_changed:
                state.last_applied_revision=int(pending.revision);self.proxy_stats["paint_skips"]+=1;return False
            old=state.current_projected_bounds if not state.current_projected_bounds.isNull() else state.previous_projected_bounds
            state.previous_projected_bounds=old;state.current_projected_bounds=current;state.projected_quad=polygon if valid else QPolygonF();state.paint_signature=signature
            state.applied_transform=deepcopy(pending);state.last_applied_revision=int(pending.revision)
            self.resource_transform=deepcopy(pending);self.proxy_stats["apply_calls"]+=1
            canvas_rect=QRect(self._canvas_origin(),QSize(self.project.width*self.zoom,self.project.height*self.zoom))
            if depth_changed:
                dirty=canvas_rect;self.proxy_stats["full_updates"]+=1
            else:
                dirty=old.united(current).united(self._resource_transform_gizmo_bounds()).adjusted(-12,-12,12,12).intersected(self.rect())
                self.proxy_stats["partial_updates"]+=1
            self.last_proxy_dirty_rect=dirty
            self.update(dirty)
            self._record_interaction("proxy_geometry_update",interaction_started);return True
        finally:
            state.render_in_progress=False

    def clear_interactive_transform_proxy(self,update=True) -> None:
        state=self.interactive_transform_proxy
        if state is None:return
        dirty=state.previous_projected_bounds.united(state.current_projected_bounds).united(self._resource_transform_gizmo_bounds()).adjusted(-12,-12,12,12).intersected(self.rect())
        self.interactive_transform_proxy=None
        if update:
            self.last_proxy_dirty_rect=dirty;self.update(dirty if not dirty.isNull() else self.rect())

    def finish_interactive_transform_proxy(self,identifier,transform) -> None:
        if self.interactive_transform_proxy is not None and self.interactive_transform_proxy.resource_layer_id==identifier:
            self.clear_interactive_transform_proxy(update=True)
        self.resource_transform_id=identifier;self.resource_transform=deepcopy(transform)

    def paintEvent(self, event: object) -> None:  # noqa: N802
        paint_started=perf_counter()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#20242b"))
        if not self.project or not self.project.frames:
            painter.setPen(QColor("#adb5bd"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No project")
            return

        width = max(1,round(self.project.width * self.zoom))
        height = max(1,round(self.project.height * self.zoom))
        origin = self._canvas_origin()
        canvas_rect = QRect(origin.x(), origin.y(), width, height)
        painter.setClipRect(canvas_rect)

        checker = max(1,round(8 * self.zoom))
        colors = (QColor("#b8bdc4"), QColor("#e1e4e8"))
        for y in range(origin.y(), origin.y() + height, checker):
            for x in range(origin.x(), origin.x() + width, checker):
                color = colors[((x - origin.x()) // checker + (y - origin.y()) // checker) % 2]
                painter.fillRect(x, y, checker, checker, color)

        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        proxy=self.interactive_transform_proxy
        if proxy is not None and proxy.active and proxy.frame==self.frame_index:
            if proxy.underlay_pixmap is not None:painter.drawPixmap(canvas_rect,proxy.underlay_pixmap)
            self._paint_interactive_transform_proxy(painter,proxy)
            if proxy.overlay_pixmap is not None:painter.drawPixmap(canvas_rect,proxy.overlay_pixmap)
            self.proxy_stats["paint_calls"]+=1
        elif self.playback_pixmap is not None:
            playback_draw_started=perf_counter();painter.drawPixmap(canvas_rect,self.playback_pixmap)
            elapsed=(perf_counter()-playback_draw_started)*1000.0;self.playback_display_stats["cached_paints"]+=1;self.playback_display_stats["cached_draw_ms"]+=elapsed;self.playback_display_stats["cached_draw_max_ms"]=max(self.playback_display_stats["cached_draw_max_ms"],elapsed)
        else:
            self.playback_display_stats["fallback_paints"]+=1
            pixels: np.ndarray = np.ascontiguousarray(self._compose_display_frame())
            image = QImage(
                pixels.data,
                self.project.width,
                self.project.height,
                pixels.strides[0],
                QImage.Format.Format_RGBA8888,
            ).copy()
            pixmap = QPixmap.fromImage(image)
            painter.drawPixmap(canvas_rect, pixmap)
        painter.setClipping(False)
        painter.setPen(QColor("#77808c"))
        painter.drawRect(canvas_rect.adjusted(0, 0, -1, -1))
        if self.preview_frames is not None:
            badge = QRect(origin.x() + 6, origin.y() + 6, 74, 24)
            painter.fillRect(badge, QColor(30, 30, 30, 210))
            painter.setPen(QColor("#ffd166"))
            painter.drawText(
                badge, Qt.AlignmentFlag.AlignCenter, self.preview_badge_text
            )
        if not self.playback_mode and self.show_effect_guides and self.gizmo_generator_id and self.gizmo_settings is not None and not self.gizmo_locked:
            self._paint_gizmo(painter)
        if not self.playback_mode and self.show_effect_guides and proxy is not None and proxy.active and len(proxy.projected_quad)==4:
            painter.setPen(QPen(QColor("#74c0fc"),1,Qt.PenStyle.DashLine));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawPolygon(proxy.projected_quad)
        # Guides and gizmos are a lightweight GUI-thread overlay.  Exact/proxy
        # frame installation must never hide them during direct manipulation.
        if not self.playback_mode and self.show_effect_guides and self.effect_guide_id and self.effect_guide_settings is not None:
            self._paint_effect_guide(painter)
        if not self.playback_mode and self.show_effect_guides and self.multi_resource_transform_context is not None:
            painter.setPen(QPen(QColor("#74c0fc"),2));painter.setBrush(Qt.BrushStyle.NoBrush)
            for _identifier,origin_point in self.multi_resource_transform_context.origins:painter.drawEllipse(self.canvas_to_widget(*origin_point),6,6)
        if not self.playback_mode and self.show_effect_guides and self.resource_transform_id and self.resource_transform is not None:
            self._paint_resource_transform_gizmo(painter)
        if hasattr(event,"rect") and event.rect()!=self.rect():self.interaction_stats["partial_paints"]+=1
        else:self.interaction_stats["full_paints"]+=1
        self._record_interaction("paint_event",paint_started)

    def _paint_interactive_transform_proxy(self,painter,state):
        if state.base.pixmap is None or len(state.projected_quad)!=4 or state.applied_transform is None:return
        mapping=projective_pixmap_transform(state.base.pixmap,state.projected_quad)
        if mapping is None:return
        painter.save();painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus if state.blend_mode=="additive" else QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setOpacity(max(0.0,min(1.0,state.applied_transform.evaluated(self.frame_index).opacity)))
        painter.setTransform(mapping);painter.drawPixmap(0,0,state.base.pixmap);painter.restore()

    def _gizmo_center(self) -> tuple[float, float]:
        s = self.gizmo_settings
        x, y = float(s.origin_x), float(s.origin_y)
        if self.gizmo_mode != "distribution" and hasattr(s, "offset_x_start"):
            x += float(s.offset_x_end if self.gizmo_edit_end else s.offset_x_start)
            y += float(s.offset_y_end if self.gizmo_edit_end else s.offset_y_start)
        return x, y

    def _paint_gizmo(self, painter: QPainter) -> None:
        painter.save()
        x, y = self._gizmo_center(); center = self.canvas_to_widget(x, y)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#51cf66"), GIZMO_OUTLINE_WIDTH)); painter.setBrush(Qt.BrushStyle.NoBrush)
        radius=GIZMO_ACTIVE_HANDLE_RADIUS if self._gizmo_drag else GIZMO_HANDLE_RADIUS
        painter.drawEllipse(center, radius, radius)
        s = self.gizmo_settings
        if self.gizmo_mode == "rotate":
            angle = float(s.rotation_end if self.gizmo_edit_end else s.rotation_start)
            end = center + QPointF(math.cos(math.radians(angle)) * 48, math.sin(math.radians(angle)) * 48)
            painter.drawLine(center, end); painter.drawEllipse(end, radius, radius)
        elif self.gizmo_mode == "scale":
            sx = abs(float(s.scale_x_end if self.gizmo_edit_end else s.scale_x_start)); sy = abs(float(s.scale_y_end if self.gizmo_edit_end else s.scale_y_start))
            rect = QRect(round(center.x() - 24*sx), round(center.y() - 24*sy), round(48*sx), round(48*sy))
            painter.drawRect(rect); painter.drawRect(rect.right()-radius, rect.bottom()-radius, radius*2, radius*2)
        elif self.gizmo_mode == "distribution":
            if getattr(s, "distribution", "Point") == "Line":
                end = self.canvas_to_widget(s.line_end_x, s.line_end_y); painter.drawLine(center, end); painter.drawEllipse(end, 5, 5)
            elif getattr(s, "distribution", "Point") == "Circle":
                radius = max(0.0, float(s.radius)) * self.zoom; painter.drawEllipse(center, radius, radius)
        painter.restore()

    def _paint_resource_transform_gizmo(self,painter):
        p=self.resource_transform_handle_positions();center=p.get("center")
        if center is None:return
        painter.save();painter.setBrush(Qt.BrushStyle.NoBrush)
        active=self._resource_transform_drag or self._resource_transform_hover
        radius=GIZMO_ACTIVE_HANDLE_RADIUS if active else GIZMO_HANDLE_RADIUS
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True);mode=self.resource_transform_mode
        if mode=="move":
            for name,color in (("x","#ff6b6b"),("y","#51cf66"),("z","#4dabf7")):
                if self.multi_resource_transform_context is not None and name=="z":continue
                axis_point=p.get("projected_z") if name=="z" else p[name];painter.setPen(QPen(QColor(color),2 if active==name else GIZMO_OUTLINE_WIDTH));painter.drawLine(center,axis_point)
                if name=="z" and p[name]!=axis_point:painter.setPen(QPen(QColor(color),2,Qt.PenStyle.DashLine));painter.drawLine(axis_point,p[name])
                painter.drawEllipse(p[name],radius,radius);painter.drawText(p[name]+QPointF(7,-5),name.upper())
            painter.setPen(QPen(QColor("#ffffff"),GIZMO_OUTLINE_WIDTH));painter.drawEllipse(center,radius,radius)
        elif mode.startswith("rotate_"):
            axis=mode[-1];color={"rotate_x":"#ff6b6b","rotate_y":"#51cf66","rotate_z":"#4dabf7"}[mode];painter.setPen(QPen(QColor(color),2 if active else GIZMO_OUTLINE_WIDTH));ring=self._resource_rotation_ring(axis)
            if len(ring)>1:painter.drawPolyline(ring)
            painter.drawLine(center,p[mode]);painter.drawEllipse(p[mode],radius,radius);painter.drawText(p[mode]+QPointF(7,-5),axis.upper())
        elif mode=="scale":
            painter.setPen(QPen(QColor("#ffd43b"),2 if active else GIZMO_OUTLINE_WIDTH));painter.drawRect(QRectF(center-QPointF(38,38),center+QPointF(38,38)));painter.drawRect(QRectF(p["scale"]-QPointF(radius,radius),p["scale"]+QPointF(radius,radius)))
        elif mode=="pivot":
            painter.setPen(QPen(QColor("#e599f7"),2));q=p["pivot"];painter.drawLine(q-QPointF(8,0),q+QPointF(8,0));painter.drawLine(q-QPointF(0,8),q+QPointF(0,8))
        painter.restore()

    def _hit_resource_transform(self,position):
        if not self.show_effect_guides:return None
        points=self.resource_transform_handle_positions();mode=self.resource_transform_mode
        names=(("x","y","center") if self.multi_resource_transform_context is not None else ("x","y","z","center")) if mode=="move" else (("rotate_z",) if self.multi_resource_transform_context is not None and mode.startswith("rotate_") else (mode,)) if mode.startswith("rotate_") else (mode,)
        return next((name for name in names if name in points and math.hypot(points[name].x()-position.x(),points[name].y()-position.y())<=GIZMO_HIT_RADIUS),None)

    def _start_resource_transform_drag(self,handle,event,event_started):
        self._resource_transform_drag=handle;self._resource_transform_before=deepcopy(self.resource_transform);self._resource_transform_start=event.position();self._resource_transform_changed=False;self.resource_transform_changed_fields=();self.resource_transform_started.emit(self.resource_transform_id);self.setFocus();event.accept();self._record_interaction("mouse_press_total",event_started)
        if handle.startswith("rotate_"):
            property_name=RESOURCE_TRANSFORM_HANDLE_PROPERTIES[handle][0];self._resource_rotation_last_angle=None;self._resource_rotation_accumulated=self._resource_transform_before.value(property_name,self.frame_index)
            center=self.resource_transform_handle_positions().get("center",event.position());self._resource_multi_start_angle=math.atan2(event.position().y()-center.y(),event.position().x()-center.x())

    def _set_resource_transform_interactive_value(self,transform,property_id,value):
        numeric=float(value);track=transform.tracks.get(property_id);current=transform.value(property_id,self.frame_index)
        if current==numeric:return False
        key=track.keyframe_at(self.frame_index) if track else None
        if key is not None:key.value=float(value)
        elif track and track.keyframes:transform.set_keyframe(property_id,self.frame_index,numeric,"Linear")
        else:setattr(transform,property_id,numeric)
        return True

    def _guide_points(self) -> dict[str, QPointF]:
        settings = self.effect_guide_settings
        if isinstance(settings, EffectCompositionLayer):
            return {
                "start": self.canvas_to_widget(*self._project_effect_point(settings.start_x, settings.start_y)),
                "end": self.canvas_to_widget(*self._project_effect_point(settings.end_x, settings.end_y)),
            }
        if isinstance(settings, ParticleEmitterSettings):
            if settings.motion.mode in {"orbit","helix"}:
                path=particle_motion_guide(settings,self.project.width if self.project else 64,self.project.height if self.project else 64,effect_frame=self.frame_index)
                evaluated_motion=settings.motion.evaluated(self.frame_index)
                projected=[]
                for item in path:
                    x,y,_,valid=project_particle_billboard(item,evaluated_motion.perspective_strength,self.project.width if self.project else 64,self.project.height if self.project else 64)
                    if valid:projected.append(self.canvas_to_widget(*self._project_effect_point(x,y,item.z)))
                if not projected:return {}
                center_raw=(settings.origin_x+evaluated_motion.center_x,settings.origin_y+evaluated_motion.center_y)
                center=self.canvas_to_widget(*self._project_effect_point(*center_raw))
                points={"motion_center":center,"radius_start":projected[0],"radius_end":projected[-1]}
                vector=projected[0]-center;length=max(1.0,math.hypot(vector.x(),vector.y()));points["start_angle"]=projected[0]+QPointF(-vector.y()/length*14,vector.x()/length*14)
                if settings.motion.mode=="helix":points["axis_end"]=projected[-1]
                self._motion_guide_path=projected
                return points
            guide = representative_particle_guide(settings)
            origin = self.canvas_to_widget(*self._project_effect_point(guide["origin_x"], guide["origin_y"]))
            endpoint = self.canvas_to_widget(*self._project_effect_point(guide["endpoint_x"], guide["endpoint_y"]))
            angle = math.radians(settings.direction_degrees)
            direction = origin + QPointF(math.cos(angle) * 48, math.sin(angle) * 48)
            points = {"origin": origin, "direction": direction, "endpoint": endpoint}
            if settings.spawn_shape == "line":
                points["shape"] = self.canvas_to_widget(*self._project_effect_point(settings.line_end_x, settings.line_end_y))
            elif settings.spawn_shape == "circle":
                points["shape"] = self.canvas_to_widget(*self._project_effect_point(settings.origin_x + settings.radius, settings.origin_y))
            elif settings.spawn_shape == "box":
                points["shape"] = self.canvas_to_widget(*self._project_effect_point(settings.origin_x + settings.box_width / 2,settings.origin_y + settings.box_height / 2))
            return points
        return {}

    def _project_effect_point(self,x,y,z=0.0):
        if self.project is None or self.resource_transform is None:return float(x),float(y)
        point=project_local_point(x,y,z,self.resource_transform,self.project.width,self.project.height,self.frame_index)
        return (point.x,point.y) if point.valid else (float(x),float(y))

    def _paint_effect_guide(self, painter: QPainter) -> None:
        points = self._guide_points()
        if not points:
            return
        painter.save();painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        guide_pen = QPen(QColor("#4dabf7"), 2, Qt.PenStyle.DashLine)
        painter.setPen(guide_pen)
        settings = self.effect_guide_settings
        if isinstance(settings, EffectCompositionLayer):
            painter.drawLine(points["start"], points["end"])
            self._paint_ghosts(painter, settings.resource_composition_id, points["start"], points["end"])
        else:
            if isinstance(settings,ParticleEmitterSettings) and settings.motion.mode in {"orbit","helix"}:
                path=getattr(self,"_motion_guide_path",[])
                if len(path)>1:painter.drawPolyline(QPolygonF(path))
                painter.drawLine(points["motion_center"],points["radius_start"]);painter.drawLine(points["motion_center"],points["radius_end"])
                if "axis_end" in points:painter.drawLine(points["motion_center"],points["axis_end"])
                for name,point in points.items():
                    active=name in {self._guide_hover,self._guide_handle};radius=GIZMO_ACTIVE_HANDLE_RADIUS if active else GIZMO_HANDLE_RADIUS
                    painter.setPen(QPen(QColor("#ffd43b") if active else QColor("#51cf66"),2 if active else GIZMO_OUTLINE_WIDTH));painter.drawEllipse(point,radius,radius)
                painter.restore()
                return
            origin, endpoint = points["origin"], points["endpoint"]
            painter.drawLine(origin, endpoint)
            painter.drawLine(origin, points["direction"])
            spread = math.radians(settings.direction_spread_degrees)
            direction = math.radians(settings.direction_degrees)
            length = min(80.0, max(36.0, math.hypot(endpoint.x()-origin.x(), endpoint.y()-origin.y())))
            for angle in (direction - spread, direction + spread):
                painter.drawLine(origin, origin + QPointF(math.cos(angle)*length, math.sin(angle)*length))
            if settings.spawn_shape == "line":
                painter.drawLine(origin, points["shape"])
            elif settings.spawn_shape == "circle":
                radius = max(0.0, settings.radius * self.zoom)
                painter.drawEllipse(origin, radius, radius)
            elif settings.spawn_shape == "box":
                painter.drawRect(QRectF(
                    origin.x()-settings.box_width*self.zoom/2,
                    origin.y()-settings.box_height*self.zoom/2,
                    settings.box_width*self.zoom, settings.box_height*self.zoom,
                ))
            if settings.resource_type == "resource_composition":
                self._paint_ghosts(painter, settings.resource_id, origin, endpoint)
        for name, point in points.items():
            active=name in {self._guide_hover,self._guide_handle};radius=GIZMO_ACTIVE_HANDLE_RADIUS if active else GIZMO_HANDLE_RADIUS
            painter.setPen(QPen(QColor("#ffd43b") if active else QColor("#51cf66"), 2 if active else GIZMO_OUTLINE_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(point, radius, radius)
        painter.restore()

    def _paint_ghosts(self, painter: QPainter, composition_id: str, start: QPointF, end: QPointF) -> None:
        if self.project is None:
            return
        composition = next((item for item in self.project.resource_compositions if item.id == composition_id), None)
        if composition is None:
            return
        # During a high-frequency 2.5D drag, keep projected guide geometry live
        # and reuse the last output frame instead of rebuilding three Ghost planes.
        if self._resource_transform_drag:
            return
        if self.resource_transform is not None:
            t=self.resource_transform.evaluated(self.frame_index);a=self.widget_to_canvas(start);b=self.widget_to_canvas(end)
            raw_a=unproject_layer_space_point(a.x(),a.y(),self.resource_transform,self.project.width,self.project.height,self.frame_index);raw_b=unproject_layer_space_point(b.x(),b.y(),self.resource_transform,self.project.width,self.project.height,self.frame_index)
            if raw_a is None or raw_b is None:return
            values=tuple(getattr(t,name) for name in ("position_x","position_y","position_z","rotation_x","rotation_y","rotation_z","scale_x","scale_y","opacity","pivot_x","pivot_y","perspective_strength"))
            key=("2.5d",composition.id,composition.revision,self.frame_index,values,tuple(round(v,3) for v in (*raw_a,*raw_b)))
            pixmaps=self._ghost_cache.get(key)
            if pixmaps is None:
                frames=render_composition_frames(self.project,composition);indexes=sorted({0,len(frames)//2,len(frames)-1});pixmaps=[]
                for order,index in enumerate(indexes):
                    amount=order/max(1,len(indexes)-1);x=raw_a[0]+(raw_b[0]-raw_a[0])*amount;y=raw_a[1]+(raw_b[1]-raw_a[1])*amount
                    raw=empty_pixels(self.project.width,self.project.height);asset=SourceAsset(composition.name,frames[index],pivot_x=composition.pivot_x,pivot_y=composition.pivot_y)
                    render_transformed_source(raw,asset,position_x=x,position_y=y,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=1)
                    pixels=np.ascontiguousarray(transform_layer_space_rgba_frame(raw,self.resource_transform,self.frame_index));image=QImage(pixels.data,self.project.width,self.project.height,pixels.strides[0],QImage.Format.Format_RGBA8888).copy();pixmaps.append(QPixmap.fromImage(image))
                self._ghost_cache[key]=pixmaps
            origin=self._canvas_origin();target=QRectF(origin.x(),origin.y(),self.project.width*self.zoom,self.project.height*self.zoom);painter.save();painter.setOpacity(.28)
            for pixmap in pixmaps:painter.drawPixmap(target,pixmap,QRectF(pixmap.rect()))
            painter.restore();return
        key = (composition.id, composition.revision)
        pixmaps = self._ghost_cache.get(key)
        if pixmaps is None:
            frames = render_composition_frames(self.project, composition)
            indexes = sorted({0, len(frames)//2, len(frames)-1})
            pixmaps = []
            for index in indexes:
                pixels = np.ascontiguousarray(frames[index])
                image = QImage(pixels.data, composition.width, composition.height, pixels.strides[0], QImage.Format.Format_RGBA8888).copy()
                pixmaps.append(QPixmap.fromImage(image))
            self._ghost_cache[key] = pixmaps
        painter.save(); painter.setOpacity(0.28)
        for index, pixmap in enumerate(pixmaps):
            amount = index / max(1, len(pixmaps)-1)
            point = start + (end-start)*amount
            target = QRectF(
                point.x()-composition.pivot_x*self.zoom,
                point.y()-composition.pivot_y*self.zoom,
                composition.width*self.zoom,
                composition.height*self.zoom,
            )
            painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        painter.restore()

    def _hit_guide_handle(self, position: QPointF) -> str | None:
        if self.effect_guide_locked or not self.show_effect_guides:return None
        candidates = self._guide_points()
        if not candidates:
            return None
        return next((name for name, point in candidates.items() if math.hypot(point.x()-position.x(), point.y()-position.y()) <= 10), None)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        event_started=perf_counter()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True; self._pan_last = event.position(); self.setCursor(Qt.CursorShape.ClosedHandCursor); event.accept(); return
        active_transform_layer = next((item for item in self.project.effect_resource_layers if item.id==self.resource_transform_id),None) if self.project is not None else None
        transform_is_selected = self.multi_resource_transform_context is not None or (active_transform_layer is not None and 0<=self.layer_index<len(self.project.layers) and active_transform_layer.generated_layer_id==self.project.layers[self.layer_index].id)
        transform_handle=None
        if event.button()==Qt.MouseButton.LeftButton and transform_is_selected and self.resource_transform is not None:
            hit_started=perf_counter();handle=self._hit_resource_transform(event.position());self._record_interaction("transform_hit_test",hit_started)
            transform_handle=handle
            # Explicit axis handles must win over an overlapping Motion Guide;
            # the central free-move affordance yields to semantic Guide points.
            if handle and (handle!="center" or self.multi_resource_transform_context is not None):self._start_resource_transform_drag(handle,event,event_started);return
        if event.button() == Qt.MouseButton.LeftButton and self.show_effect_guides and self.effect_guide_id:
            hit_started=perf_counter();handle = self._hit_guide_handle(event.position());self._record_interaction("guide_hit_test",hit_started)
            if handle:
                self._guide_handle = handle
                self._guide_identifier = self.effect_guide_id
                self._guide_before = deepcopy(self.effect_guide_settings)
                self._guide_last_canvas_point = None
                self._guide_changed = False
                self.effect_guide_started.emit(self._guide_identifier);self.setFocus()
                event.accept()
                self._record_interaction("mouse_press_total",event_started)
                return
        if transform_handle:self._start_resource_transform_drag(transform_handle,event,event_started);return
        if event.button() == Qt.MouseButton.LeftButton and self.show_effect_guides and self.gizmo_generator_id and self.gizmo_settings is not None and not self.gizmo_locked:
            self._gizmo_drag = True; self._gizmo_before = deepcopy(self.gizmo_settings); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton:
            layer_index = self._layer_at(event.position())
            if layer_index is not None:
                self.layer_selected.emit(layer_index); event.accept(); return
        super().mousePressEvent(event)

    def _layer_at(self, widget_point: QPointF) -> int | None:
        if self.project is None or not (0 <= self.frame_index < len(self.project.frames)):
            return None
        point = self.widget_to_canvas(widget_point); x, y = int(math.floor(point.x())), int(math.floor(point.y()))
        if not (0 <= x < self.project.width and 0 <= y < self.project.height):
            return None
        frame = self.project.frames[self.frame_index]
        for index in range(len(self.project.layers)-1, -1, -1):
            layer = self.project.layers[index]
            pixels = frame.layer_pixels.get(layer.id)
            if layer.visible and pixels is not None and pixels[y, x, 3] > 0:
                return index
        return None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            delta=event.position()-self._pan_last;self._pan_last=event.position();self.pan_offset+=delta;self.update();event.accept();return
        if self._resource_transform_drag:
            event_started=perf_counter();old_gizmo=self._resource_transform_gizmo_bounds();value_started=perf_counter();t=self.resource_transform;delta=(event.position()-self._resource_transform_start)/max(.001,self.zoom);before=self._resource_transform_before;handle=self._resource_transform_drag;changed=False
            if self.multi_resource_transform_context is not None:
                if handle in {"x","center"} or handle=="y":
                    value=(delta.x() if handle in {"x","center"} else 0.0,delta.y() if handle in {"y","center"} else 0.0);operation="move"
                elif handle=="rotate_z":
                    center=self.resource_transform_handle_positions()["center"];angle=math.atan2(event.position().y()-center.y(),event.position().x()-center.x());value=math.degrees(angle-self._resource_multi_start_angle);value=round(value/15)*15 if event.modifiers()&Qt.KeyboardModifier.ShiftModifier else value;operation="rotate"
                elif handle=="scale":
                    value=(max(.01,1+delta.x()/32),max(.01,1+delta.y()/32));operation="scale"
                else:event.accept();return
                payload={"operation":operation,"value":value};self.resource_transform_changed.emit("__multi__",payload,False);event.accept();self._record_interaction("mouse_move_total",event_started);return
            local_delta=np.array((delta.x(),delta.y()),dtype=np.float64)
            if self._resource_parent_prefix is not None:
                try:local_delta=np.linalg.inv(self._resource_parent_prefix[:2,:2])@local_delta
                except np.linalg.LinAlgError:pass
            if handle in {"x","center"}:changed=self._set_resource_transform_interactive_value(t,"position_x",before.value("position_x",self.frame_index)+local_delta[0]) or changed
            if handle in {"y","center"}:changed=self._set_resource_transform_interactive_value(t,"position_y",before.value("position_y",self.frame_index)+local_delta[1]) or changed
            if handle=="z":changed=self._set_resource_transform_interactive_value(t,"position_z",before.value("position_z",self.frame_index)-delta.y()+delta.x()) or changed
            if handle.startswith("rotate_"):
                center=self.resource_transform_handle_positions()["center"];pointer_angle=math.degrees(math.atan2(event.position().y()-center.y(),event.position().x()-center.x()));angle=pointer_angle+round((self._resource_rotation_accumulated-pointer_angle)/360.0)*360.0;self._resource_rotation_last_angle=pointer_angle;self._resource_rotation_accumulated=angle
                if event.modifiers()&Qt.KeyboardModifier.ShiftModifier:angle=round(angle/15)*15
                property_name=RESOURCE_TRANSFORM_HANDLE_PROPERTIES[handle][0];changed=self._set_resource_transform_interactive_value(t,property_name,angle) or changed
                counter=f"{property_name}_updates";calls=self.interaction_stats["calls"];calls[counter]=calls.get(counter,0)+1
            if handle=="scale":changed=self._set_resource_transform_interactive_value(t,"scale_x",max(.01,before.value("scale_x",self.frame_index)+delta.x()/32)) or changed;changed=self._set_resource_transform_interactive_value(t,"scale_y",max(.01,before.value("scale_y",self.frame_index)+delta.y()/32)) or changed
            if handle=="pivot":
                pivot_x,pivot_y=before.pivot_x+delta.x(),before.pivot_y+delta.y();changed=(t.pivot_x,t.pivot_y)!=(pivot_x,pivot_y);t.pivot_x,t.pivot_y=pivot_x,pivot_y
            if not changed:event.accept();self._record_interaction("mouse_move_total",event_started);return
            self._resource_transform_changed=True
            self.resource_transform_changed_fields=RESOURCE_TRANSFORM_HANDLE_PROPERTIES.get(handle,())
            self._record_interaction("transform_value_calculation",value_started);signal_started=perf_counter();self.resource_transform_changed.emit(self.resource_transform_id,deepcopy(t),False);self._record_interaction("transform_signal",signal_started)
            if self.interactive_transform_proxy is None:
                dirty=old_gizmo.united(self._resource_transform_gizmo_bounds()).adjusted(-12,-12,12,12).intersected(self.rect());self.last_proxy_dirty_rect=dirty;self.update(dirty)
            event.accept();self._record_interaction("mouse_move_total",event_started);return
        if self._guide_handle:
            event_started=perf_counter();old_guide=self._effect_guide_bounds();coordinate_started=perf_counter()
            point = self.widget_to_canvas(event.position())
            self._record_interaction("screen_to_canvas",coordinate_started)
            integer_point = (round(point.x()), round(point.y()))
            if integer_point == self._guide_last_canvas_point:
                event.accept(); return
            self._guide_last_canvas_point = integer_point
            guide_started=perf_counter();changed=self._move_effect_guide(point, event.modifiers());self._record_interaction("guide_value_calculation",guide_started)
            if not changed:event.accept();self._record_interaction("mouse_move_total",event_started);return
            self._guide_changed=True
            signal_started=perf_counter();self.effect_guide_changed.emit(self._guide_identifier, deepcopy(self.effect_guide_settings), False);self._record_interaction("guide_signal",signal_started)
            dirty=old_guide.united(self._effect_guide_bounds()).united(self._resource_transform_gizmo_bounds()).adjusted(-12,-12,12,12).intersected(self.rect())
            if dirty.isNull():self.interaction_stats["full_updates_without_rect"]+=1
            else:self.update(dirty)
            event.accept();self._record_interaction("mouse_move_total",event_started);return
        transform_hover=self._hit_resource_transform(event.position()) if self.resource_transform_id and self.resource_transform is not None else None
        if transform_hover:
            changed=transform_hover!=self._resource_transform_hover;self._resource_transform_hover=transform_hover;self._guide_hover=None;self.setCursor(Qt.CursorShape.PointingHandCursor);self.setToolTip(self.resource_transform_tooltips.get(transform_hover,""))
            if changed:self.update()
            return super().mouseMoveEvent(event)
        if self._resource_transform_hover is not None:self._resource_transform_hover=None;self.setToolTip("")
        if self.effect_guide_id:
            hover = self._hit_guide_handle(event.position())
            if hover != self._guide_hover:
                self._guide_hover = hover
                self.setCursor(Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor)
                self.update()
        if not self._gizmo_drag: super().mouseMoveEvent(event); return
        point = self.widget_to_canvas(event.position()); s = self.gizmo_settings
        if self.gizmo_mode == "move":
            name_x = "offset_x_end" if self.gizmo_edit_end else "offset_x_start"; name_y = "offset_y_end" if self.gizmo_edit_end else "offset_y_start"
            setattr(s, name_x, round(point.x() - s.origin_x)); setattr(s, name_y, round(point.y() - s.origin_y))
        elif self.gizmo_mode == "distribution":
            if getattr(s, "distribution", "Point") == "Line": s.line_end_x, s.line_end_y = round(point.x()), round(point.y())
            elif getattr(s, "distribution", "Point") == "Circle": s.radius = max(0, round(math.hypot(point.x()-s.origin_x, point.y()-s.origin_y)))
            else: s.origin_x, s.origin_y = round(point.x()), round(point.y())
        elif self.gizmo_mode == "rotate":
            x, y = self._gizmo_center(); angle = math.degrees(math.atan2(point.y()-y, point.x()-x))
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: angle = round(angle / 15) * 15
            setattr(s, "rotation_end" if self.gizmo_edit_end else "rotation_start", angle)
        elif self.gizmo_mode == "scale":
            x, y = self._gizmo_center(); value = max(0.01, math.hypot(point.x()-x, point.y()-y) / 34.0)
            setattr(s, "scale_x_end" if self.gizmo_edit_end else "scale_x_start", value); setattr(s, "scale_y_end" if self.gizmo_edit_end else "scale_y_start", value)
        self.gizmo_changed.emit(self.gizmo_generator_id, deepcopy(s)); self.update(); event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._panning and event.button()==Qt.MouseButton.MiddleButton:
            self._panning=False;self.setCursor(Qt.CursorShape.ArrowCursor);event.accept();return
        if self._resource_transform_drag:
            started=perf_counter();self._resource_transform_drag=None;self._resource_rotation_last_angle=None;self._resource_rotation_accumulated=None
            if self.multi_resource_transform_context is not None:self.resource_transform_changed.emit("__multi__",{"operation":"final","value":None},True)
            elif self._resource_transform_changed:self.resource_transform_changed.emit(self.resource_transform_id,deepcopy(self.resource_transform),True)
            event.accept();self._record_interaction("mouse_release_total",started);return
        if self._guide_handle:
            started=perf_counter()
            self._guide_handle = None
            self._guide_last_canvas_point = None
            identifier=self._guide_identifier;self._guide_identifier=None
            if self._guide_changed and identifier:self.effect_guide_changed.emit(identifier, deepcopy(self.effect_guide_settings), True)
            event.accept();self._record_interaction("mouse_release_total",started); return
        if self._gizmo_drag: self._gizmo_drag = False; event.accept(); return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self._guide_handle and self._guide_before is not None:
            before = deepcopy(self._guide_before)
            self.effect_guide_settings = before
            self._guide_handle = None
            self._guide_last_canvas_point = None
            identifier=self._guide_identifier;self._guide_identifier=None
            if identifier:self.effect_guide_cancelled.emit(identifier, before)
            self.update(); event.accept(); return
        if event.key()==Qt.Key.Key_Escape and self._resource_transform_drag and self._resource_transform_before is not None:
            self.resource_transform=deepcopy(self._resource_transform_before);self._resource_transform_drag=None;self._resource_rotation_last_angle=None;self._resource_rotation_accumulated=None;self.resource_transform_cancelled.emit(self.resource_transform_id,deepcopy(self.resource_transform));event.accept();return
        if event.key() == Qt.Key.Key_Escape and self._gizmo_drag and self._gizmo_before is not None:
            self.gizmo_settings = self._gizmo_before; self._gizmo_drag = False
            self.gizmo_changed.emit(self.gizmo_generator_id, deepcopy(self.gizmo_settings)); self.update(); event.accept(); return
        super().keyPressEvent(event)

    def _set_motion_interactive_value(self,motion,property_id,value):
        numeric=float(value);track=motion.tracks.get(property_id);current=motion.value(property_id,self.frame_index)
        if current==numeric:return False
        key=track.keyframe_at(self.frame_index) if track else None
        if key is not None:key.value=numeric
        elif track and track.keyframes:motion.set_keyframe(property_id,self.frame_index,numeric,"Linear")
        else:setattr(motion,property_id,numeric)
        return True

    def _move_effect_guide(self, point: QPointF, modifiers) -> bool:
        settings = self.effect_guide_settings
        if self.project is not None and self.resource_transform is not None:
            local=unproject_layer_space_point(point.x(),point.y(),self.resource_transform,self.project.width,self.project.height,self.frame_index)
            if local is None:return False
            point=QPointF(*local)
        x, y = round(point.x()), round(point.y())
        if isinstance(settings, EffectCompositionLayer):
            before=(settings.start_x,settings.start_y,settings.end_x,settings.end_y)
            if self._guide_handle == "start": settings.start_x, settings.start_y = x, y
            elif self._guide_handle == "end": settings.end_x, settings.end_y = x, y
            return before!=(settings.start_x,settings.start_y,settings.end_x,settings.end_y)
        if not isinstance(settings, ParticleEmitterSettings):
            return False
        if settings.motion.mode in {"orbit","helix"}:
            motion=settings.motion;evaluated=motion.evaluated(self.frame_index);center_x=settings.origin_x+evaluated.center_x;center_y=settings.origin_y+evaluated.center_y;changed=False
            if self._guide_handle=="motion_center":changed=self._set_motion_interactive_value(motion,"center_x",x-settings.origin_x) or changed;changed=self._set_motion_interactive_value(motion,"center_y",y-settings.origin_y) or changed
            elif self._guide_handle=="radius_start":changed=self._set_motion_interactive_value(motion,"radius_start",max(0.0,math.hypot(x-center_x,y-center_y)))
            elif self._guide_handle=="radius_end":changed=self._set_motion_interactive_value(motion,"radius_end",max(0.0,math.hypot(x-center_x,y-center_y)))
            elif self._guide_handle=="start_angle":
                angle=math.degrees(math.atan2(y-center_y,x-center_x));previous=float(evaluated.start_angle_degrees)
                angle+=round((previous-angle)/360.0)*360.0
                changed=self._set_motion_interactive_value(motion,"start_angle_degrees",round(angle/15)*15 if modifiers&Qt.KeyboardModifier.ShiftModifier else angle)
            elif self._guide_handle=="axis_end":
                value=x-center_x if motion.helix_axis=="x" else y-center_y if motion.helix_axis=="y" else (x-center_x)-(y-center_y);changed=self._set_motion_interactive_value(motion,"axis_end",value)
            if changed:motion.revision+=1
            return changed
        before=deepcopy(settings)
        if self._guide_handle == "origin":
            dx, dy = x-settings.origin_x, y-settings.origin_y
            settings.origin_x, settings.origin_y = x, y
            if settings.spawn_shape == "line": settings.line_end_x += dx; settings.line_end_y += dy
        elif self._guide_handle == "direction":
            angle = math.degrees(math.atan2(y-settings.origin_y, x-settings.origin_x))
            if modifiers & Qt.KeyboardModifier.ShiftModifier: angle = round(angle/15)*15
            settings.direction_degrees = angle
        elif self._guide_handle == "endpoint":
            dx, dy = x-settings.origin_x, y-settings.origin_y
            angle = math.degrees(math.atan2(dy, dx))
            if modifiers & Qt.KeyboardModifier.ShiftModifier: angle = round(angle/15)*15
            settings.direction_degrees = angle
            lifetime = max(1.0, (settings.lifetime_min+settings.lifetime_max)/2.0-1.0)
            center = math.hypot(dx, dy)/lifetime
            half = max(0.0, (settings.speed_max-settings.speed_min)/2.0)
            settings.speed_min = max(0.0, center-half); settings.speed_max = center+half
        elif self._guide_handle == "shape":
            if settings.spawn_shape == "line": settings.line_end_x, settings.line_end_y = x, y
            elif settings.spawn_shape == "circle": settings.radius = max(0.0, math.hypot(x-settings.origin_x, y-settings.origin_y))
            elif settings.spawn_shape == "box":
                settings.box_width = abs(x-settings.origin_x)*2; settings.box_height = abs(y-settings.origin_y)*2
        return before!=settings

    def _compose_display_frame(self) -> np.ndarray:
        assert self.project is not None
        if self.preview_frames is None:
            return self.project.compose_frame(self.frame_index,solo_preview=True)
        if not (0 <= self.frame_index < len(self.preview_frames)):
            return self.project.compose_frame(min(self.frame_index, len(self.project.frames) - 1),solo_preview=True)
        output = np.zeros((self.project.height, self.project.width, 4), dtype=np.float32)
        preview = self.preview_frames[self.frame_index]
        if preview.shape[:2] != output.shape[:2]:
            return self.project.compose_frame(min(self.frame_index, len(self.project.frames) - 1),solo_preview=True)
        project_frame = (
            self.project.frames[self.frame_index]
            if self.frame_index < len(self.project.frames)
            else None
        )
        replacement_seen = False
        logical_by_generated={item.generated_layer_id:item for item in self.project.effect_resource_layers};has_solo=any(item.solo for item in self.project.effect_resource_layers)
        for layer in self.project.layers:
            if not layer.visible:
                continue
            logical=logical_by_generated.get(layer.id)
            if has_solo and (logical is None or not logical.solo):continue
            if layer.id == self.preview_layer_id:
                source = preview
                replacement_seen = True
            elif project_frame is not None:
                source = project_frame.layer_pixels.get(layer.id)
            else:
                source = None
            if source is not None:
                self._composite(output, source, layer.opacity, project_layer_blend_mode(self.project,layer.id))
        if not replacement_seen and not has_solo:
            self._composite(output, preview, 1.0, project_layer_blend_mode(self.project,self.preview_layer_id))
        return np.clip(output * 255.0, 0, 255).astype(np.uint8)

    @staticmethod
    def _composite(output: np.ndarray, source: np.ndarray, opacity: float, blend_mode: str = BLEND_NORMAL) -> None:
        if source.shape[:2] != output.shape[:2]:
            return
        composite_rgba8_over_float32(output,source,opacity,blend_mode)
    gizmo_changed = Signal(str, object)
    effect_guide_changed = Signal(str, object, bool)
    effect_guide_started = Signal(str)
    effect_guide_cancelled = Signal(str, object)
    resource_transform_changed = Signal(str, object, bool)
    resource_transform_cancelled = Signal(str, object)
    resource_transform_started = Signal(str)
    layer_selected = Signal(int)
