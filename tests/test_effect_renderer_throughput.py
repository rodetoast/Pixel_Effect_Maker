import numpy as np

from app.models.project import Project
from app.services.alpha_composite_service import ALPHA_COMPOSITE_STATS,reset_alpha_composite_stats
from app.services.effect_playback_service import render_exact_playback_frame


def test_five_sparse_layers_composite_only_alpha_rois():
    project=Project.create_default(width=600,height=600,fps=12,frame_count=1)
    while len(project.layers)<5:project.add_layer(f"Layer {len(project.layers)+1}")
    for index,layer in enumerate(project.layers):
        pixels=project.frames[0].layer_pixels[layer.id];pixels[20+index*15:70+index*15,30:90]=[20+index*30,80,220,180]
    reset_alpha_composite_stats();rgba,_=render_exact_playback_frame(project,0)
    assert rgba.shape==(600,600,4) and rgba.dtype==np.uint8
    assert ALPHA_COMPOSITE_STATS["calls"]==5 and ALPHA_COMPOSITE_STATS["roi_composites"]==5
    assert ALPHA_COMPOSITE_STATS["full_canvas_rois"]==0
    assert ALPHA_COMPOSITE_STATS["roi_pixels"]==5*50*60
    assert ALPHA_COMPOSITE_STATS["source_pixels"]==5*600*600


def test_off_canvas_or_empty_effect_layer_is_a_transparent_skip():
    project=Project.create_default(width=600,height=600,fps=12,frame_count=1)
    reset_alpha_composite_stats();rgba,_=render_exact_playback_frame(project,0)
    assert not np.any(rgba) and ALPHA_COMPOSITE_STATS["transparent_skips"]==1
