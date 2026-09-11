from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import LifetimeColorModulation, LifetimeScalarModulation, ParticleEmitter, ParticleEmitterSettings, ParticleMotionSettings
from app.models.project import Project
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import render_transformed_source
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer, render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.lifetime_modulation_service import eased_lifetime_amount, evaluate_lifetime_color_component
from app.services.particle_render_service import build_particle_instances, render_particle_frame
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def _color(enabled=True,start=(241,13,73),end=(17,199,226),easing="Linear"):
    return LifetimeColorModulation(enabled,start,end,easing)


def _project(*,mode="linear",births=False,color=None,scale=None,pixels=None,opacity=.37):
    project=Project.create_default(width=16,height=16,fps=12,frame_count=8)
    rgba=np.array([[[200,100,50,180]]],dtype=np.uint8) if pixels is None else np.asarray(pixels,dtype=np.uint8)
    clip=AnimationClipAsset("dot",[rgba],fps=12,pivot_x=0,pivot_y=0,playback_mode="hold");project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=8,particle_count_min=2 if births else 1,particle_count_max=2 if births else 1,
        emission_mode="over_time" if births else "burst",emission_duration=3,start_delay_min=0,start_delay_max=0,lifetime_min=5,lifetime_max=5,
        origin_x=5,origin_y=6,speed_min=0,speed_max=0,scale_min=1,scale_max=1,opacity_start=opacity,opacity_end=opacity,seed=73,
        motion=ParticleMotionSettings(mode=mode,radius_start=2,radius_end=6,turns=.5,axis_start=-2,axis_end=2),
        scale_over_lifetime=scale or LifetimeScalarModulation(),color_over_lifetime=color or LifetimeColorModulation())
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("particles",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy();return project,layer


def _diagnostics(project,layer,frame):
    values=[];render_particle_frame(project,layer.as_particle_emitter(),frame,diagnostic_collector=values);return values


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def _window(tmp_path,color=None):
    project,layer=_project(color=color);apply_effect_resource_layer(project,layer);window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"color.ini"),QSettings.Format.IniFormat)),project);window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False;return window,layer


def test_color_lifetime_disabled_is_identity():
    channel=_color(False,(0,1,2),(3,4,5),"Ease In/Out")
    assert [evaluate_lifetime_color_component(channel,.5,index) for index in range(3)]==[1,1,1]


@pytest.mark.parametrize(("easing","expected"),[("Linear",.5),("Ease In",.25),("Ease Out",.75),("Ease In/Out",.5)])
def test_color_lifetime_start_middle_end_and_easing(easing,expected):
    channel=_color(True,(0,0,0),(255,128,64),easing)
    assert evaluate_lifetime_color_component(channel,0,0)==0
    assert evaluate_lifetime_color_component(channel,1,0)==1
    assert evaluate_lifetime_color_component(channel,.5,0)==pytest.approx(expected)
    assert evaluate_lifetime_color_component(channel,.5,1)==pytest.approx((128*expected)/255)


def test_color_lifetime_age_clamps_and_rgb_channels_do_not_cross():
    channel=_color(True,(241,13,73),(17,199,226))
    assert eased_lifetime_amount(-1,"Linear")==0 and eased_lifetime_amount(2,"Linear")==1
    middle=[evaluate_lifetime_color_component(channel,.5,index) for index in range(3)]
    assert middle==pytest.approx((129/255,106/255,149.5/255))


@pytest.mark.parametrize("channel",[
    LifetimeColorModulation("false"),LifetimeColorModulation(True,(256,0,0),(0,0,0)),
    LifetimeColorModulation(True,(-1,0,0),(0,0,0)),LifetimeColorModulation(True,(1.0,0,0),(0,0,0)),
    LifetimeColorModulation(True,(0,0),(0,0,0)),LifetimeColorModulation(True,(0,0,0),(0,0,0),"Unknown"),
])
def test_color_lifetime_rejects_invalid_persistent_values(channel):
    with pytest.raises(ValueError):channel.validate()


def test_rgb_tint_multiplies_source_in_encoded_rgb_and_keeps_straight_alpha():
    source=np.array([[[200,100,50,128],[77,88,99,0]]],dtype=np.uint8);asset=SourceAsset("source",source,pivot_x=0,pivot_y=0);output=np.zeros((2,3,4),dtype=np.uint8)
    render_transformed_source(output,asset,position_x=0,position_y=0,rotation=0,scale_x=1,scale_y=1,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=.5,tint_r=.5,tint_g=.25,tint_b=1)
    assert tuple(output[0,0])==(100,25,50,64)
    assert output[0,2,3]==0 and not np.any(output[0,2,3:])


def test_disabled_color_render_is_bit_exact_and_seed_sequence_is_unchanged():
    a,la=_project(color=LifetimeColorModulation());b,lb=_project(color=_color(False,(0,1,2),(3,4,5),"Ease Out"))
    assert build_particle_instances(la.particle_settings,1)==build_particle_instances(lb.particle_settings,1)
    assert all(np.array_equal(x,y) for x,y in zip(render_effect_resource_layer(a,la),render_effect_resource_layer(b,lb),strict=True))


def test_different_birth_times_have_independent_lifetime_colors():
    project,layer=_project(births=True,color=_color(True,(0,0,0),(255,255,255)))
    by_birth={item.spawn_frame:item for item in _diagnostics(project,layer,2)}
    assert set(by_birth)=={0,2};assert by_birth[0].lifetime_tint_r==pytest.approx(.5);assert by_birth[2].lifetime_tint_r==0


def test_scale_and_color_channels_work_together_without_mutating_each_other():
    scale=LifetimeScalarModulation(True,.5,2,"Ease Out");color=_color(True,(255,0,0),(0,0,255),"Ease In")
    project,layer=_project(scale=scale,color=color);before=deepcopy(layer.particle_settings.to_dict());value=_diagnostics(project,layer,2)[0]
    assert value.lifetime_scale==pytest.approx(1.625);assert (value.lifetime_tint_r,value.lifetime_tint_g,value.lifetime_tint_b)==pytest.approx((.75,0,.25))
    assert layer.particle_settings.to_dict()==before


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_color_lifetime_works_in_all_motion_modes_without_changing_trajectory(mode):
    plain,plain_layer=_project(mode=mode);colored,colored_layer=_project(mode=mode,color=_color(True,(255,128,64),(64,128,255),"Ease Out"))
    for frame in range(5):
        a=_diagnostics(plain,plain_layer,frame)[0];b=_diagnostics(colored,colored_layer,frame)[0]
        assert (a.local_x,a.local_y,a.local_z,a.x,a.y)==pytest.approx((b.local_x,b.local_y,b.local_z,b.x,b.y))


def test_color_lifetime_does_not_modify_particle_or_layer_alpha_or_alpha_easing():
    project,layer=_project(color=_color(True,(255,0,0),(0,0,255),"Ease In/Out"),opacity=.37);layer.particle_settings.easing="Ease Out";layer.layer_space_transform.opacity=.6;layer.layer_space_transform.set_keyframe("opacity",2,.4,"Ease In")
    before=deepcopy(layer.to_dict());values=[]
    for frame in (0,2,4):values.extend(_diagnostics(project,layer,frame))
    assert all(value.opacity==pytest.approx(.37) for value in values)
    assert layer.particle_settings.opacity_start==layer.particle_settings.opacity_end==.37 and layer.particle_settings.easing=="Ease Out" and layer.layer_space_transform.opacity==.6 and layer.to_dict()==before


def test_preview_full_materialized_and_export_color_match_with_strict_dimensions(tmp_path):
    project,layer=_project(color=_color(True,(255,255,0),(255,0,0),"Ease Out"));full=render_effect_resource_layer(project,layer)
    for frame in range(8):assert np.array_equal(render_effect_resource_layer_current_frame(project,layer,frame),full[frame])
    generated=apply_effect_resource_layer(project,layer,full);paths=export_png_frames(project,tmp_path/"png")
    from PIL import Image
    for frame,path in enumerate(paths):
        decoded=np.asarray(Image.open(path));assert decoded.shape==(16,16,4);assert np.array_equal(decoded,project.compose_frame(frame));assert np.array_equal(project.frames[frame].layer_pixels[generated.id],full[frame])


def test_color_lifetime_ui_refresh_is_exact_and_disabled_controls_preserve_values():
    project,layer=_project(color=_color(False,(241,162,3),(23,201,228),"Ease Out"));from app.ui.particle_properties_panel import ParticlePropertiesPanel
    panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1));panel.set_resource_layer(layer,project)
    for _ in range(4):panel.set_resource_layer(layer,project)
    assert not panel.color_lifetime_enabled.isChecked() and not panel.color_lifetime_start.isEnabled() and not panel.color_lifetime_end.isEnabled()
    assert panel._color_lifetime_start==(241,162,3) and panel._color_lifetime_end==(23,201,228) and panel.color_lifetime_easing.currentData()=="Ease Out" and changes==[]
    panel.color_lifetime_enabled.setChecked(True);assert panel.color_lifetime_start.isEnabled() and panel._color_lifetime_start==(241,162,3) and len(changes)==1;panel.close()


def test_color_picker_cancel_and_noop_do_not_mutate_or_push_undo(tmp_path,monkeypatch):
    window,layer=_window(tmp_path,color=_color(True,(10,20,30),(40,50,60)));before=deepcopy(layer.to_dict());revision=window._project_edit_revision
    monkeypatch.setattr("app.ui.particle_properties_panel.QColorDialog.getColor",lambda *args:QColor())
    window.particle_properties._choose_lifetime_color(True)
    monkeypatch.setattr("app.ui.particle_properties_panel.QColorDialog.getColor",lambda *args:QColor(10,20,30))
    window.particle_properties._choose_lifetime_color(True)
    assert layer.to_dict()==before and window.application_undo_stack.count()==0 and window._project_edit_revision==revision and not window.dirty;_close(window)


def test_each_color_user_commit_is_one_undo_and_redo_is_exact(tmp_path,monkeypatch):
    window,layer=_window(tmp_path);panel=window.particle_properties
    panel.color_lifetime_enabled.setChecked(True)
    monkeypatch.setattr("app.ui.particle_properties_panel.QColorDialog.getColor",lambda *args:QColor(241,13,73,7));panel._choose_lifetime_color(True)
    monkeypatch.setattr("app.ui.particle_properties_panel.QColorDialog.getColor",lambda *args:QColor(17,199,226));panel._choose_lifetime_color(False)
    panel.color_lifetime_easing.setCurrentIndex(panel.color_lifetime_easing.findData("Ease Out"));APP.processEvents()
    expected=_color(True,(241,13,73),(17,199,226),"Ease Out");assert window.application_undo_stack.count()==4 and layer.particle_settings.color_over_lifetime==expected and layer.particle_settings.scale_over_lifetime==LifetimeScalarModulation()
    for _ in range(4):window.application_undo_stack.undo()
    assert layer.particle_settings.color_over_lifetime==LifetimeColorModulation()
    for _ in range(4):window.application_undo_stack.redo()
    assert layer.particle_settings.color_over_lifetime==expected;_close(window)


def test_color_selection_change_preserves_each_layer_and_edits_primary_only(tmp_path,monkeypatch):
    window,first=_window(tmp_path,color=_color(True,(241,162,3),(23,201,228),"Ease Out"));second=window.duplicate_resource_layer(first.id);second.particle_settings.color_over_lifetime=_color(True,(1,2,3),(4,5,6),"Ease In")
    window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False;revision=window._project_edit_revision;before=(deepcopy(first.to_dict()),deepcopy(second.to_dict()))
    window.select_resource_layer(first.id);window.select_resource_layer(second.id);window.select_resource_layer(first.id)
    assert window.particle_properties._color_lifetime_start==(241,162,3) and first.particle_settings.color_over_lifetime.easing=="Ease Out" and second.particle_settings.color_over_lifetime.easing=="Ease In"
    assert (first.to_dict(),second.to_dict())==before and window.application_undo_stack.count()==0 and window._project_edit_revision==revision and not window.dirty
    window.select_effect_layers_with_modifiers(first.id);window.select_effect_layers_with_modifiers(second.id,Qt.KeyboardModifier.ControlModifier);window.application_undo_stack.clear()
    monkeypatch.setattr("app.ui.particle_properties_panel.QColorDialog.getColor",lambda *args:QColor(7,8,9));window.particle_properties._choose_lifetime_color(True)
    assert second.particle_settings.color_over_lifetime.start_rgb==(7,8,9) and first.particle_settings.color_over_lifetime.start_rgb==(241,162,3) and window.application_undo_stack.count()==1;_close(window)


@pytest.mark.parametrize(("name","start","end"),[("Fire",(255,255,0),(255,0,0)),("Magic",(255,255,255),(0,80,255)),("Poison",(220,60,255),(70,0,100)),("Hit Spark",(255,255,255),(255,128,0))])
def test_representative_color_fixtures_improve_rgb_authoring(name,start,end):
    project,layer=_project(color=_color(True,start,end,"Ease Out"));layer.name=name;a=_diagnostics(project,layer,0)[0];b=_diagnostics(project,layer,4)[0]
    assert (a.lifetime_tint_r,a.lifetime_tint_g,a.lifetime_tint_b)==pytest.approx(tuple(value/255 for value in start));assert (b.lifetime_tint_r,b.lifetime_tint_g,b.lifetime_tint_b)==pytest.approx(tuple(value/255 for value in end))
