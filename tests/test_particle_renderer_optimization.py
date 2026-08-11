import numpy as np

from app.services.effect_render_service import _source_over,EFFECT_RASTER_STATS,reset_effect_raster_stats


def reference_source_over(destination,source):
    source_f=source.astype(np.float64)/255.0;destination_f=destination.astype(np.float64)/255.0
    source_alpha=source_f[...,3:4];destination_alpha=destination_f[...,3:4]
    output_alpha=source_alpha+destination_alpha*(1.0-source_alpha);safe=np.where(output_alpha>0.0,output_alpha,1.0)
    rgb=(source_f[...,:3]*source_alpha+destination_f[...,:3]*destination_alpha*(1.0-source_alpha))/safe
    output=np.concatenate((rgb,output_alpha),axis=2);destination[:]=np.clip(np.rint(output*255.0),0,255).astype(np.uint8)


def test_particle_source_over_roi_matches_reference_for_500_cases():
    rng=np.random.default_rng(4401)
    for index in range(500):
        height=int(rng.integers(1,48));width=int(rng.integers(1,48));source=rng.integers(0,256,(height,width,4),dtype=np.uint8)
        if index%4==0:source[...,3]=0
        elif index%7==0:source[...,3]=255
        elif index%9==0:
            source[...,3]=0;source[height//3:max(height//3+1,2*height//3),width//3:max(width//3+1,2*width//3),3]=rng.integers(1,256)
        expected=np.zeros((height,width,4),dtype=np.uint8);actual=np.zeros_like(expected)
        for _ in range(index%4):
            prefix=rng.integers(0,256,(height,width,4),dtype=np.uint8)
            reference_source_over(expected,prefix);reference_source_over(actual,prefix)
        reference_source_over(expected,source);_source_over(actual,source)
        assert np.array_equal(actual,expected),index


def test_particle_composite_skips_transparent_and_uses_exact_opaque_roi():
    reset_effect_raster_stats();destination=np.zeros((600,600,4),dtype=np.uint8);source=np.zeros_like(destination)
    _source_over(destination,source);source[10:14,20:26]=[4,8,12,255];_source_over(destination,source)
    assert EFFECT_RASTER_STATS["transparent_skips"]==1 and EFFECT_RASTER_STATS["opaque_fast_paths"]==1
    assert EFFECT_RASTER_STATS["roi_pixels"]==4*6 and np.array_equal(destination[10:14,20:26],source[10:14,20:26])
