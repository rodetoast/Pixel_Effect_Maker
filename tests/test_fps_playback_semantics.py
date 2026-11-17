"""Independent Resource/Effect timebases: exact source indices and RGBA."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from fractions import Fraction
import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QSettings
from app.models.project import Project
from app.services.resource_composition_render_service import render_composition_frame,composition_as_clip
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame as current,render_effect_resource_layer as full,apply_effect_resource_layer
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.export_service import export_png_frames
from app.services.particle_render_service import render_particle_frame,particle_spawn_states
from app.services.project_io import save_project,load_project
from app.services.settings_service import ShortcutSettingsService
from app.services.particle_preview_service import ParticleDraft,ParticlePreviewSession
from app.ui.main_window import MainWindow
from tests.test_native_regression_repair import rotation_project
from tests.test_effect_layer_group_workflow import _close


def fixture(turns=1,loop=True,mode='particle',effect_fps=24):
    p,c,sprite,layer=rotation_project(12,effect_fps,turns,loop)
    p.frames=p.frames[:48];c.frame_count=12;sprite.end_frame=11
    track=sprite.tracks['rotation'];track.keyframes.clear();track.set_keyframe(0,0);track.set_keyframe(11,330*turns)
    layer.end_frame=47;layer.placement_mode=mode
    layer.start_x=layer.end_x=layer.start_y=layer.end_y=12
    layer.particle_settings.output_frame_count=48
    layer.particle_settings.particle_count_min=layer.particle_settings.particle_count_max=1
    layer.particle_settings.lifetime_min=layer.particle_settings.lifetime_max=48
    layer.particle_settings.random_start_frame=False
    return p,c,sprite,layer


def assert_paths(p,c,layer,indices,tmp_path):
    expected=[render_composition_frame(p,c,index) for index in indices]
    frames=full(p,layer);generated=apply_effect_resource_layer(p,layer,frames)
    loaded=load_project(save_project(p,tmp_path/'saved'))
    paths=export_png_frames(p,tmp_path/'png')
    for frame in reversed(range(len(indices))):
        for pixels in (current(p,layer,frame),frames[frame],p.frames[frame].layer_pixels[generated.id],
                       render_exact_playback_frame(p,frame)[0],current(loaded,loaded.effect_resource_layers[0],frame),
                       np.asarray(Image.open(paths[frame]).convert('RGBA'))):
            np.testing.assert_array_equal(pixels,expected[frame],err_msg=f'output={frame},source={indices[frame]}')


@pytest.mark.parametrize('speed',[.5,1,2])
@pytest.mark.parametrize('turns',[1,2,-1])
@pytest.mark.parametrize('loop',[True,False])
def test_particle_timebases_speed_source_indices_rgba_png_reload(tmp_path,speed,turns,loop):
    p,c,sprite,layer=fixture(turns,loop)
    layer.particle_settings.clip_speed_min=layer.particle_settings.clip_speed_max=speed
    raw=[int(Fraction(frame*12,24)*Fraction(speed)) for frame in range(48)]
    indices=[index%12 if loop else min(index,11) for index in raw]
    actual=[]
    for frame in range(48):
        diagnostics=[];render_particle_frame(p,layer.as_particle_emitter(),frame,diagnostic_collector=diagnostics)
        assert len(diagnostics)==1
        actual.append(diagnostics[0].source_frame)
    assert actual==indices
    assert Fraction(12,12)/Fraction(speed)=={.5:Fraction(2),1:Fraction(1),2:Fraction(1,2)}[speed]
    if speed==2:assert actual[:12]==list(range(12)) and Fraction(12,p.fps)==Fraction(1,2)
    if speed==1:assert actual[:12]==[i//2 for i in range(12)]
    if speed==.5:assert actual[:12]==[i//4 for i in range(12)]
    assert [sprite.value('rotation',f) for f in range(12)]==[f*30*turns for f in range(12)]
    assert_paths(p,c,layer,indices,tmp_path)
    assert not current(p,layer,48)[...,3].any()  # particle lifetime, not source loop


@pytest.mark.parametrize('loop',[True,False])
def test_single_output_fps_is_time_preserving_and_end_is_inclusive(tmp_path,loop):
    p,c,_,layer=fixture(loop=loop,mode='single')
    indices=[(i//2)%12 if loop else min(i//2,11) for i in range(48)]
    assert_paths(p,c,layer,indices,tmp_path)
    assert not current(p,layer,48)[...,3].any()  # Single active end=47


@pytest.mark.parametrize('mode',['single','particle'])
@pytest.mark.parametrize('turns',[1,2,-1])
def test_resource_fps_ui_keeps_frames_keys_and_invalidates_all_paths(tmp_path,mode,turns):
    p,c,sprite,layer=fixture(turns,mode=mode)
    before_keys=deepcopy(sprite.to_dict());before_images=[render_composition_frame(p,c,i) for i in range(12)]
    full(p,layer)  # deliberately warm the old base/clip caches
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat)),p)
    try:
        editor=window.resource_editor;editor.refresh(p);editor.controller.select_composition(c.id,sprite.id)
        editor.clear_layer_selection()
        assert editor.inspector_stack.currentWidget() is editor.composition_inspector
        window.application_undo_stack.clear();window.application_undo_stack.setClean()
        editor.composition_inspector.fps.setValue(24)
        assert c.fps==24 and c.frame_count==12 and Fraction(c.frame_count,c.fps)==Fraction(1,2)
        assert p.fps==24 and sprite.to_dict()==before_keys
        assert window.application_undo_stack.count()==1 and window.dirty
        for i in range(12):np.testing.assert_array_equal(render_composition_frame(p,c,i),before_images[i])
        assert composition_as_clip(p,c).fps==24
        for i in range(12):
            window.select_frame(i)
            np.testing.assert_array_equal(p.frames[i].layer_pixels[layer.generated_layer_id],before_images[i])
        assert_paths(p,c,layer,[i%12 for i in range(48)],tmp_path)
        window.application_undo_stack.undo()
        assert c.fps==12 and c.frame_count==12 and sprite.to_dict()==before_keys
        np.testing.assert_array_equal(current(p,layer,1),before_images[0])
        np.testing.assert_array_equal(p.frames[1].layer_pixels[layer.generated_layer_id],before_images[0])
        window.application_undo_stack.redo()
        assert c.fps==24 and c.frame_count==12
        np.testing.assert_array_equal(current(p,layer,1),before_images[1])
    finally:_close(window)


def test_random_start_offsets_are_not_confused_with_source_speed():
    p,_,_,layer=fixture()
    s=layer.particle_settings;s.random_start_frame=True
    s.particle_count_min=s.particle_count_max=8;s.clip_speed_min=s.clip_speed_max=2
    starts=[item.clip_start_frame for item in particle_spawn_states(s,12)]
    assert any(starts)
    diagnostics=[];render_particle_frame(p,layer.as_particle_emitter(),1,diagnostic_collector=diagnostics)
    assert [item.source_frame for item in diagnostics]==[(start+1)%12 for start in starts]


def test_resource_fps_edit_rejects_old_preview_result_without_discarding_draft(tmp_path):
    p,c,_,layer=fixture()
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat)),p)
    try:
        manager=window.particle_preview_manager;draft=manager.ensure_draft(layer.as_particle_emitter())
        draft.settings.seed=987;draft.is_dirty=True
        unrelated=deepcopy(draft.settings);unrelated.clip_asset_id='different-resource'
        manager.drafts['other']=ParticleDraft('other',unrelated)
        manager.sessions['other']=ParticlePreviewSession('other',0,[])
        context=manager._context_revision;revision=draft.revision
        editor=window.resource_editor;editor.refresh(p);editor.controller.select_composition(c.id)
        editor.composition_inspector.fps.setValue(24)
        # Deterministic completion gate: an old-FPS worker returns after edit.
        manager._queue.put((context,layer.id,revision,[],''));manager._drain()
        assert layer.id not in manager.sessions, 'old Resource FPS result was accepted'
        assert draft.settings.seed==987 and draft.is_dirty
        assert manager.drafts['other'].revision==0 and 'other' in manager.sessions
    finally:_close(window)


def test_resource_change_cancels_pending_preview_not_just_completed_session(tmp_path):
    p,c,_,layer=fixture()
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat)),p)
    try:
        manager=window.particle_preview_manager
        manager.update(p,layer.as_particle_emitter(),deepcopy(layer.particle_settings))
        assert manager._pending is not None and manager._timer.isActive()
        window.resource_composition_changed(c.id)
        assert manager._pending is None and not manager._timer.isActive()
    finally:_close(window)


@pytest.mark.parametrize('language',['ko','en'])
def test_timebase_help_is_translated_and_view_only(tmp_path,language):
    p,c,_,layer=fixture()
    settings=QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat);settings.setValue('ui/language',language)
    window=MainWindow(ShortcutSettingsService(settings),p)
    try:
        window.select_resource_layer(layer.id)
        before=deepcopy(p.to_dict());count=window.application_undo_stack.count()
        text=window.particle_properties.workflow.source_timing_help.text()
        assert '12' in text and '24' in text and '2×' in text and '0.5' in text
        assert '2×' in window.particle_properties.clip_speed_min.toolTip()
        window.resource_editor.refresh(p);window.resource_editor.controller.select_composition(c.id)
        assert '24' in window.resource_editor.composition_inspector.fps.toolTip()
        assert p.to_dict()==before and window.application_undo_stack.count()==count
    finally:_close(window)


def test_effect_fps_and_ui_exact_speed_change_do_not_retime_resource(tmp_path):
    p,c,sprite,layer=fixture(effect_fps=12)
    before=deepcopy(c.to_dict())
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat)),p)
    try:
        window.set_fps(24)
        assert c.to_dict()==before and len(p.frames)==48
        np.testing.assert_array_equal(current(p,layer,1),render_composition_frame(p,c,0))
        window.select_resource_layer(layer.id)
        window.application_undo_stack.clear()
        window.particle_properties.clip_speed_min.setValue(2)
        assert layer.particle_settings.clip_speed_min==layer.particle_settings.clip_speed_max==2
        assert not layer.particle_settings.random_start_frame
        assert window.application_undo_stack.count()==1
        for i in range(12):
            np.testing.assert_array_equal(current(p,layer,i),render_composition_frame(p,c,i))
        window.application_undo_stack.undo()
        np.testing.assert_array_equal(current(p,layer,1),render_composition_frame(p,c,0))
        window.application_undo_stack.redo()
        np.testing.assert_array_equal(current(p,layer,1),render_composition_frame(p,c,1))
        assert c.to_dict()==before
    finally:_close(window)
