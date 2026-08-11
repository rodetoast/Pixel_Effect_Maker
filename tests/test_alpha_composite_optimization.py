import numpy as np

from app.services.alpha_composite_service import (
    ALPHA_COMPOSITE_STATS,
    composite_rgba8_over_float32,
    reset_alpha_composite_stats,
)


def reference_composite(output,source,opacity):
    src=source.astype(np.float32)/255.0
    src_alpha=src[...,3:4]*max(0.0,min(1.0,float(opacity)));dst_alpha=output[...,3:4]
    combined=src_alpha+dst_alpha*(1.0-src_alpha);safe=np.where(combined==0,1.0,combined)
    output[...,:3]=(src[...,:3]*src_alpha+output[...,:3]*dst_alpha*(1.0-src_alpha))/safe
    output[...,3:4]=combined


def test_optimized_composite_matches_reference_for_500_random_cases():
    rng=np.random.default_rng(20260811)
    for index in range(500):
        height=int(rng.integers(1,65));width=int(rng.integers(1,65))
        source=rng.integers(0,256,(height,width,4),dtype=np.uint8)
        if index%5==0:source[...,3]=0
        elif index%7==0:source[...,3]=255
        elif index%11==0:
            source[...,3]=0;source[height//3:max(height//3+1,2*height//3),width//3:max(width//3+1,2*width//3),3]=rng.integers(1,255)
        opacity=(0.0,1.0,1/255,254/255,.37)[index%5]
        expected=np.zeros((height,width,4),dtype=np.float32);actual=np.zeros_like(expected)
        for _ in range(index%4):
            prefix=rng.integers(0,256,(height,width,4),dtype=np.uint8);prefix_opacity=float(rng.random())
            reference_composite(expected,prefix,prefix_opacity);reference_composite(actual,prefix,prefix_opacity)
        reference_composite(expected,source,opacity);composite_rgba8_over_float32(actual,source,opacity)
        expected_rgba=np.clip(expected*255.0,0,255).astype(np.uint8)
        actual_rgba=np.clip(actual*255.0,0,255).astype(np.uint8)
        assert np.array_equal(actual_rgba,expected_rgba),index


def test_transparent_opaque_and_roi_fast_paths_are_counted_and_exact():
    reset_alpha_composite_stats();output=np.zeros((600,600,4),dtype=np.float32)
    transparent=np.zeros((600,600,4),dtype=np.uint8)
    assert not composite_rgba8_over_float32(output,transparent,1.0)
    opaque=np.zeros_like(transparent);opaque[20:30,40:55]=[10,20,30,255]
    assert composite_rgba8_over_float32(output,opaque,1.0)
    assert ALPHA_COMPOSITE_STATS["transparent_skips"]==1
    assert ALPHA_COMPOSITE_STATS["opaque_candidates"]==1
    assert ALPHA_COMPOSITE_STATS["roi_pixels"]==10*15
    assert ALPHA_COMPOSITE_STATS["source_pixels"]==600*600
    assert np.array_equal(output[20:30,40:55],opaque[20:30,40:55].astype(np.float32)/255.0)
