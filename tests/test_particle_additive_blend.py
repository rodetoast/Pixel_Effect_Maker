from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.animation_clip import AnimationClipAsset
from app.models.blend_mode import BLEND_ADDITIVE, BLEND_NORMAL
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import LifetimeColorModulation, LifetimeScalarModulation, ParticleEmitter, ParticleEmitterSettings
from app.models.project import FORMAT_VERSION, Project
from app.services.alpha_composite_service import composite_rgba8_additive_in_place, composite_rgba8_over_float32
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer, render_effect_resource_layer_current_frame
from app.services.effect_resource_layer_render_service import invalidate_effect_resource_layer_base
from app.services.export_service import export_png_frames
from app.services.particle_render_service import build_particle_instances
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


def _reference_additive(destination,source,opacity=1.0):
    dst=destination.astype(np.float64)/255.0;src=source.astype(np.float64)/255.0
    ad=dst[...,3:4];a_s=src[...,3:4]*opacity
    alpha=np.clip(ad+a_s,0,1);premult=np.clip(dst[...,:3]*ad+src[...,:3]*a_s,0,1)
    rgb=np.where(alpha>0,premult/np.where(alpha>0,alpha,1),0)
    return np.concatenate((rgb,alpha),axis=2)


def _project(mode=BLEND_NORMAL, *, count=2, color=None, scale=None):
    project=Project.create_default(width=8,height=8,fps=12,frame_count=4)
    pixels=np.array([[[160,80,40,255]]],dtype=np.uint8)
    clip=AnimationClipAsset("dot",[pixels],fps=12,pivot_x=0,pivot_y=0,playback_mode="hold");project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=4,particle_count_min=count,particle_count_max=count,
        lifetime_min=4,lifetime_max=4,origin_x=3,origin_y=3,speed_min=0,speed_max=0,scale_min=1,scale_max=1,
        opacity_start=.5,opacity_end=.5,seed=41,blend_mode=mode,
        color_over_lifetime=color or LifetimeColorModulation(),scale_over_lifetime=scale or LifetimeScalarModulation())
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter("Glow",settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def _close(window):
    window.resource_transform_render_timer.stop();window.resource_transform_finalize_timer.stop();window.particle_motion_render_timer.stop();window.particle_motion_finalize_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def test_additive_straight_alpha_equation_and_saturation_are_exact():
    destination=np.array([[[100,20,0,128],[250,250,250,255]]],dtype=np.uint8)
    source=np.array([[[200,100,50,64],[255,255,255,255]]],dtype=np.uint8)
    output=destination.astype(np.float32)/255.0
    composite_rgba8_over_float32(output,source,.5,BLEND_ADDITIVE)
    assert output==pytest.approx(_reference_additive(destination,source,.5),abs=2e-7)
    assert np.all(output[0,1]==1.0)


def test_additive_rgba8_transparent_destination_preserves_source_and_zero_alpha_rgb_is_inert():
    destination=np.zeros((1,2,4),dtype=np.uint8);source=np.array([[[23,71,199,129],[255,19,233,0]]],dtype=np.uint8)
    assert composite_rgba8_additive_in_place(destination,source)
    assert np.array_equal(destination[0,0],source[0,0])
    assert np.array_equal(destination[0,1],[0,0,0,0])
    output=destination.astype(np.float32)/255.0;before=output.copy()
    assert not composite_rgba8_over_float32(output,source,0,BLEND_ADDITIVE) and np.array_equal(output,before)


def test_same_emitter_particle_overlap_uses_selected_blend_mode():
    normal,n_layer=_project(BLEND_NORMAL);additive,a_layer=_project(BLEND_ADDITIVE)
    normal_pixel=render_effect_resource_layer(normal,n_layer)[0][3,3]
    additive_pixel=render_effect_resource_layer(additive,a_layer)[0][3,3]
    assert np.max(np.abs(normal_pixel[:3].astype(int)-additive_pixel[:3].astype(int)))<=1
    assert normal_pixel[3]==192 and additive_pixel[3]==255


def test_additive_effect_layer_combines_over_lower_normal_layer_with_layer_opacity():
    project,layer=_project(BLEND_ADDITIVE,count=1);lower=project.layers[0]
    project.frames[0].layer_pixels[lower.id][:]=[20,20,20,255]
    generated=apply_effect_resource_layer(project,layer);generated.opacity=.5
    source=project.frames[0].layer_pixels[generated.id]
    expected=np.clip(_reference_additive(project.frames[0].layer_pixels[lower.id],source,.5)*255,0,255).astype(np.uint8)
    assert np.array_equal(project.compose_frame(0),expected)
    assert tuple(project.compose_frame(0)[3,3])==(60,40,30,255)


def test_upper_normal_layer_source_over_can_cover_lower_additive_result():
    project,layer=_project(BLEND_ADDITIVE,count=1);generated=apply_effect_resource_layer(project,layer)
    foreground=project.add_layer("foreground");project.frames[0].layer_pixels[foreground.id][3,3]=[7,11,13,255]
    assert project.layers.index(foreground)>project.layers.index(generated)
    assert tuple(project.compose_frame(0)[3,3])==(7,11,13,255)


def test_two_additive_effect_layers_accumulate_in_project_order():
    project,first=_project(BLEND_ADDITIVE,count=1);apply_effect_resource_layer(project,first)
    second=deepcopy(first);second.id="second-additive";second.name="Second";second.generated_layer_id=None
    project.effect_resource_layers.append(second);project.repair_effect_hierarchy();apply_effect_resource_layer(project,second)
    sources=[]
    for logical in project.effect_resource_layers:
        generated=next(item for item in project.layers if item.id==logical.generated_layer_id)
        sources.append((project.frames[0].layer_pixels[generated.id],generated.opacity))
    expected=np.zeros((project.height,project.width,4),dtype=np.float32)
    for source,opacity in sources:composite_rgba8_over_float32(expected,source,opacity,BLEND_ADDITIVE)
    assert np.array_equal(project.compose_frame(0),np.clip(expected*255,0,255).astype(np.uint8))


def test_normal_mode_remains_byte_exact_to_historical_source_over_reference():
    rng=np.random.default_rng(20260911);sources=[rng.integers(0,256,(7,9,4),dtype=np.uint8) for _ in range(4)];opacities=(1.0,.37,0.0,.83)
    actual=np.zeros((7,9,4),dtype=np.float32);expected=np.zeros_like(actual)
    for source,opacity in zip(sources,opacities,strict=True):
        composite_rgba8_over_float32(actual,source,opacity,BLEND_NORMAL)
        src=source.astype(np.float32)/255.0;sa=src[...,3:4]*max(0,min(1,opacity));da=expected[...,3:4];combined=sa+da*(1-sa);safe=np.where(combined==0,1,combined)
        expected[...,:3]=(src[...,:3]*sa+expected[...,:3]*da*(1-sa))/safe;expected[...,3:4]=combined
    assert np.array_equal(np.clip(actual*255,0,255).astype(np.uint8),np.clip(expected*255,0,255).astype(np.uint8))


def test_additive_preserves_seed_motion_and_lifetime_channels():
    color=LifetimeColorModulation(True,(255,64,32),(32,64,255),"Ease Out");scale=LifetimeScalarModulation(True,.5,2,"Ease In")
    normal,n_layer=_project(BLEND_NORMAL,color=color,scale=scale);additive,a_layer=_project(BLEND_ADDITIVE,color=deepcopy(color),scale=deepcopy(scale))
    assert build_particle_instances(n_layer.particle_settings,1)==build_particle_instances(a_layer.particle_settings,1)
    left=n_layer.particle_settings.to_dict();right=a_layer.particle_settings.to_dict()
    for value in (left,right):value.pop("blend_mode");value.pop("clip_asset_id")
    assert left==right


def test_blend_mode_changes_invalidate_cached_particle_base_without_stale_pixels():
    project,layer=_project(BLEND_NORMAL);normal=render_effect_resource_layer(project,layer)[0].copy()
    layer.particle_settings.blend_mode=BLEND_ADDITIVE;additive=render_effect_resource_layer(project,layer)[0].copy()
    assert not np.array_equal(normal,additive)
    layer.particle_settings.blend_mode=BLEND_NORMAL;restored=render_effect_resource_layer(project,layer)[0]
    assert np.array_equal(restored,normal)
    invalidate_effect_resource_layer_base(layer.id)


def test_additive_current_full_baked_playback_and_png_are_identical(tmp_path):
    project,layer=_project(BLEND_ADDITIVE,color=LifetimeColorModulation(True,(255,255,0),(255,0,0),"Ease Out"),scale=LifetimeScalarModulation(True,.5,1.5,"Ease In/Out"));full=render_effect_resource_layer(project,layer)
    assert all(np.array_equal(render_effect_resource_layer_current_frame(project,layer,index),full[index]) for index in range(4))
    apply_effect_resource_layer(project,layer,full);paths=export_png_frames(project,tmp_path/"png")
    for index,path in enumerate(paths):
        exact,_=render_exact_playback_frame(project,index)
        assert np.array_equal(exact,project.compose_frame(index))
        assert np.array_equal(np.asarray(Image.open(path)),exact)


def test_format14_migrates_to_normal_and_current_format_round_trips_additive():
    project,layer=_project(BLEND_ADDITIVE);payload=project.to_dict();assert payload["format_version"]==FORMAT_VERSION==22
    loaded=Project.from_dict(payload);assert loaded.effect_resource_layers[0].particle_settings.blend_mode==BLEND_ADDITIVE
    payload["format_version"]=14;payload["effect_resource_layers"][0]["particle_settings"].pop("blend_mode")
    migrated=Project.from_dict(payload);assert migrated.format_version==22 and migrated.effect_resource_layers[0].particle_settings.blend_mode==BLEND_NORMAL


@pytest.mark.parametrize("value",["Additive","multiply","screen","",None,1])
def test_unknown_or_malformed_blend_modes_are_rejected(value):
    project,layer=_project();payload=layer.particle_settings.to_dict();payload["blend_mode"]=value
    with pytest.raises(ValueError):ParticleEmitterSettings.from_dict(payload)


def test_blend_mode_ui_refresh_noop_and_one_undo(tmp_path):
    project,layer=_project();apply_effect_resource_layer(project,layer)
    window=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"blend.ini"),QSettings.Format.IniFormat)),project);window.select_resource_layer(layer.id);window.application_undo_stack.clear();window.application_undo_stack.setClean();window.dirty=False;window._non_undo_dirty=False
    panel=window.particle_properties;changes=[];panel.draft_changed.connect(lambda *_:changes.append(1));before=deepcopy(layer.to_dict())
    for _ in range(3):panel.set_resource_layer(layer,project);panel.set_settings(layer.particle_settings)
    groups={title:group for title,group,_form,_records in panel._group_records}
    assert panel.blend_mode.currentData()==BLEND_NORMAL and changes==[] and layer.to_dict()==before and window.application_undo_stack.count()==0
    assert groups["Rendering"] is panel.rendering_group and panel.blend_mode not in [widget for _name,widget in next(records for title,_group,_form,records in panel._group_records if title=="Over Lifetime")]
    assert "premultiplied" in panel.blend_mode.toolTip().lower()
    panel.blend_mode.setCurrentIndex(panel.blend_mode.findData(BLEND_ADDITIVE));APP.processEvents()
    assert layer.particle_settings.blend_mode==BLEND_ADDITIVE and window.application_undo_stack.count()==1
    window.application_undo_stack.undo();assert layer.particle_settings.blend_mode==BLEND_NORMAL
    window.application_undo_stack.redo();assert layer.particle_settings.blend_mode==BLEND_ADDITIVE
    _close(window)


def test_single_placement_ignores_inactive_particle_blend_setting():
    project,layer=_project(BLEND_ADDITIVE);layer.set_placement_mode("single")
    assert all(item.particle_settings.blend_mode==BLEND_ADDITIVE for item in project.effect_resource_layers)
    from app.models.blend_mode import project_layer_blend_mode
    assert project_layer_blend_mode(project,layer.generated_layer_id)==BLEND_NORMAL
