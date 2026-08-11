import os
from copy import deepcopy
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.particle_emitter import ParticleEmitterSettings, ParticleMotionSettings
from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import (
    apply_effect_resource_layer,
    render_effect_resource_layer,
    render_effect_resource_layer_current_frame,
)
from app.services.particle_render_service import (
    PARTICLE_RENDER_STATS,
    particle_spawn_states,
    render_particle_frame,
)
from app.services.project_io import load_project, save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def particle_project(mode="linear", frames=24):
    project=Project.create_default(name=f"{mode}-current",width=40,height=40,fps=24,frame_count=frames)
    pixels=np.zeros((3,3,4),dtype=np.uint8);pixels[1,1]=[255,100,20,255]
    asset=SourceAsset("spark",pixels,pivot_x=1,pivot_y=1)
    composition=ResourceComposition("spark",3,3,24,1,True)
    composition.layers.append(CompositionLayer("spark","source_asset",asset.id,0,0,pivot_x=1,pivot_y=1))
    project.source_assets.append(asset);project.resource_compositions.append(composition)
    motion=ParticleMotionSettings(mode=mode,radius_start=0,radius_end=10,turns=1,
        phase_spread_degrees=0,helix_axis="z",axis_start=-3,axis_end=4,perspective_strength=0)
    settings=ParticleEmitterSettings(composition.id,resource_type="resource_composition",output_frame_count=frames,
        particle_count_min=4,particle_count_max=4,lifetime_min=frames,lifetime_max=frames,
        speed_min=1,speed_max=1,direction_degrees=0,direction_spread_degrees=0,
        origin_x=15,origin_y=20,seed=71,motion=motion)
    layer=EffectResourceLayer("particles",composition.id,placement_mode=PLACEMENT_PARTICLE,
        end_frame=frames-1,particle_settings=settings)
    project.effect_resource_layers.append(layer)
    apply_effect_resource_layer(project,layer)
    return project,layer


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_current_frame_matches_full_sequence_and_playback_every_frame(mode):
    project,layer=particle_project(mode);full=render_effect_resource_layer(project,layer)
    generated=next(item for item in project.layers if item.id==layer.generated_layer_id)
    for frame in range(24):
        direct=render_effect_resource_layer_current_frame(project,layer,frame)
        playback,_=render_exact_playback_frame(project,frame)
        expected=deepcopy(project);expected.frames[frame].layer_pixels[generated.id]=direct
        assert np.array_equal(direct,full[frame])
        assert np.array_equal(playback,expected.compose_frame(frame))


@pytest.mark.parametrize("order",[
    tuple(range(24)),tuple(reversed(range(24))),
    (7,2,15,3,9,9,1,20,6,23,0,11,4,18),
    (12,12,12),
])
def test_current_frame_is_independent_of_access_order(order):
    project,layer=particle_project("helix");emitter=layer.as_particle_emitter()
    reference={frame:render_particle_frame(project,emitter,frame) for frame in set(order)}
    actual=[(frame,render_particle_frame(project,emitter,frame)) for frame in order]
    assert all(np.array_equal(value,reference[frame]) for frame,value in actual)


def test_particle_state_diagnostics_have_exact_age_position_source_and_depth():
    project,layer=particle_project("linear");emitter=layer.as_particle_emitter();states=[]
    render_particle_frame(project,emitter,5,diagnostic_collector=states)
    assert states and all(item.age==5-item.spawn_frame for item in states)
    assert all(item.normalized_age==item.age/item.lifetime for item in states)
    assert all(item.x==pytest.approx(15+item.age) and item.y==pytest.approx(20) for item in states)
    assert all(item.source_frame==0 and item.depth_key==(item.z,item.generation_order) for item in states)


def test_spawn_state_is_immutable_and_boundary_ages_are_exact():
    project,layer=particle_project("linear");emitter=layer.as_particle_emitter()
    instances=particle_spawn_states(emitter.settings,1);before=tuple(instances)
    for frame in (0,1,22,23,24):render_particle_frame(project,emitter,frame,instances=instances)
    assert instances==before
    at_spawn=[];after_spawn=[];at_end=[]
    render_particle_frame(project,emitter,0,instances=instances,diagnostic_collector=at_spawn)
    render_particle_frame(project,emitter,1,instances=instances,diagnostic_collector=after_spawn)
    render_particle_frame(project,emitter,23,instances=instances,diagnostic_collector=at_end)
    assert {item.age for item in at_spawn}=={0}
    assert {item.age for item in after_spawn}=={1}
    assert {item.age for item in at_end}=={23}


def test_metadata_round_trip_stale_buffers_reproduce_spawn_origin_but_timeline_installs_exact(tmp_path):
    project,layer=particle_project("orbit")
    # Persist an old radius-zero bake, then save only the updated motion metadata.
    layer.particle_settings.motion.radius_end=0;layer.particle_settings.motion.revision+=1
    apply_effect_resource_layer(project,layer)
    layer.particle_settings.motion.radius_end=10;layer.particle_settings.motion.revision+=1
    target=save_project(project,tmp_path/"stale-current")
    loaded=load_project(target);loaded_layer=loaded.effect_resource_layers[0]
    stale=[loaded.compose_frame(frame) for frame in range(24)]
    exact=[render_exact_playback_frame(loaded,frame)[0] for frame in range(24)]
    divergent=[frame for frame in range(24) if not np.array_equal(stale[frame],exact[frame])]
    assert divergent and 0 not in divergent

    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"ui.ini"),QSettings.Format.IniFormat)),loaded)
    full_before=PARTICLE_RENDER_STATS["full_sequence_renders"]
    for frame in range(24):
        window.select_frame(frame)
        assert np.array_equal(window.canvas._compose_display_frame(),exact[frame])
    assert PARTICLE_RENDER_STATS["full_sequence_renders"]==full_before

    # Exercise the real Timeline cell signal, including its 0-based conversion.
    frame=17;row=len(loaded.layers)-1-window.layer_index
    window.timeline.table.setCurrentCell(row,frame+window.timeline.FRAME_COLUMN_OFFSET);APP.processEvents()
    assert window.frame_index==window.canvas.frame_index==frame
    assert np.array_equal(window.canvas._compose_display_frame(),exact[frame])
    window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_stale_gizmo_worker_result_for_old_frame_is_rejected(tmp_path,monkeypatch):
    project,layer=particle_project("orbit");window=MainWindow(
        ShortcutSettingsService(QSettings(str(tmp_path/"stale.ini"),QSettings.Format.IniFormat)),project)
    window.select_frame(7);calls=[]
    monkeypatch.setattr(window.canvas,"apply_interactive_motion_proxy",lambda *args: calls.append(args) or True)
    from app.services.interactive_gizmo_service import GizmoRenderRequest,GizmoRenderResult
    request=GizmoRenderRequest(1,id(project),deepcopy(layer),6,False)
    window._interactive_gizmo_frame_ready(GizmoRenderResult(request,np.zeros((40,40,4),dtype=np.uint8),None,(),{}))
    assert calls==[]
    window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def _wait_playback(window,minimum=24,timeout_ms=4000):
    started=perf_counter()
    while len(window.effect_playback.cache)<minimum and (perf_counter()-started)*1000<timeout_ms:APP.processEvents()
    assert len(window.effect_playback.cache)>=minimum


def test_paused_current_frame_does_not_depend_on_playback_cache(tmp_path):
    project,_=particle_project("orbit");window=MainWindow(
        ShortcutSettingsService(QSettings(str(tmp_path/"cache.ini"),QSettings.Format.IniFormat)),project)
    window.select_frame(9);cold=window.canvas._compose_display_frame().copy()
    window.set_playing(True);_wait_playback(window);window.set_playing(False)
    window.canvas.clear_playback_frame();window.select_frame(9);warm=window.canvas._compose_display_frame().copy()
    assert np.array_equal(cold,warm)
    window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_playback_stop_frame_matches_paused_direct_frame(tmp_path):
    project,_=particle_project("helix");window=MainWindow(
        ShortcutSettingsService(QSettings(str(tmp_path/"stop.ini"),QSettings.Format.IniFormat)),project)
    window.set_playing(True);_wait_playback(window);window._select_playback_frame(13)
    cached=window.effect_playback.get(window._playback_key(13));assert cached is not None
    window.set_playing(False);window.canvas.clear_playback_frame();window.select_frame(13)
    assert np.array_equal(window.canvas._compose_display_frame(),cached.rgba)
    window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()
