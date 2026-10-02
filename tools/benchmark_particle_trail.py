"""Synthetic history-free Trail evidence; no app build/user assets/manual GUI."""
from __future__ import annotations
import argparse
from copy import deepcopy
from pathlib import Path
import platform
import json
import subprocess
import sys
import types
from time import perf_counter
import statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
from app.models.particle_emitter import ParticleTrailSettings as Trail
from app.models.particle_emitter import ParticleMotionSettings
from app.services.particle_render_service import render_particle_frame,render_particle_frames
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.export_service import export_png_frames
from app.services.project_io import save_project,load_project
from tools.benchmark_lifetime_multi_point import fixture


def elapsed(fn):
    start=perf_counter();value=fn();return value,round((perf_counter()-start)*1000,3)


def median(fn):return round(statistics.median(elapsed(fn)[1] for _ in range(3)),3)


def counts(values):
    return dict(head_copies=sum(d.trail_delta==0 for d in values),visual_copies=len({d.generation_order for d in values}),
        trail_stamps=sum(d.trail_delta>0 for d in values))


def run(root):
    root.mkdir(parents=True,exist_ok=False)
    result=dict(version="0.0.24",format=21,platform=platform.platform(),python=platform.python_version(),
        native_gui_manual="수행하지 않음",conditions="96x96, 5x5 synthetic sprite, median 3 warm renders; samples do not copy source frame; renderer reference shares current dependencies",
        representatives={},benchmarks=[])
    legacy=types.ModuleType("pem_v23_trail_reference");sys.modules[legacy.__name__]=legacy
    source=subprocess.check_output(["git","show","9cf4a41:app/services/particle_render_service.py"],text=True,encoding="utf-8")
    exec(compile(source,"<v23 frozen renderer>","exec"),legacy.__dict__)
    tiles=[]
    for name,base in (("Projectile","Sword Slash"),("Magic Wisp Comet","Magic Wisp"),("Hit Spark","Hit Spark"),("Sword Slash Helper","Sword Slash"),("Cyclic Ember","Cyclic Fire")):
        project,layer=fixture(base);settings=layer.particle_settings
        settings.trail=Trail(True,12,2,.75)
        if name=="Projectile":
            settings.particle_count_min=settings.particle_count_max=1;settings.speed_min=settings.speed_max=2
            settings.direction_degrees=0;settings.direction_spread_degrees=0;settings.lifetime_min=settings.lifetime_max=12
            settings.opacity_over_lifetime.start=settings.opacity_over_lifetime.end=1
        if name=="Magic Wisp Comet":settings.motion=ParticleMotionSettings(mode="orbit",radius_start=8,radius_end=15,turns=1)
        if name=="Sword Slash Helper":settings.motion=ParticleMotionSettings(mode="orbit",radius_start=18,radius_end=18,turns=.5)
        if name=="Cyclic Ember":settings.lifetime_min=settings.lifetime_max=5;settings.emission_period_frames=6
        settings.validate();emitter=layer.as_particle_emitter();raw=render_particle_frames(project,emitter)
        target=root/name.replace(" ","_");target.mkdir();generated=apply_effect_resource_layer(project,layer)
        final=[project.compose_frame(t) for t in range(24)]
        values=[];render_particle_frame(project,emitter,0,diagnostic_collector=values)
        if name=="Projectile":assert np.any(raw[12][...,3]) and not np.any(raw[22][...,3])
        if name=="Cyclic Ember":
            assert any(d.copy_age>=d.lifetime for d in values)
            for t in range(6):assert np.array_equal(raw[t],render_particle_frame(project,emitter,t+6))
        for t in range(24):
            assert np.array_equal(raw[t],render_particle_frame(project,emitter,t))
            assert np.array_equal(raw[t],project.frames[t].layer_pixels[generated.id])
            assert np.array_equal(final[t],render_exact_playback_frame(project,t)[0])
        path=save_project(project,target/"fixture.peffect.json");loaded=load_project(path)
        pngs=export_png_frames(loaded,target/"frames")
        assert all(np.array_equal(f,np.asarray(Image.open(p))) for f,p in zip(final,pngs))
        result["representatives"][name]=dict(parity_reload_png_exact=True,dimensions=[96,96],gate=counts(values),
            tail_only_at_gate=any(d.copy_age>=d.lifetime for d in values),alpha_pixels=[int(np.count_nonzero(f[...,3])) for f in raw])
        tiles.append(np.concatenate([final[t] for t in (0,3,6,12,18,23)],axis=1))
    Image.fromarray(np.concatenate(tiles,axis=0)).save(root/"contact_sheet.png")
    project,layer=fixture("Hit Spark");base=layer.as_particle_emitter()
    for count in (100,500,1000):
        for label,trail in (("off",Trail(False)),("light",Trail(True,12,3)),("medium",Trail(True,12,2)),("dense",Trail(True,24,2)),("cyclic_full_stack",Trail(True,12,2))):
            emitter=deepcopy(base);s=emitter.settings;s.particle_count_min=s.particle_count_max=count;s.trail=trail
            if label=="cyclic_full_stack":
                s.emission_cycle_mode="cyclic_steady";s.emission_period_frames=24;s.lifetime_min=s.lifetime_max=16
                s.noise_enabled=True;s.noise_strength=2;s.blend_mode="additive"
            entry=dict(scenario=label,canonical_count=count,duration=trail.duration_frames,interval=trail.sample_interval_frames,
                period=s.emission_period_frames,cycle_mode=s.emission_cycle_mode,lifetime=s.lifetime_max,
                visual_bound=s.cyclic_active_copy_bound() if label=="cyclic_full_stack" else count,stamp_bound=s.trail_stamp_bound())
            try:s.validate()
            except ValueError as error:
                entry["explicit_rejection"]=str(error);result["benchmarks"].append(entry);continue
            values=[];first,cold=elapsed(lambda:render_particle_frame(project,emitter,12,diagnostic_collector=values))
            entry.update(counts(values));entry["cold_diagnostic_ms"]=cold
            entry["warm_ms"]=median(lambda:render_particle_frame(project,emitter,12))
            if label=="off":
                assert np.array_equal(first,legacy.render_particle_frame(project,emitter,12))
                entry["frozen_v23_warm_ms"]=median(lambda:legacy.render_particle_frame(project,emitter,12))
            if label=="cyclic_full_stack":
                large_values=[];large,large_ms=elapsed(lambda:render_particle_frame(project,emitter,100000,diagnostic_collector=large_values))
                assert np.array_equal(large,render_particle_frame(project,emitter,100000%s.emission_period_frames))
                entry["large_frame"]=100000;entry["large_diagnostic_ms"]=large_ms;entry["large_counts"]=counts(large_values)
            result["benchmarks"].append(entry)
    (root/"report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);run(parser.parse_args().output)
