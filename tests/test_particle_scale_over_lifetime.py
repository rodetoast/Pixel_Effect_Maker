from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.particle_emitter import LifetimeScalarModulation, ParticleEmitter, ParticleEmitterSettings, ParticleInstance, ParticleMotionSettings
from app.models.project import FORMAT_VERSION, Project
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer, render_effect_resource_layer_current_frame
from app.services.export_service import export_png_frames
from app.services.lifetime_modulation_service import evaluate_lifetime_scalar, normalized_lifetime_age
from app.services.particle_render_service import build_particle_instances, render_particle_frame
from app.services.project_io import load_project, save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def _channel(enabled=True,start=0.0,end=1.0,easing="Linear"):
    return LifetimeScalarModulation(enabled,start,end,easing)


def _project(mode="linear",births=False,modulation=None):
    project=Project.create_default(width=32,height=24,fps=12,frame_count=8)
    pixels=np.full((3,3,4),255,dtype=np.uint8);clip=AnimationClipAsset("dot",[pixels],fps=12,pivot_x=1,pivot_y=1,playback_mode="hold");project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=8,particle_count_min=2 if births else 1,particle_count_max=2 if births else 1,
        emission_mode="over_time" if births else "burst",emission_duration=3,start_delay_min=0,start_delay_max=0,
        lifetime_min=5,lifetime_max=5,origin_x=8,origin_y=12,speed_min=1,speed_max=1,direction_degrees=0,direction_spread_degrees=0,
        scale_min=1.25,scale_max=1.25,seed=91,motion=ParticleMotionSettings(mode=mode,radius_start=2,radius_end=6,turns=.5,axis_start=-2,axis_end=2),
        scale_over_lifetime=modulation or LifetimeScalarModulation())
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("particles",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def _diagnostics(project,layer,frame):
    values=[];render_particle_frame(project,layer.as_particle_emitter(),frame,diagnostic_collector=values);return values


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_lifetime_scale_disabled_returns_one():
    assert evaluate_lifetime_scalar(_channel(False,0,16,"Ease In/Out"),.4)==1


def test_lifetime_age_and_linear_boundaries_are_exact_and_clamped():
    channel=_channel(True,.2,1.2)
    assert normalized_lifetime_age(0,5)==0 and normalized_lifetime_age(2,5)==.5 and normalized_lifetime_age(4,5)==1
    assert normalized_lifetime_age(-9,5)==0 and normalized_lifetime_age(99,5)==1
    assert evaluate_lifetime_scalar(channel,0)==pytest.approx(.2)
    assert evaluate_lifetime_scalar(channel,.5)==pytest.approx(.7)
    assert evaluate_lifetime_scalar(channel,1)==pytest.approx(1.2)


@pytest.mark.parametrize(("easing","expected"),[("Ease In",.25),("Ease Out",.75),("Ease In/Out",.5)])
def test_lifetime_scale_easings(easing,expected):
    assert evaluate_lifetime_scalar(_channel(True,0,1,easing),.5)==pytest.approx(expected)


def test_zero_or_one_frame_lifetime_is_safe_end_state():
    channel=_channel(True,.25,2)
    for lifetime in (-1,0,1):
        age=normalized_lifetime_age(0,lifetime);value=evaluate_lifetime_scalar(channel,age)
        assert age==1 and value==2 and np.isfinite(value)


@pytest.mark.parametrize("channel",[
    LifetimeScalarModulation(True,-.01,1),LifetimeScalarModulation(True,1,16.01),
    LifetimeScalarModulation(True,float("nan"),1),LifetimeScalarModulation(True,0,1,"Unknown"),
    LifetimeScalarModulation("false",0,1),
])
def test_lifetime_scale_rejects_invalid_or_negative_values(channel):
    with pytest.raises(ValueError):channel.validate()


def test_lifetime_scale_multiplies_base_and_preserves_xy_ratio(monkeypatch):
    project,layer=_project(modulation=_channel(True,.5,.5));layer.layer_space_transform.scale_x=2;layer.layer_space_transform.scale_y=1
    captured=[]
    monkeypatch.setattr("app.services.particle_render_service.render_transformed_source",lambda _o,_a,**values:captured.append((values["scale_x"],values["scale_y"])))
    render_particle_frame(project,layer.as_particle_emitter(),0,layer_space_transform=layer.layer_space_transform)
    assert captured==[(pytest.approx(1.25),pytest.approx(.625))] and captured[0][0]/captured[0][1]==pytest.approx(2)


def test_lifetime_scale_preserves_random_base_scale_and_rng_sequence():
    project,layer=_project();settings=layer.particle_settings;settings.particle_count_min=8;settings.particle_count_max=8;settings.scale_min=.4;settings.scale_max=1.6
    before=build_particle_instances(deepcopy(settings),1);settings.scale_over_lifetime=_channel(True,.2,1.8,"Ease Out");after=build_particle_instances(settings,1)
    assert before==after and len({item.scale for item in after})>1


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
def test_scale_progression_is_independent_of_motion(mode):
    base_project,base_layer=_project(mode,modulation=_channel(False));scaled_project,scaled_layer=_project(mode,modulation=_channel(True,.2,1.8,"Ease Out"))
    for frame in range(5):
        base=_diagnostics(base_project,base_layer,frame)[0];scaled=_diagnostics(scaled_project,scaled_layer,frame)[0]
        assert (scaled.x,scaled.y,scaled.z)==pytest.approx((base.x,base.y,base.z))
        assert scaled.scale==pytest.approx(base.scale*scaled.lifetime_scale)


def test_different_birth_times_use_independent_normalized_lifetime():
    project,layer=_project(births=True,modulation=_channel(True,0,1))
    values=_diagnostics(project,layer,2);by_birth={item.spawn_frame:item for item in values}
    assert set(by_birth)=={0,2};assert by_birth[0].lifetime_scale==pytest.approx(.5);assert by_birth[2].lifetime_scale==0


def test_disabled_render_is_bit_exact_with_default_and_does_not_change_seed():
    a,la=_project(modulation=LifetimeScalarModulation());b,lb=_project(modulation=_channel(False,0,16,"Ease In/Out"))
    assert build_particle_instances(la.particle_settings,1)==build_particle_instances(lb.particle_settings,1)
    assert all(np.array_equal(x,y) for x,y in zip(render_effect_resource_layer(a,la),render_effect_resource_layer(b,lb),strict=True))


def test_format12_defaults_disabled_and_old_render_is_preserved():
    project,layer=_project();old_frames=render_effect_resource_layer(project,layer);payload=project.to_dict();payload["format_version"]=12
    for item in payload["effect_resource_layers"]:item["particle_settings"].pop("scale_over_lifetime",None)
    loaded=Project.from_dict(payload);restored=loaded.effect_resource_layers[0]
    assert not restored.particle_settings.scale_over_lifetime.enabled
    assert restored.particle_settings.scale_over_lifetime.to_dict()=={"enabled":False,"start":1.0,"end":1.0,"easing":"Linear"}
    assert all(np.array_equal(x,y) for x,y in zip(old_frames,render_effect_resource_layer(loaded,restored),strict=True))


@pytest.mark.parametrize("easing",["Linear","Ease In","Ease Out","Ease In/Out"])
def test_format13_round_trip_is_exact(tmp_path,easing):
    project,layer=_project(modulation=_channel(True,.25,2,easing));path=save_project(project,tmp_path/"lifetime")
    loaded=load_project(path);value=loaded.effect_resource_layers[0].particle_settings.scale_over_lifetime
    assert FORMAT_VERSION==13 and loaded.format_version==13 and value==_channel(True,.25,2,easing)


def test_preview_current_full_materialized_and_export_match(tmp_path):
    project,layer=_project(modulation=_channel(True,.2,2,"Ease In/Out"));full=render_effect_resource_layer(project,layer)
    for frame in range(8):assert np.array_equal(render_effect_resource_layer_current_frame(project,layer,frame),full[frame])
    generated=apply_effect_resource_layer(project,layer,full);paths=export_png_frames(project,tmp_path/"png")
    from PIL import Image
    for frame,path in enumerate(paths):
        assert np.asarray(Image.open(path)).shape==(24,32,4)
        assert np.array_equal(np.asarray(Image.open(path)),project.compose_frame(frame))
        assert np.array_equal(project.frames[frame].layer_pixels[generated.id],full[frame])


def test_scaled_particle_obeys_strict_output_clip():
    project,layer=_project(modulation=_channel(True,4,4));layer.particle_settings.origin_x=31;layer.particle_settings.origin_y=23
    frames=render_effect_resource_layer(project,layer)
    assert all(frame.shape==(24,32,4) for frame in frames) and any(np.any(frame[...,3]) for frame in frames)


def test_lifetime_scale_render_does_not_mutate_transform_parenting_or_tracks():
    project,parent=_project(modulation=_channel(True,.2,2,"Ease Out"));child=deepcopy(parent);child.id="child";child.name="child";child.generated_layer_id=None;child.parent_id=parent.id;child.parent_offset=(1,0,3,0,1,-2,0,0,1);child.advanced_transform_enabled=False
    child.layer_space_transform.rotation_z=1080;child.surface_transform.rotation_z=-450
    project.effect_resource_layers.append(child);project.repair_effect_hierarchy();before=deepcopy(child.to_dict())
    render_effect_resource_layer(project,child)
    assert child.to_dict()==before and child.parent_id==parent.id and child.parent_offset==(1,0,3,0,1,-2,0,0,1)
    assert child.layer_space_transform.rotation_z==1080 and child.surface_transform.rotation_z==-450 and not child.advanced_transform_enabled


def test_scale_lifetime_ui_refresh_toggle_and_disabled_state():
    project,layer=_project(modulation=_channel(False,.25,2,"Ease Out"));from app.ui.particle_properties_panel import ParticlePropertiesPanel
    panel=ParticlePropertiesPanel();changes=[];panel.draft_changed.connect(lambda *_:changes.append(1));panel.set_resource_layer(layer,project)
    assert not panel.scale_lifetime_enabled.isChecked() and not panel.scale_lifetime_start.isEnabled()
    assert panel.scale_lifetime_start.value()==.25 and panel.scale_lifetime_end.value()==2 and panel.scale_lifetime_easing.currentData()=="Ease Out" and changes==[]
    panel.scale_lifetime_enabled.setChecked(True);assert panel.scale_lifetime_start.isEnabled() and len(changes)==1
    panel.close()


def test_scale_lifetime_each_control_is_one_undo_noop_is_zero_and_primary_only(tmp_path):
    project,layer=_project();window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"scale.ini"),QSettings.Format.IniFormat)),project);window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False
    panel=window.particle_properties;panel.scale_lifetime_enabled.setChecked(True);panel.scale_lifetime_start.setValue(.2);panel.scale_lifetime_end.setValue(2);panel.scale_lifetime_easing.setCurrentIndex(panel.scale_lifetime_easing.findData("Ease Out"));APP.processEvents()
    assert window.application_undo_stack.count()==4 and layer.particle_settings.scale_over_lifetime==_channel(True,.2,2,"Ease Out") and layer.particle_settings.motion.tracks=={}
    panel.scale_lifetime_end.setValue(panel.scale_lifetime_end.value());assert window.application_undo_stack.count()==4
    for _ in range(4):window.application_undo_stack.undo()
    assert layer.particle_settings.scale_over_lifetime==LifetimeScalarModulation()
    for _ in range(4):window.application_undo_stack.redo()
    assert layer.particle_settings.scale_over_lifetime==_channel(True,.2,2,"Ease Out")
    _close(window)


def test_scale_lifetime_multi_selection_edits_primary_layer_only(tmp_path):
    project,first=_project();apply_effect_resource_layer(project,first);window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"multi.ini"),QSettings.Format.IniFormat)),project);window.select_resource_layer(first.id);second=window.duplicate_resource_layer(first.id)
    window.select_effect_layers_with_modifiers(first.id);window.select_effect_layers_with_modifiers(second.id,Qt.KeyboardModifier.ControlModifier);window.application_undo_stack.clear();window.application_undo_stack.setClean()
    assert window.primary_effect_layer_id==second.id
    window.particle_properties.scale_lifetime_enabled.setChecked(True);APP.processEvents()
    assert second.particle_settings.scale_over_lifetime.enabled and not first.particle_settings.scale_over_lifetime.enabled
    assert window.application_undo_stack.count()==1
    _close(window)


@pytest.mark.parametrize(("name","start","end","easing"),[
    ("Hit Spark",1.0,0.0,"Ease In"),("Explosion",.2,1.4,"Ease Out"),("Smoke",.5,1.8,"Ease Out"),
])
def test_representative_lifetime_scale_fixtures_progress(name,start,end,easing):
    project,layer=_project(modulation=_channel(True,start,end,easing));layer.name=name
    at_birth=_diagnostics(project,layer,0)[0];at_end=_diagnostics(project,layer,4)[0]
    assert at_birth.lifetime_scale==pytest.approx(start) and at_end.lifetime_scale==pytest.approx(end)
    assert at_birth.scale==pytest.approx(1.25*start) and at_end.scale==pytest.approx(1.25*end)
