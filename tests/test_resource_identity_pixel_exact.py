from __future__ import annotations

import numpy as np
import pytest

from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import EFFECT_RASTER_STATS,reset_effect_raster_stats
from app.services.resource_composition_render_service import composition_as_clip,render_composition_frame
from app.ui.resource_editor_v2.composition_canvas import alpha_bounds


def edge_pattern(width,height,margin=0):
    pixels=np.zeros((height,width,4),dtype=np.uint8);pixels[...,0]=17;pixels[...,1]=31;pixels[...,2]=47
    left,top=margin,margin;right,bottom=width-margin,height-margin
    if left<right and top<bottom:
        pixels[top, left:right]=[240,20,20,255];pixels[bottom-1,left:right]=[20,240,20,255]
        pixels[top:bottom,left]=[20,20,240,255];pixels[top:bottom,right-1]=[240,220,20,255]
        pixels[(top+bottom-1)//2,(left+right-1)//2]=[230,30,210,255]
    return pixels


def render_identity(pixels):
    height,width=pixels.shape[:2];project=Project.create_default(width=width,height=height,frame_count=1)
    asset=SourceAsset("fixture",pixels);composition=ResourceComposition("fixture",width,height,12,1,True)
    layer=CompositionLayer("fixture","source_asset",asset.id,0,0,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y)
    composition.layers.append(layer);project.source_assets.append(asset);project.resource_compositions.append(composition)
    return project,asset,composition,layer,render_composition_frame(project,composition,0)


@pytest.mark.parametrize("size",[1,2,3,27,28,29])
def test_identity_even_odd_and_single_pixel_sizes_are_exact(size):
    source=edge_pattern(size,size)
    _,_,_,_,rendered=render_identity(source)
    assert np.array_equal(rendered,source)


def test_28x28_identity_resource_matches_source_rgba_exactly():
    source=np.zeros((28,28,4),dtype=np.uint8);source[2:27,2:27]=[80,120,220,255];source[4,19]=[250,30,80,255];_,asset,_,_,rendered=render_identity(source)
    assert (asset.pivot_x,asset.pivot_y)==(14,14)
    assert np.array_equal(rendered,source)
    assert alpha_bounds(rendered)==(2,2,27,27)  # opaque pixel indexes are 2..26 inclusive


def test_identity_preserves_right_bottom_edges_and_transparent_rgb():
    source=edge_pattern(28,28);source[0,0]=[91,72,53,0];source[-1,-1]=[8,7,6,255]
    _,_,_,_,rendered=render_identity(source)
    assert np.array_equal(rendered,source)
    assert tuple(rendered[-1,-1])==(8,7,6,255) and tuple(rendered[0,0])==(91,72,53,0)


def test_alpha_bounds_are_half_open_outer_edge_geometry():
    pixels=np.zeros((28,28,4),dtype=np.uint8);pixels[2:27,2:27,3]=255
    assert alpha_bounds(pixels)==(2,2,27,27)


def test_identity_fast_path_skips_homography(monkeypatch):
    import app.services.effect_render_service as renderer
    monkeypatch.setattr(renderer,"_homography_from_unit_square",lambda *args:(_ for _ in ()).throw(AssertionError("identity used homography")))
    reset_effect_raster_stats();source=edge_pattern(28,28,2);_,_,_,_,rendered=render_identity(source)
    assert np.array_equal(rendered,source) and EFFECT_RASTER_STATS["identity_blits"]==1


def test_identity_composition_as_clip_matches_source():
    source=edge_pattern(28,28,2);project,_,composition,_,rendered=render_identity(source);clip=composition_as_clip(project,composition)
    assert np.array_equal(clip.frames[0],source) and np.array_equal(clip.frames[0],rendered)
