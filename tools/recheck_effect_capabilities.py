"""Post-v21 audit fixtures, not production presets or a new feature.

Run with --output pointing to a NEW directory. Keeps evidence outside the repo.
Static white dot/arc artwork intentionally avoids baked lifetime animation.
Does not open user projects or the native GUI. Assertions fail the process.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication
from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import (ParticleEmitter, ParticleEmitterSettings,
    ParticleMotionSettings, LifetimeScalarModulation, LifetimeColorModulation)
from app.models.project import Project, FORMAT_VERSION
from app.services.effect_resource_layer_render_service import (
    apply_effect_resource_layer, invalidate_effect_resource_layer_base)
from app.services.particle_render_service import (
    build_particle_instances, render_particle_frame, render_particle_frames,
    invalidate_particle_render_caches)
from app.services.project_io import save_project, load_project
from app.services.export_service import export_png_frames
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.version import VERSION_LABEL

NAMES = ("Hit Spark", "Explosion", "Smoke Puff", "Fire Ember", "Magic Wisp",
         "Projectile", "Sword Slash", "Area Dust", "Ring Burst", "Rain Snow")


def add(project, name, **changes):
    values = dict(clip_asset_id=project.animation_clips[0].id, output_frame_count=24,
        origin_x=48, origin_y=48, particle_count_min=24, particle_count_max=24,
        speed_min=.6, speed_max=1.6, lifetime_min=12, lifetime_max=20,
        direction_spread_degrees=15, opacity_start=1, opacity_end=0, seed=21022,
        scale_over_lifetime=LifetimeScalarModulation(True, 1, .2, "Ease Out"),
        color_over_lifetime=LifetimeColorModulation(True, (255,230,120), (255,70,20)))
    values.update(changes)
    layer = EffectResourceLayer.from_particle_emitter(
        ParticleEmitter(name, ParticleEmitterSettings(**values)))
    project.effect_resource_layers.append(layer)
    return layer


def fixture(name):
    project = Project.create_default(width=96, height=96, frame_count=24)
    project.name = name
    dot = np.zeros((9,9,4), np.uint8)
    dot[3:6,3:6] = (255,255,255,255)
    if name == "Sword Slash":
        # Static arc is explicit source artwork, NOT a generated path/ribbon.
        yy,xx = np.mgrid[:9,:9]
        dot[:] = 0
        dot[(np.hypot(xx-4,yy-4)>2.5) & (np.hypot(xx-4,yy-4)<4.5) & (yy<5)] = 255
    project.animation_clips.append(AnimationClipAsset("static white artwork", [dot], fps=12, playback_mode="loop"))
    if name == "Hit Spark":
        add(project,name,direction_mode="radial_outward",blend_mode="additive",
            drag_enabled=True,drag_strength=.12,gravity_enabled=True,gravity_strength=.02)
    elif name == "Explosion":
        add(project,"flash",direction_mode="radial_outward",blend_mode="additive",
            speed_max=2.5,drag_enabled=True,drag_strength=.15)
        add(project,"scheduled smoke",start_frame=4,spawn_shape="box",box_width=12,
            box_height=8,speed_min=.1,speed_max=.5,noise_enabled=True,noise_strength=3,
            noise_frequency=.09,scale_over_lifetime=LifetimeScalarModulation(True,.5,2),
            color_over_lifetime=LifetimeColorModulation(True,(180,180,180),(50,50,50)))
    elif name in {"Smoke Puff","Fire Ember"}:
        add(project,name,spawn_shape="box",box_width=12,box_height=4,
            emission_mode="over_time" if name=="Fire Ember" else "burst",emission_duration=18,
            noise_enabled=True,noise_strength=3,noise_frequency=.08,
            drag_enabled=True,drag_strength=.03,gravity_enabled=True,gravity_strength=-.015,
            blend_mode="additive" if name=="Fire Ember" else "normal",
            scale_over_lifetime=LifetimeScalarModulation(True,.5,2 if name=="Smoke Puff" else .1))
    elif name == "Magic Wisp":
        add(project,name,particle_count_min=6,particle_count_max=6,blend_mode="additive",
            noise_enabled=True,noise_strength=2,noise_frequency=.1,
            motion=ParticleMotionSettings(mode="orbit",radius_start=20,radius_end=20,
                turns=1,phase_spread_degrees=360))
    elif name == "Projectile":
        add(project,name,particle_count_min=1,particle_count_max=1,origin_x=15,
            speed_min=2.5,speed_max=2.5,direction_degrees=0,direction_spread_degrees=0,
            lifetime_min=24,lifetime_max=24,blend_mode="additive")
        add(project,"scheduled impact (not death event)",start_frame=18,origin_x=60,
            direction_mode="radial_outward",lifetime_min=6,lifetime_max=6)
    elif name == "Sword Slash":
        add(project,name,particle_count_min=1,particle_count_max=1,speed_min=0,speed_max=0,
            scale_min=6,scale_max=6,angular_velocity_min=5,angular_velocity_max=5)
    elif name == "Area Dust":
        add(project,name,spawn_shape="box",box_width=80,box_height=70,
            emission_mode="over_time",emission_duration=24,speed_min=.1,speed_max=.3,
            noise_enabled=True,noise_strength=3,noise_frequency=.06)
    elif name == "Ring Burst":
        add(project,name,spawn_shape="circle",radius=12,direction_mode="radial_outward",
            direction_spread_degrees=0,blend_mode="additive",
            drag_enabled=True,drag_strength=.06)
    else:
        add(project,name,spawn_shape="line",origin_x=8,origin_y=10,line_end_x=88,line_end_y=10,
            direction_degrees=90,direction_spread_degrees=2,emission_mode="over_time",
            emission_duration=24,gravity_enabled=True,gravity_strength=.02,
            noise_enabled=True,noise_strength=1,noise_frequency=.05)
    project.repair_effect_hierarchy()
    return project


def materialize(project):
    invalidate_effect_resource_layer_base()
    invalidate_particle_render_caches()
    for layer in project.effect_resource_layers:
        apply_effect_resource_layer(project,layer)
    return [project.compose_frame(frame) for frame in range(24)]


def exact(left,right):
    assert len(left)==len(right)==24
    assert all(np.array_equal(a,b) for a,b in zip(left,right,strict=True))


def run(root):
    root.mkdir(parents=True,exist_ok=False)
    app = QApplication.instance() or QApplication([])
    result = dict(version=VERSION_LABEL,format_version=FORMAT_VERSION,
        conditions="96x96 RGBA, 24 frames; seed 21022; diagnostic artwork, not production art",
        native_gui_manual="수행하지 않음",fixtures={},spawn={},combinations={})
    tiles=[]
    for name in NAMES:
        project=fixture(name)
        settings_before=[layer.particle_settings.to_dict() for layer in project.effect_resource_layers]
        started=perf_counter()
        reference=materialize(project)
        elapsed=(perf_counter()-started)*1000
        assert sum(np.count_nonzero(frame[...,3]) for frame in reference)>0
        exact(reference,materialize(project))
        for layer in project.effect_resource_layers:
            emitter=layer.as_particle_emitter()
            full=render_particle_frames(project,emitter)
            for frame in (23,0,12,3,18,1,12,23,0):
                assert np.array_equal(full[frame],render_particle_frame(project,emitter,frame))
            panel=ParticlePropertiesPanel()
            panel.set_emitter(emitter,project)
            assert panel.settings().to_dict()==emitter.settings.to_dict()
            panel.close()
        assert settings_before==[layer.particle_settings.to_dict() for layer in project.effect_resource_layers]
        target=root/name.replace(" ","_")
        target.mkdir()
        restored=load_project(save_project(project,target/"fixture.peffect.json"))
        assert settings_before==[layer.particle_settings.to_dict() for layer in restored.effect_resource_layers]
        exact(reference,materialize(restored))
        paths=export_png_frames(restored,target/"frames")
        exact(reference,[np.asarray(Image.open(path)) for path in paths])
        alpha=[int(np.count_nonzero(frame[...,3])) for frame in reference]
        births=[[particle.birth_frame for particle in build_particle_instances(layer.particle_settings,1)] for layer in project.effect_resource_layers]
        result["fixtures"][name]=dict(layers=len(project.effect_resource_layers),frames=24,
            alpha_pixels_by_frame=alpha,birth_frames=births,cold_materialize_ms=round(elapsed,3),
            rerender_seek_inspector_reload_png_exact=True,
            loop_boundary_equal=bool(np.array_equal(reference[0],reference[-1])),
            sha256=hashlib.sha256(b"".join(frame.tobytes() for frame in reference)).hexdigest())
        tiles.append(np.concatenate([reference[i] for i in (0,4,8,12,16,20)],axis=1))
    base=fixture("Hit Spark").effect_resource_layers[0].particle_settings
    for shape in ("point","line","box","circle"):
        settings=replace(base,spawn_shape=shape,particle_count_min=256,particle_count_max=256,
            line_end_x=72,line_end_y=48,box_width=30,box_height=20,radius=16)
        points=build_particle_instances(settings,1)
        assert points==build_particle_instances(settings,1)
        xy=np.array([(p.start_x,p.start_y) for p in points])
        radii=np.linalg.norm(xy-[48,48],axis=1)
        if shape=="point": assert np.all(xy==[48,48])
        if shape=="line": assert np.all(xy[:,1]==48) and np.all((xy[:,0]>=48)&(xy[:,0]<=72))
        if shape=="box": assert np.all(np.abs(xy-[48,48])<=[15,10])
        if shape=="circle": assert np.allclose(radii,16,atol=1e-12)
        result["spawn"][shape]=dict(count=256,radius_min=float(radii.min()),radius_max=float(radii.max()),deterministic=True)
    project=fixture("Hit Spark")
    emitter=project.effect_resource_layers[0].as_particle_emitter()
    base=emitter.settings
    for name,g,d,n in (("gravity_drag",1,1,0),("drag_noise",0,1,1),
        ("gravity_noise",1,0,1),("gravity_drag_noise",1,1,1),
        ("scale_color_opacity",0,0,0),("additive_color",0,0,0),("full_stack",1,1,1)):
        emitter.settings=replace(base,gravity_enabled=bool(g),gravity_strength=.02,
            drag_enabled=bool(d),drag_strength=.1,noise_enabled=bool(n),noise_strength=3,
            blend_mode="additive" if name in {"additive_color","full_stack"} else "normal")
        instances=build_particle_instances(emitter.settings,1)
        full=render_particle_frames(project,emitter)
        assert instances==build_particle_instances(base,1) # natural motion does not consume spawn RNG
        assert any(np.any(frame[...,3]) for frame in full)
        for frame in (23,0,7,16,7):
            assert np.array_equal(full[frame],render_particle_frame(project,emitter,frame))
        result["combinations"][name]=dict(nonempty=True,seek_exact=True,spawn_rng_unchanged=True)
    Image.fromarray(np.concatenate(tiles,axis=0)).save(root/"contact_sheet.png")
    (root/"results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    app.processEvents()
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True,type=Path)
    run(parser.parse_args().output)
