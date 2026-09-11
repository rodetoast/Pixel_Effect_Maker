"""Read-only v0.0.16 microbenchmark for the particle lifetime scale hot path."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.models.animation_clip import AnimationClipAsset
from app.models.particle_emitter import LifetimeScalarModulation, ParticleEmitter, ParticleEmitterSettings, ParticleInstance
from app.models.project import Project
from app.services.particle_render_service import render_particle_frame


def instances(count: int) -> tuple[ParticleInstance, ...]:
    return tuple(ParticleInstance(0,9,16,16,0,0,.75+(index%7)*.05,0,0,0,1,index,particle_id=index) for index in range(count))


def median_ms(callback, repeats=3):
    values=[]
    for _ in range(repeats):
        started=perf_counter();callback();values.append((perf_counter()-started)*1000)
    return round(statistics.median(values),3)


def main():
    project=Project.create_default(width=32,height=32,frame_count=1)
    clip=AnimationClipAsset("pixel",[np.full((1,1,4),255,dtype=np.uint8)],fps=12,playback_mode="hold")
    project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=1,particle_count_min=1,particle_count_max=1,lifetime_min=9,lifetime_max=9)
    emitter=ParticleEmitter("benchmark",settings)
    output={"conditions":"32x32, one 1x1 sprite, age 4/8, median of 3 actual frame renders","milliseconds":{}}
    modes=(
        ("off",LifetimeScalarModulation(False,.2,1.8,"Ease In/Out")),
        ("linear",LifetimeScalarModulation(True,.2,1.8,"Linear")),
        ("ease_in_out",LifetimeScalarModulation(True,.2,1.8,"Ease In/Out")),
    )
    for count in (100,500,1000,5000):
        resolved=instances(count);row={}
        for name,modulation in modes:
            settings.scale_over_lifetime=modulation
            row[name]=median_ms(lambda:render_particle_frame(project,emitter,4,clip=clip,instances=resolved))
        output["milliseconds"][str(count)]=row
    print(json.dumps(output,indent=2))


if __name__=="__main__":main()
