"""Synthetic v25 parity/throughput evidence; no build or native GUI QA."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
from copy import deepcopy
import json
import platform
import subprocess
import types
from time import perf_counter
import statistics
import numpy as np
from PIL import Image
from app.models.particle_emitter import ParticleSubEmitterEventSettings as Event,ParticleTrailSettings as Trail,ParticleMotionSettings
from app.services.particle_sub_emitter_service import render_layer_particles,contribution_bounds,iter_invocations,template_settings
from app.services import particle_render_service as r
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame,render_effect_resource_layer,apply_effect_resource_layer
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.project_io import save_project,load_project
from app.services.export_service import export_png_frames
from tools.benchmark_lifetime_multi_point import fixture


def make(kind="death",count=1,child_count=4,cyclic=False,full=False):
    project,parent=fixture("Hit Spark")
    settings=parent.particle_settings
    settings.particle_count_min=settings.particle_count_max=count
    settings.lifetime_min=settings.lifetime_max=8
    settings.emission_cycle_mode="cyclic_steady" if cyclic else "one_shot";settings.emission_period_frames=24
    settings.speed_min=settings.speed_max=1;settings.direction_degrees=0;settings.direction_spread_degrees=0
    settings.trail=Trail(full,8,2,.75)
    child=deepcopy(parent);child.id="child-template";child.name="Impact Template";child.generated_layer_id=None;child.visible=False
    child.particle_settings=deepcopy(settings);cs=child.particle_settings
    cs.particle_count_min=cs.particle_count_max=child_count;cs.start_frame=12;cs.origin_x=cs.origin_y=0
    cs.direction_spread_degrees=180;cs.speed_min=.5;cs.speed_max=1.5;cs.lifetime_min=cs.lifetime_max=6
    cs.trail=Trail(full,8,2,.75)
    if full:
        for s in (settings,cs):s.gravity_enabled=True;s.gravity_strength=.04;s.drag_enabled=True;s.drag_strength=.06;s.noise_enabled=True;s.noise_strength=1
        cs.blend_mode="additive"
    project.effect_resource_layers.append(child);project.repair_effect_hierarchy()
    for event_kind in ("birth","death"):
        if kind in (event_kind,"both"):setattr(settings,event_kind+"_sub_emitter",Event(True,child.id))
    return project,parent,child


def measured(fn):
    start=perf_counter();value=fn();return value,round((perf_counter()-start)*1000,3)


def diagnostic_counts(values):
    child=[v for v in values if isinstance(v.generation_order,tuple) and v.generation_order[0]==1]
    return dict(head_copies=sum(v.trail_delta==0 for v in values),visual_copies=len({v.generation_order for v in values}),
        trail_stamps=sum(v.trail_delta>0 for v in values),child_visual_copies=len({v.generation_order for v in child}),
        child_trail_stamps=sum(v.trail_delta>0 for v in child),relevant_invocations=len({v.generation_order[1:-1] for v in child}))


def run(root):
    root.mkdir(parents=True,exist_ok=False)
    result=dict(version="0.0.25",format=22,platform=platform.platform(),python=platform.python_version(),native_gui_manual="수행하지 않음",
        conditions="96x96 /5x5 synthetic sprite, 3 warm render median, diagnostics count projectable groups incl zero-alpha stamps; count safety is conservative, not realtime",representatives={},benchmarks=[])
    tiles=[]
    frozen=types.ModuleType("v24_sub_benchmark_reference");sys.modules[frozen.__name__]=frozen
    source=subprocess.check_output(["git","show","2470af2:app/services/particle_render_service.py"],text=True,encoding="utf-8")
    exec(compile(source,"<v24 reference>","exec"),frozen.__dict__)
    for name in ("Projectile Impact","Explosion Secondary Smoke","Firework","Birth Puff","Cyclic Death Splash Diagnostic"):
        kind="birth" if name=="Birth Puff" else "death"
        project,parent,child=make(kind,10 if name=="Explosion Secondary Smoke" else 1,6,name.startswith("Cyclic"),True)
        s=parent.particle_settings
        if name=="Explosion Secondary Smoke":s.lifetime_min=4;s.lifetime_max=12;s.direction_spread_degrees=180
        if name=="Firework":s.direction_degrees=-90;s.gravity_enabled=False;child.particle_settings.blend_mode="additive"
        if name=="Birth Puff":s.emission_mode="over_time";s.emission_duration=8;s.particle_count_min=s.particle_count_max=6;s.start_delay_min=0;s.start_delay_max=2
        raw=render_effect_resource_layer(project,parent);generated=apply_effect_resource_layer(project,parent);apply_effect_resource_layer(project,child)
        final=[project.compose_frame(t) for t in range(24)]
        target=root/name.replace(" ","_");target.mkdir()
        for t in range(24):
            assert np.array_equal(raw[t],render_effect_resource_layer_current_frame(project,parent,t))
            assert np.array_equal(raw[t],project.frames[t].layer_pixels[generated.id])
            assert np.array_equal(final[t],render_exact_playback_frame(project,t)[0])
        loaded=load_project(save_project(project,target/"fixture.peffect.json"));png=export_png_frames(loaded,target/"frames")
        assert all(np.array_equal(frame,np.asarray(Image.open(path))) for frame,path in zip(final,png))
        evidence=[]
        for t in (0,7,8,12,18,23):
            values=[];render_layer_particles(project,parent,t,diagnostics=values);evidence.append(dict(frame=t,**diagnostic_counts(values)))
        result["representatives"][name]=dict(parity_reload_png_exact=True,dimensions=[96,96],counts=evidence)
        tiles.append(np.concatenate([final[t] for t in (0,7,8,12,18,23)],axis=1))
    Image.fromarray(np.concatenate(tiles,axis=0)).save(root/"contact_sheet.png")
    for count in (100,500,1000):
        for label,kind,cyclic,full in (("off","none",False,False),("birth","birth",False,False),("death","death",False,False),("both","both",False,False),("cyclic","both",True,False),("full_stack","both",True,True)):
            project,parent,child=make(kind,count,4,cyclic,full);s=parent.particle_settings
            entry=dict(scenario=label,parent_count=count,child_count=4,period=24,parent_lifetime=8,child_lifetime=6,enabled_events=kind)
            try:
                visual,stamps,details=contribution_bounds(s,{i.id:i for i in project.effect_resource_layers},parent.id)
            except ValueError as error:entry["explicit_rejection"]=str(error);result["benchmarks"].append(entry);continue
            entry.update(total_visual_bound=visual,total_stamp_bound=stamps,event_bounds=details)
            frame=3 if label in ("birth","off") else 9
            values=[];_,milliseconds=measured(lambda:render_layer_particles(project,parent,frame,diagnostics=values))
            entry.update(diagnostic_counts(values));entry["diagnostic_ms"]=milliseconds
            entry["warm_ms"]=round(statistics.median(measured(lambda:render_layer_particles(project,parent,frame))[1] for _ in range(3)),3)
            if label=="off":
                assert np.array_equal(render_layer_particles(project,parent,frame),frozen.render_particle_frame(project,parent.as_particle_emitter(),frame))
                entry["frozen_v24_warm_ms"]=round(statistics.median(measured(lambda:frozen.render_particle_frame(project,parent.as_particle_emitter(),frame))[1] for _ in range(3)),3)
            if cyclic:
                large_values=[];large,ms=measured(lambda:render_layer_particles(project,parent,100000,diagnostics=large_values))
                assert np.array_equal(large,render_layer_particles(project,parent,100000%24))
                entry.update(large_frame=100000,large_diagnostic_ms=ms,large_counts=diagnostic_counts(large_values))
            result["benchmarks"].append(entry)
    (root/"report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output)
