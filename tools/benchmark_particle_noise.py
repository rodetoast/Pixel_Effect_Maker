"""Read-only v0.0.21 smooth value-noise particle hot-path benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.models.animation_clip import AnimationClipAsset
from app.models.blend_mode import BLEND_ADDITIVE,BLEND_NORMAL
from app.models.particle_emitter import LifetimeColorModulation,LifetimeScalarModulation,ParticleEmitter,ParticleEmitterSettings,ParticleInstance
from app.models.project import Project
from app.services.particle_render_service import render_particle_frame


REPEATS=3


def instances(count: int) -> tuple[ParticleInstance,...]:
    return tuple(ParticleInstance(0,9,16+(index%5),16+((index//5)%5),0,0,1,0,0,0,1,index,particle_id=index) for index in range(count))


def median_ms(callback) -> float:
    values=[]
    for _ in range(REPEATS):
        started=perf_counter();callback();values.append((perf_counter()-started)*1000)
    return round(statistics.median(values),3)


def main() -> None:
    project=Project.create_default(width=32,height=32,frame_count=1)
    clip=AnimationClipAsset("dot",[np.array([[[240,180,60,160]]],dtype=np.uint8)],fps=12,playback_mode="hold",pivot_x=0,pivot_y=0)
    project.animation_clips.append(clip)
    settings=ParticleEmitterSettings(clip.id,output_frame_count=1,particle_count_min=1,particle_count_max=1,lifetime_min=9,lifetime_max=9,opacity_start=.75,opacity_end=.75)
    emitter=ParticleEmitter("noise benchmark",settings)
    scale=LifetimeScalarModulation(True,.35,1.65,"Ease In/Out")
    color=LifetimeColorModulation(True,(255,220,64),(64,96,255),"Ease In/Out")
    scenarios=(
        ("off",False,False,False,BLEND_NORMAL,LifetimeScalarModulation(),LifetimeColorModulation()),
        ("noise",False,False,True,BLEND_NORMAL,LifetimeScalarModulation(),LifetimeColorModulation()),
        ("gravity_drag_noise",True,True,True,BLEND_NORMAL,LifetimeScalarModulation(),LifetimeColorModulation()),
        ("gravity_drag_noise_scale_color_additive",True,True,True,BLEND_ADDITIVE,scale,color),
    )
    result={"conditions":f"32x32, semi-transparent 1x1 sprite, age 4/8, median of {REPEATS} complete particle frame renders","milliseconds":{},"ratios_vs_off":{}}
    for count in (100,500,1000,5000):
        resolved=instances(count);row={}
        for name,gravity,drag,noise,blend,lifetime_scale,lifetime_color in scenarios:
            settings.gravity_enabled=gravity;settings.gravity_strength=.125
            settings.drag_enabled=drag;settings.drag_strength=.125
            settings.noise_enabled=noise;settings.noise_strength=3.125;settings.noise_frequency=.1
            settings.blend_mode=blend;settings.scale_over_lifetime=lifetime_scale;settings.color_over_lifetime=lifetime_color
            row[name]=median_ms(lambda:render_particle_frame(project,emitter,4,clip=clip,instances=resolved))
        result["milliseconds"][str(count)]=row
        result["ratios_vs_off"][str(count)]={name:round(value/row["off"],3) for name,value in row.items()}
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
