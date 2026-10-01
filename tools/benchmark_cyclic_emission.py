"""Reproducible synthetic diagnostics, not native GUI QA or production presets.

New --output directory only; no user project/asset reads. Reports valid workloads
and explicit over-limit rejections; never truncates copies to make benchmarks pass.
"""
from __future__ import annotations
import argparse
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
from app.models.particle_emitter import LifetimeScalarModulation,LifetimeColorModulation
from app.services.particle_render_service import (build_particle_instances,render_particle_frame,
    render_particle_frames,invalidate_particle_render_caches)
from app.services.particle_cyclic_emission_service import iter_particle_cycle_copies
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.export_service import export_png_frames
from app.services.project_io import save_project,load_project
from tools.recheck_effect_capabilities import fixture,materialize


def timed(fn):
    start=perf_counter();value=fn()
    return value,round((perf_counter()-start)*1000,3)


def run(root):
    root.mkdir(parents=True,exist_ok=False)
    # Read-only actual checkpoint renderer, sharing unchanged dependency services.
    # No checkout, worktree, user asset, or source-file rewrite.
    legacy=types.ModuleType("pem_v21_renderer_reference");sys.modules[legacy.__name__]=legacy
    legacy_source=subprocess.check_output(["git","show","af9be4c948f3d3a09700478dc00dd2102196c2ab:app/services/particle_render_service.py"],cwd=Path(__file__).resolve().parents[1],text=True,encoding="utf-8")
    exec(compile(legacy_source,"<v0.0.21 checkpoint renderer>","exec"),legacy.__dict__)
    result=dict(platform=platform.platform(),python=platform.python_version(),
        conditions="96x96 RGBA, static white artwork; median of 3 warm renders; frame 100000 direct seek",
        native_gui_manual="수행하지 않음",representatives={},benchmarks=[])
    tiles=[]
    for name in ("Fire Ember","Area Dust","Rain Snow"):
        for period in (6,12,24):
            project=fixture(name);layer=project.effect_resource_layers[0];s=layer.particle_settings
            s.emission_cycle_mode="cyclic_steady";s.emission_period_frames=period
            s.emission_duration=min(s.emission_duration,period)
            s.lifetime_min=24;s.lifetime_max=36;s.start_frame=0
            if name=="Area Dust":s.drag_enabled=True;s.drag_strength=.03;s.scale_over_lifetime=LifetimeScalarModulation(True,.5,1.5)
            s.validate();emitter=layer.as_particle_emitter()
            full=render_particle_frames(project,emitter)
            slots=build_particle_instances(s,1)
            active0=list(iter_particle_cycle_copies(s,slots,0))
            assert any(copy.cycle_index<0 for copy in active0) and np.any(full[0][...,3])
            for t in (0,1,period-1,period,period+1,2*period-1):
                assert np.array_equal(render_particle_frame(project,emitter,t),render_particle_frame(project,emitter,t+period))
            assert np.array_equal(render_particle_frame(project,emitter,24 if 24%period==0 else period),full[0])
            for frame in (23,0,12,3):assert np.array_equal(full[frame],render_particle_frame(project,emitter,frame))
            apply_effect_resource_layer(project,layer)
            final=[project.compose_frame(i) for i in range(24)]
            for i in range(24):assert np.array_equal(final[i],render_exact_playback_frame(project,i)[0])
            target=root/(name.replace(" ","_")+f"_P{period}");target.mkdir()
            path=save_project(project,target/"fixture.peffect.json");restored=load_project(path)
            replay=materialize(restored)
            assert all(np.array_equal(a,b) for a,b in zip(final,replay,strict=True))
            pngs=export_png_frames(restored,target/"frames")
            assert all(np.array_equal(a,np.asarray(Image.open(p))) for a,p in zip(final,pngs,strict=True))
            result["representatives"][name+f" P{period}"]=dict(canonical_count=len(slots),period=period,
                lifetime_range=[24,36],active_at_gate=len(active0),upper_bound=s.cyclic_active_copy_bound(),
                gate_alpha_pixels=int(np.count_nonzero(full[0][...,3])),periodic_seek_reload_png_exact=True,
                pixel_sha256=hashlib.sha256(b"".join(frame.tobytes() for frame in final)).hexdigest())
            tiles.append(np.concatenate([final[i] for i in (0,1,5,6,12,23)],axis=1))
    Image.fromarray(np.concatenate(tiles,axis=0)).save(root/"contact_sheet.png")
    project=fixture("Hit Spark");emitter=project.effect_resource_layers[0].as_particle_emitter();base=emitter.settings
    for count,period,lifetime in ((100,1,1),(500,12,24),(1000,24,24),(100,12,96),
                                  (500,24,96),(1000,24,96),(1000,1,24)):
        for mode in ("one_shot","cyclic_steady"):
            s=replace(base,emission_cycle_mode=mode,emission_period_frames=period,
                particle_count_min=count,particle_count_max=count,lifetime_min=lifetime,lifetime_max=lifetime,
                gravity_enabled=True,gravity_strength=.015,drag_enabled=True,drag_strength=.03,
                noise_enabled=True,noise_strength=2,noise_frequency=.07,blend_mode="additive",
                scale_over_lifetime=LifetimeScalarModulation(True,.5,1.5),
                color_over_lifetime=LifetimeColorModulation(True,(255,255,100),(255,30,10)))
            entry=dict(mode=mode,canonical_count=count,period=period,lifetime=lifetime,
                cyclic_upper_bound=s.cyclic_active_copy_bound(),full_stack=True)
            try:s.validate()
            except ValueError as error:
                assert mode=="cyclic_steady" and s.cyclic_active_copy_bound()>4096
                entry["expected_rejection"]=str(error);result["benchmarks"].append(entry);continue
            emitter.settings=s;slots=build_particle_instances(s,1)
            frame=0 if mode=="cyclic_steady" else min(3,lifetime-1)
            entry["actual_active_copies"]=len(list(iter_particle_cycle_copies(s,slots,frame))) if mode=="cyclic_steady" else count
            invalidate_particle_render_caches();_,entry["cold_render_ms"]=timed(lambda:render_particle_frame(project,emitter,frame))
            entry["warm_render_median_ms"]=statistics.median(timed(lambda:render_particle_frame(project,emitter,frame))[1] for _ in range(3))
            if mode=="one_shot":
                assert legacy.build_particle_instances(s,1)==slots
                entry["v21_spawn_instances_exact"]=True
                assert np.array_equal(legacy.render_particle_frame(project,emitter,frame),render_particle_frame(project,emitter,frame))
                entry["v21_renderer_warm_median_ms"]=statistics.median(timed(lambda:legacy.render_particle_frame(project,emitter,frame))[1] for _ in range(3))
                # Alternate order to reduce warm-up/scheduler bias in the comparison.
                old_samples=[];new_samples=[]
                for repetition in range(5):
                    pair=((old_samples,legacy.render_particle_frame),(new_samples,render_particle_frame))
                    for samples,renderer in pair if repetition%2==0 else reversed(pair):
                        samples.append(timed(lambda:renderer(project,emitter,frame))[1])
                entry["v21_renderer_warm_median_ms"]=statistics.median(old_samples)
                entry["warm_render_median_ms"]=statistics.median(new_samples)
                entry["paired_one_shot_samples"]=5
                entry["v21_rgba_exact"]=True
            if mode=="cyclic_steady":
                entry["enumeration_at_0"]=len(list(iter_particle_cycle_copies(s,slots,0)))
                copies,entry["enumeration_at_100000_ms"]=timed(lambda:list(iter_particle_cycle_copies(s,slots,100000)))
                entry["enumeration_at_100000"]=len(copies)
                invalidate_particle_render_caches();large,entry["cold_direct_100000_ms"]=timed(lambda:render_particle_frame(project,emitter,100000))
                assert np.array_equal(large,render_particle_frame(project,emitter,100000%period))
            result["benchmarks"].append(entry)
    (root/"results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    run(p.parse_args().output)
