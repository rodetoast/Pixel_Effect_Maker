from copy import deepcopy
from dataclasses import replace
import importlib.util
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

from app.models.particle_emitter import (LifetimeScalarPoint as S, LifetimeColorPoint as C,
    LifetimeScalarModulation, LifetimeColorModulation, ParticleMotionSettings)
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.resource_composition import EASINGS
from app.services.lifetime_modulation_service import (evaluate_lifetime_scalar,
    evaluate_lifetime_color_component, normalized_lifetime_age)
from app.services.emitter_service import ease
from app.services.particle_render_service import render_particle_frame, render_particle_frames, particle_spawn_states
from app.services.effect_resource_layer_render_service import render_effect_resource_layer, render_effect_resource_layer_current_frame, apply_effect_resource_layer
from app.services.effect_playback_service import playback_relevant_revision
from app.services.export_service import export_png_frames
from tests.test_particle_cyclic_emission import setup


def curves(settings):
    settings.scale_over_lifetime = LifetimeScalarModulation(True, points=(S(0,.2,"Ease Out"), S(.15,1.3,"Ease In"), S(1,0)))
    settings.opacity_over_lifetime = LifetimeScalarModulation(True, points=(S(0,0,"Ease Out"), S(.18,1), S(.77,.65,"Ease In"), S(1,0)))
    settings.color_over_lifetime = LifetimeColorModulation(True, points=(C(0,(255,255,255)), C(.42,(255,208,32),"Ease In"), C(1,(255,48,0))))
    return settings


@pytest.mark.parametrize("easing", EASINGS)
@pytest.mark.parametrize("time", [-1,0,.1,.37,.5,.99,1,2])
def test_scalar_and_rgb_two_point_exact_legacy(easing,time):
    amount = ease(max(0,min(1,time)), easing)
    scalar = LifetimeScalarModulation(True,.2,1.4,easing)
    color = LifetimeColorModulation(True,(241,13,73),(17,199,226),easing)
    assert evaluate_lifetime_scalar(scalar,time) == .2+(1.4-.2)*amount
    for channel in range(3):
        start,end=color.start_rgb[channel],color.end_rgb[channel]
        assert evaluate_lifetime_color_component(color,time,channel)==(start+(end-start)*amount)/255


def test_peak_hold_independent_segment_easing_and_exact_knots():
    curve=LifetimeScalarModulation(True,points=(S(0,0,"Ease Out"),S(.25,1,"Linear"),S(.75,1,"Ease In"),S(1,0)))
    for time,value in [(0,0),(.125,.75),(.25,1),(.5,1),(.75,1),(.875,.75),(1,0)]:
        assert evaluate_lifetime_scalar(curve,time)==value
    color=LifetimeColorModulation(True,points=(C(0,(255,255,255)),C(.37,(241,162,3)),C(1,(153,34,204))))
    assert tuple(evaluate_lifetime_color_component(color,.37,c)*255 for c in range(3))==(241,162,3)
    assert normalized_lifetime_age(0,1)==1 and normalized_lifetime_age(4,5)==1
    curve.enabled=False;assert evaluate_lifetime_scalar(curve,.25)==1
    color.enabled=False;assert evaluate_lifetime_color_component(color,.37,0)==1


@pytest.fixture(scope="module")
def v22_renderer():
    # Read-only frozen checkpoint; also install its original lifetime helpers.
    modules=[]
    for filename,name in [("app/services/lifetime_modulation_service.py","app.services._v22_lifetime"),("app/services/particle_render_service.py","app.services._v22_renderer")]:
        source=subprocess.run(["git","show",f"73af974:{filename}"],check=True,capture_output=True,text=True).stdout
        module=importlib.util.module_from_spec(importlib.util.spec_from_loader(name,loader=None));sys.modules[name]=module
        exec(compile(source,filename,"exec"),module.__dict__);modules.append(module)
    lifetime,renderer=modules
    for name in ("eased_lifetime_amount","evaluate_lifetime_scalar","evaluate_lifetime_color_component","normalized_lifetime_age"):
        setattr(renderer,name,getattr(lifetime,name))
    yield renderer
    for module in modules:sys.modules.pop(module.__name__,None)


@pytest.mark.parametrize("easing",EASINGS)
@pytest.mark.parametrize("cyclic",[False,True])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_v22_pixels_exact_all_easings_alpha_integrity(v22_renderer,easing,cyclic,blend):
    project,emitter=setup(emission_cycle_mode="cyclic_steady" if cyclic else "one_shot",blend_mode=blend,
        easing=easing,gravity_enabled=True,gravity_strength=.02,drag_enabled=True,drag_strength=.1,
        noise_enabled=True,noise_strength=2,noise_frequency=.12,
        scale_over_lifetime=LifetimeScalarModulation(True,.2,1.4,easing),
        color_over_lifetime=LifetimeColorModulation(True,(241,13,73),(17,199,226),easing))
    for frame in (0,1,5,7,15,23):
        assert np.array_equal(v22_renderer.render_particle_frame(project,emitter,frame),render_particle_frame(project,emitter,frame))


@pytest.mark.parametrize("mode",["linear","orbit","helix"])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_cyclic_prewarm_actual_age_full_stack_seek_and_rgb_alpha_isolation(mode,blend):
    project,emitter=setup(blend_mode=blend,gravity_enabled=True,gravity_strength=.02,drag_enabled=True,drag_strength=.1,
        noise_enabled=True,noise_strength=2,noise_frequency=.12,motion=ParticleMotionSettings(mode=mode,radius_start=3,radius_end=6,turns=1,axis_end=4))
    curves(emitter.settings)
    before=deepcopy(emitter.settings);diagnostics=[]
    frame=render_particle_frame(project,emitter,0,diagnostic_collector=diagnostics)
    assert diagnostics and any(d.cycle_index<0 and d.age>0 for d in diagnostics)
    for d in diagnostics:
        t=normalized_lifetime_age(d.age,d.lifetime)
        assert d.lifetime_scale==evaluate_lifetime_scalar(emitter.settings.scale_over_lifetime,t)
        assert d.opacity==evaluate_lifetime_scalar(emitter.settings.opacity_over_lifetime,t)
        assert d.lifetime_tint_g==evaluate_lifetime_color_component(emitter.settings.color_over_lifetime,t,1)
    for t in (0,1,5,6,23,100000):
        assert np.array_equal(render_particle_frame(project,emitter,t),render_particle_frame(project,emitter,t%6))
    assert emitter.settings==before
    canonical=particle_spawn_states(emitter.settings,4)
    revision=playback_relevant_revision(project)
    emitter.settings.color_over_lifetime.points=(C(0,(10,20,30)),C(.5,(30,40,50)),C(1,(80,90,100)))
    other=render_particle_frame(project,emitter,0)
    assert np.array_equal(frame[...,3],other[...,3])
    assert particle_spawn_states(emitter.settings,4) is canonical


@pytest.mark.parametrize("cyclic",[False,True])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_current_full_generated_png_parity_and_cache_invalidation(tmp_path,cyclic,blend):
    project,emitter=setup(emission_cycle_mode="cyclic_steady" if cyclic else "one_shot",blend_mode=blend)
    curves(emitter.settings)
    layer=EffectResourceLayer.from_particle_emitter(emitter);project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    frames=render_effect_resource_layer(project,layer);generated=apply_effect_resource_layer(project,layer)
    for t in (0,1,5,12,23):
        assert np.array_equal(frames[t],render_effect_resource_layer_current_frame(project,layer,t))
        assert np.array_equal(frames[t],project.frames[t].layer_pixels[generated.id])
    paths=export_png_frames(project,tmp_path/"png")
    for t in (0,1,5,12,23):
        assert np.array_equal(np.array(Image.open(paths[t]).convert("RGBA")),project.compose_frame(t))
    before=playback_relevant_revision(project);canonical=particle_spawn_states(layer.particle_settings,4)
    layer.particle_settings.opacity_over_lifetime.points=(S(0,1),S(.5,1),S(1,1))
    assert playback_relevant_revision(project)!=before
    assert particle_spawn_states(layer.particle_settings,4) is canonical
    assert not np.array_equal(frames[0],render_effect_resource_layer_current_frame(project,layer,0))


@pytest.mark.parametrize("advanced",[False,True])
@pytest.mark.parametrize("blend",["normal","additive"])
def test_multi_curves_parent_offset_system_surface_2_5d_strict_clip_ratio(advanced,blend):
    project,emitter=setup(blend_mode=blend);curves(emitter.settings)
    layer=EffectResourceLayer.from_particle_emitter(emitter);layer.advanced_transform_enabled=advanced
    layer.layer_space_transform.scale_x=1.5;layer.layer_space_transform.scale_y=.75
    layer.layer_space_transform.rotation_x=25;layer.layer_space_transform.rotation_y=-15;layer.layer_space_transform.rotation_z=720
    layer.surface_transform.rotation_z=12
    parent=deepcopy(layer);parent.id="parent";parent.visible=False;parent.generated_layer_id=None
    parent.layer_space_transform.position_x=2;parent.layer_space_transform.rotation_x=0;parent.layer_space_transform.rotation_y=0
    project.effect_resource_layers.extend((parent,layer));layer.parent_id=parent.id;layer.parent_offset=(1,0,3,0,1,-2,0,0,1)
    project.repair_effect_hierarchy();before=deepcopy(layer.to_dict())
    full=render_effect_resource_layer(project,layer)
    for t in (0,1,5,12,23):
        assert full[t].shape==(48,48,4)
        assert np.array_equal(full[t],render_effect_resource_layer_current_frame(project,layer,t))
    assert layer.to_dict()==before
    # Uniform lifetime factor cannot overwrite the base non-uniform ratio.
    from app.models.effect_resource_layer import EffectLayerTransform3D
    from app.services import particle_render_service as renderer
    calls=[];original=renderer.render_transformed_source
    def capture(*args,**kwargs):calls.append(kwargs);return original(*args,**kwargs)
    transform=EffectLayerTransform3D(scale_x=2,scale_y=1)
    with patch.object(renderer,"render_transformed_source",side_effect=capture):
        render_particle_frame(project,emitter,5,layer_space_transform=transform)
    assert calls and all(call["scale_x"]==2*call["scale_y"] for call in calls)
