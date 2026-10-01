"""Synthetic v23 evidence only: no build, user assets, or native GUI claims."""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import subprocess
import types
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
from app.models.animation_clip import AnimationClipAsset
from app.models.project import Project
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import (ParticleEmitterSettings, ParticleEmitter, LifetimeScalarModulation as Scalar,
    LifetimeColorModulation as Color, LifetimeScalarPoint as S, LifetimeColorPoint as C)
from app.services.lifetime_modulation_service import evaluate_lifetime_scalar_for_render, evaluate_lifetime_color_component
from app.services.emitter_service import ease
from app.services.particle_render_service import render_particle_frame, render_particle_frames, build_particle_instances
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.project_io import save_project,load_project
from app.services.export_service import export_png_frames


def multi(settings, name="Hit Spark"):
    smoke=name=="Smoke"
    settings.scale_over_lifetime=Scalar(True,points=(S(0,.2,"Ease Out"),S(.15,1.3),S(1,2 if smoke else 0)))
    settings.opacity_over_lifetime=Scalar(True,points=(S(0,0,"Ease Out"),S(.18,1),S(.77,.65,"Ease In"),S(1,0)))
    palette=((255,255,255),(32,255,255),(20,48,255)) if name=="Magic Wisp" else ((255,255,255),(255,208,32),(255,48,0))
    if smoke:palette=((180,180,180),(140,140,140),(100,100,100))
    settings.color_over_lifetime=Color(True,points=(C(0,palette[0]),C(.42,palette[1],"Ease In"),C(1,palette[2])))
    return settings


def fixture(name):
    project=Project.create_default(width=96,height=96,frame_count=24)
    clip=AnimationClipAsset("synthetic white sprite",[np.full((5,5,4),255,np.uint8)],fps=12,pivot_x=2,pivot_y=2)
    project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,particle_count_min=24,particle_count_max=24,lifetime_min=24,lifetime_max=24,
        origin_x=48,origin_y=48,direction_spread_degrees=180,speed_min=.5,speed_max=1.5,seed=23023,
        gravity_enabled=True,gravity_strength=.02,drag_enabled=True,drag_strength=.03,
        blend_mode="normal" if name=="Smoke" else "additive")
    if name=="Explosion":settings.direction_spread_degrees=360;settings.speed_max=2
    if name=="Smoke":settings.direction_spread_degrees=25;settings.gravity_strength=-.02
    if name=="Sword Slash":settings.direction_degrees=0;settings.direction_spread_degrees=10
    if name=="Magic Wisp":settings.noise_enabled=True;settings.noise_strength=2
    if name=="Cyclic Fire":settings.emission_cycle_mode="cyclic_steady";settings.emission_period_frames=6;settings.noise_enabled=True;settings.noise_strength=2
    multi(settings,name)
    layer=EffectResourceLayer.from_particle_emitter(ParticleEmitter(name,settings));project.effect_resource_layers.append(layer);project.repair_effect_hierarchy()
    return project,layer


def median_ms(fn,repeats=3):
    samples=[]
    for _ in range(repeats):
        start=perf_counter();fn();samples.append((perf_counter()-start)*1000)
    return round(statistics.median(samples),4)


def legacy_sample(settings,t):
    scalar=settings.scale_over_lifetime;color=settings.color_over_lifetime
    scale=scalar.start+(scalar.end-scalar.start)*ease(t,scalar.easing)
    opacity=settings.opacity_start+(settings.opacity_end-settings.opacity_start)*ease(t,settings.easing)
    amount=ease(t,color.easing)
    return scale+opacity+sum((color.start_rgb[c]+(color.end_rgb[c]-color.start_rgb[c])*amount)/255 for c in range(3))


def point_sample(settings,t):
    return evaluate_lifetime_scalar_for_render(settings.scale_over_lifetime,t)+evaluate_lifetime_scalar_for_render(settings.opacity_over_lifetime,t)+sum(evaluate_lifetime_color_component(settings.color_over_lifetime,t,c) for c in range(3))


def run(root):
    root.mkdir(parents=True,exist_ok=False)
    legacy_modules=[]
    for path,name in (("app/services/lifetime_modulation_service.py","pem_v22_lifetime"),("app/services/particle_render_service.py","pem_v22_renderer")):
        source=subprocess.check_output(["git","show",f"73af974:{path}"],cwd=Path(__file__).resolve().parents[1],text=True,encoding="utf-8")
        module=types.ModuleType(name);sys.modules[name]=module;exec(compile(source,path,"exec"),module.__dict__);legacy_modules.append(module)
    lifetime,legacy=legacy_modules
    for name in ("eased_lifetime_amount","evaluate_lifetime_scalar","evaluate_lifetime_color_component","normalized_lifetime_age"):
        setattr(legacy,name,getattr(lifetime,name))
    result={"version":"0.0.23","format":20,"platform":platform.platform(),"python":platform.python_version(),
        "native_gui_manual":"수행하지 않음","conditions":"96x96 synthetic 5x5 sprite; 3 warm median samples; independent curve sample workload includes count 5000; renderer safety limits remain unchanged", "representatives":{},"benchmarks":[]}
    tiles=[]
    for name in ("Hit Spark","Explosion","Smoke","Magic Wisp","Sword Slash","Cyclic Fire"):
        project,layer=fixture(name);emitter=layer.as_particle_emitter();raw=render_particle_frames(project,emitter)
        target=root/name.replace(" ","_");target.mkdir()
        generated=apply_effect_resource_layer(project,layer)
        final=[project.compose_frame(t) for t in range(24)]
        for t in range(24):
            assert np.array_equal(raw[t],render_particle_frame(project,emitter,t))
            assert np.array_equal(raw[t],project.frames[t].layer_pixels[generated.id])
            assert np.array_equal(final[t],render_exact_playback_frame(project,t)[0])
        path=save_project(project,target/"fixture.peffect.json");loaded=load_project(path)
        pngs=export_png_frames(loaded,target/"frames")
        assert all(np.array_equal(frame,np.asarray(Image.open(path))) for frame,path in zip(final,pngs))
        if name=="Cyclic Fire":
            for t in range(6):assert np.array_equal(raw[t],render_particle_frame(project,emitter,t+6))
        tiles.append(np.concatenate([final[t] for t in (0,3,6,12,18,23)],axis=1))
        result["representatives"][name]={"png_reload_playback_exact":True,"dimensions":[96,96],"cyclic_periodic":name=="Cyclic Fire",
            "alpha_pixels":[int(np.count_nonzero(f[...,3])) for f in raw],"rgba_sha256":hashlib.sha256(b"".join(f.tobytes() for f in final)).hexdigest()}
    Image.fromarray(np.concatenate(tiles,axis=0)).save(root/"contact_sheet.png")
    project,layer=fixture("Hit Spark");baseline=layer.particle_settings
    # All channels enabled, original two-point lerp; identical source and RNG.
    baseline.scale_over_lifetime=Scalar(True,.2,1.3,"Ease Out");baseline.opacity_over_lifetime=Scalar(True,.8,.1,"Ease In")
    baseline.color_over_lifetime=Color(True,(255,255,255),(255,48,0),"Ease In/Out")
    for count in (100,500,1000,5000):
        for scenario in ("legacy_2_point","scale_3_point","opacity_4_point","color_3_point","all_curves","cyclic_full_stack"):
            settings=deepcopy(baseline);candidate=multi(deepcopy(settings))
            if scenario in ("scale_3_point","all_curves","cyclic_full_stack"):settings.scale_over_lifetime=candidate.scale_over_lifetime
            if scenario in ("opacity_4_point","all_curves","cyclic_full_stack"):settings.opacity_over_lifetime=candidate.opacity_over_lifetime
            if scenario in ("color_3_point","all_curves","cyclic_full_stack"):settings.color_over_lifetime=candidate.color_over_lifetime
            if scenario=="cyclic_full_stack":
                settings.emission_cycle_mode="cyclic_steady";settings.emission_period_frames=24;settings.lifetime_min=settings.lifetime_max=36
                settings.noise_enabled=True;settings.noise_strength=2;settings.blend_mode="additive"
            settings.particle_count_min=settings.particle_count_max=count
            def sample():
                total=0
                for i in range(count):total+=point_sample(settings,(i%24)/23)
                return total
            entry={"requested_count":count,"scenario":scenario,"curve_samples_ms":median_ms(sample)}
            if scenario=="legacy_2_point":
                entry["v22_equivalent_evaluator_ms"]=median_ms(lambda:sum(legacy_sample(settings,(i%24)/23) for i in range(count)))
            try:settings.validate()
            except ValueError as error:
                entry["render_rejected_safety"]=str(error);result["benchmarks"].append(entry);continue
            frame=5 if scenario=="cyclic_full_stack" else 12
            entry["frame"]=frame
            emitter=ParticleEmitter("benchmark",settings);render_particle_frame(project,emitter,frame)
            entry["render_warm_ms"]=median_ms(lambda:render_particle_frame(project,emitter,frame))
            if scenario=="legacy_2_point":
                old=legacy.render_particle_frame(project,emitter,12)
                assert np.array_equal(old,render_particle_frame(project,emitter,12))
                entry["v22_render_warm_ms"]=median_ms(lambda:legacy.render_particle_frame(project,emitter,12))
                entry["legacy_render_ratio"]=round(entry["render_warm_ms"]/entry["v22_render_warm_ms"],4)
            slots=build_particle_instances(settings,1)
            entry["canonical_count"]=len(slots)
            entry["active_count"]=len(list(iter_particle_cycle_copies(settings,slots,frame))) if scenario=="cyclic_full_stack" else len(slots)
            result["benchmarks"].append(entry)
    (root/"report.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output)
