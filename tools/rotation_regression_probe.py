"""Write synthetic Resource/Effect rotation RGBA evidence, never user files."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings
from app.services.settings_service import ShortcutSettingsService
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.resource_composition_render_service import render_composition_frame
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame,render_effect_resource_layer
from app.services.export_service import export_png_frames
from app.ui.main_window import MainWindow
from tests.test_native_regression_repair import rotation_project
from tests.test_effect_layer_group_workflow import _close

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    p,c,sprite,_=rotation_project(12,12)
    p.frames=p.frames[:24];p.effect_resource_layers=[];p.repair_effect_hierarchy()
    c.frame_count=12;sprite.end_frame=11
    track=sprite.tracks["rotation"];track.keyframes.clear();track.set_keyframe(0,0);track.set_keyframe(11,330)
    win=MainWindow(ShortcutSettingsService(QSettings(str(out/"isolated.ini"),QSettings.Format.IniFormat)),p)
    try:
        layer=win.create_resource_layer_from_resource(c.id)
        old=[f.layer_pixels[layer.generated_layer_id].copy() for f in p.frames]
        win.set_fps(24);full=render_effect_resource_layer(p,layer);pngs=export_png_frames(p,out/"export")
        data=[]
        for resource_frame,effect_frame in ((0,0),(3,6),(6,12),(9,18),(0,24)):
            expected=render_composition_frame(p,c,resource_frame)
            current=render_effect_resource_layer_current_frame(p,layer,effect_frame)
            # End frame 23 is inclusive; 24 is the next loop boundary and
            # outside this Effect layer. Record boundary semantics separately.
            if effect_frame==24:
                data.append(dict(resource_frame=0,effect_frame=24,rotation=0,layer_active=False,transparent=not current[...,3].any()));continue
            variants={"resource":expected,"current":current,"full":full[effect_frame],"generated":p.frames[effect_frame].layer_pixels[layer.generated_layer_id],"playback":render_exact_playback_frame(p,effect_frame)[0],"png":np.asarray(Image.open(pngs[effect_frame]).convert("RGBA"))}
            for name,pixels in variants.items():Image.fromarray(pixels).resize((240,240),Image.Resampling.NEAREST).save(out/f"f{effect_frame:02}_{name}.png")
            Image.fromarray(old[effect_frame]).resize((240,240),Image.Resampling.NEAREST).save(out/f"f{effect_frame:02}_old_fps_generated.png")
            data.append(dict(resource_frame=resource_frame,effect_frame=effect_frame,rotation=sprite.value("rotation",resource_frame),rgba_equal={name:bool(np.array_equal(pixels,expected)) for name,pixels in variants.items()}))
        (out/"results.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
        print(json.dumps(data))
    finally:_close(win)

if __name__=="__main__":main()
