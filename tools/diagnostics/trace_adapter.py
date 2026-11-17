"""Opt-in, bounded developer tracing. No production hooks or payload logging."""
from contextlib import contextmanager, ExitStack
from functools import wraps
from time import monotonic
from unittest.mock import patch

@contextmanager
def trace_adapters(enabled,events):
    if not enabled:
        yield
        return
    from app.ui.main_window import MainWindow
    from app.models.project import Project
    from app.services import effect_resource_layer_render_service as render
    from app.services.particle_preview_service import ParticlePreviewManager
    started=monotonic()
    counts={}
    def emit(event,**fields):
        count=counts.get(event,0);counts[event]=count+1
        # A hot cache stream must not exhaust the budget before FPS/Undo events.
        if count<100 and len(events)<2000:
            events.append(dict(event=event,elapsed_seconds=round(monotonic()-started,6),**fields))
    def wrap(owner,name,event,measure):
        original=getattr(owner,name)
        @wraps(original)
        def method(*args,**kwargs):
            before=measure(args)
            try:result=original(*args,**kwargs)
            except Exception:
                emit(event,outcome="exception",**before);raise
            after=measure(args)
            outcome=("accepted" if result is not None and result is not False else "rejected") if event.startswith("undo_command_") else "rejected" if result is False else "returned"
            emit(event,outcome=outcome,changed=before!=after,**after)
            return result
        return patch.object(owner,name,method)
    selection=lambda a:dict(selection_count=len(a[0].effect_layer_selection.selected_ids))
    fps=lambda a:dict(fps=int(a[0].project.fps),frame_count=len(a[0].project.frames))
    with ExitStack() as stack:
        for name,event,measure in (("select_effect_layers_with_modifiers","selection_changed",selection),("create_effect_group_selected","undo_command_group",selection),("ungroup_effect","undo_command_ungroup",selection),("_undo_index_changed","undo_index_changed",selection),("set_fps","fps_changed",fps),("_refresh_resource_timing_outputs","derived_output_invalidated",fps)):
            stack.enter_context(wrap(MainWindow,name,event,measure))
        stack.enter_context(wrap(Project,"add_frame","frame_count_changed",lambda a:dict(frame_count=len(a[0].frames))))
        stack.enter_context(wrap(ParticlePreviewManager,"reset_context","render_session_changed",lambda a:dict(generation=a[0]._context_revision)))
        original=render.render_effect_resource_layer_base
        @wraps(original)
        def base(project,layer):
            key=render._base_key(project,layer);cached=render._BASE_CACHE.get(layer.id)
            emit("base_cache",hit=cached is not None and cached[0]==key)
            return original(project,layer)
        stack.enter_context(patch.object(render,"render_effect_resource_layer_base",base))
        try:yield
        finally:events.append(dict(event="trace_summary",recorded=len(events),dropped=sum(counts.values())-len(events)))
