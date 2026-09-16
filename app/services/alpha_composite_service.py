"""Bit-exact float32 straight-alpha composition with conservative ROI fast paths."""

from __future__ import annotations

import numpy as np

from app.models.blend_mode import BLEND_ADDITIVE, BLEND_NORMAL, validate_blend_mode


ALPHA_COMPOSITE_STATS={
    "calls":0,"roi_composites":0,"transparent_skips":0,"opacity_skips":0,
    "opaque_candidates":0,"full_canvas_rois":0,"source_pixels":0,"roi_pixels":0,
    "additive_calls":0,
}


def reset_alpha_composite_stats() -> None:
    for key in ALPHA_COMPOSITE_STATS:ALPHA_COMPOSITE_STATS[key]=0


def alpha_bounds_rgba(source: np.ndarray) -> tuple[int,int,int,int] | None:
    """Return inclusive non-zero-alpha bounds without retaining mutable image state."""
    alpha=source[...,3];ys,xs=np.nonzero(alpha)
    if not len(xs):return None
    return int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())


def composite_rgba8_over_float32(output: np.ndarray,source: np.ndarray,opacity: float=1.0,blend_mode: str=BLEND_NORMAL) -> bool:
    """Composite one RGBA8 source into a same-sized float32 straight-alpha canvas.

    Arithmetic order matches the original Effect Playback renderer inside the
    selected ROI. Pixels outside non-zero source alpha are mathematically inert.
    """
    blend_mode=validate_blend_mode(blend_mode)
    ALPHA_COMPOSITE_STATS["calls"]+=1;opacity=max(0.0,min(1.0,float(opacity)))
    if opacity<=0.0:ALPHA_COMPOSITE_STATS["opacity_skips"]+=1;return False
    bounds=alpha_bounds_rgba(source)
    if bounds is None:ALPHA_COMPOSITE_STATS["transparent_skips"]+=1;return False
    left,top,right,bottom=bounds;src_u8=source[top:bottom+1,left:right+1];dst=output[top:bottom+1,left:right+1]
    full_pixels=int(source.shape[0]*source.shape[1]);roi_pixels=int(src_u8.shape[0]*src_u8.shape[1])
    ALPHA_COMPOSITE_STATS["source_pixels"]+=full_pixels;ALPHA_COMPOSITE_STATS["roi_pixels"]+=roi_pixels
    ALPHA_COMPOSITE_STATS["roi_composites"]+=1
    if roi_pixels==full_pixels:ALPHA_COMPOSITE_STATS["full_canvas_rois"]+=1
    src=src_u8.astype(np.float32)/255.0
    # A direct opaque assignment looks equivalent, but the historical
    # multiply/add/divide sequence can differ by float32 ULPs before the final
    # uint8 conversion. Keep the reference operation order for bit-exactness.
    if opacity==1.0 and bool(np.all(src_u8[...,3]==255)):ALPHA_COMPOSITE_STATS["opaque_candidates"]+=1
    src_alpha=src[...,3:4]*opacity;dst_alpha=dst[...,3:4]
    if blend_mode==BLEND_ADDITIVE:
        ALPHA_COMPOSITE_STATS["additive_calls"]+=1
        combined=np.clip(dst_alpha+src_alpha,0.0,1.0)
        premultiplied=np.clip(dst[...,:3]*dst_alpha+src[...,:3]*src_alpha,0.0,1.0)
        safe=np.where(combined==0,1.0,combined)
        dst[...,:3]=np.where(combined>0,premultiplied/safe,0.0);dst[...,3:4]=combined
        return True
    combined=src_alpha+dst_alpha*(1.0-src_alpha);safe=np.where(combined==0,1.0,combined)
    dst[...,:3]=(src[...,:3]*src_alpha+dst[...,:3]*dst_alpha*(1.0-src_alpha))/safe;dst[...,3:4]=combined
    return True


def composite_layers_rgba8(size: tuple[int,int],layers) -> np.ndarray:
    width,height=size;output=np.zeros((height,width,4),dtype=np.float32)
    for item in layers:
        source,opacity,*mode=item
        composite_rgba8_over_float32(output,source,opacity,mode[0] if mode else BLEND_NORMAL)
    return np.ascontiguousarray(np.clip(output*255.0,0,255).astype(np.uint8))


def composite_rgba8_additive_in_place(destination: np.ndarray, source: np.ndarray) -> bool:
    """Add straight-alpha RGBA8 source contributions into destination in place."""
    bounds=alpha_bounds_rgba(source)
    if bounds is None:return False
    left,top,right,bottom=bounds
    src=source[top:bottom+1,left:right+1].astype(np.float64)/255.0
    dst_u8=destination[top:bottom+1,left:right+1]
    dst=dst_u8.astype(np.float64)/255.0
    src_alpha=src[...,3:4];dst_alpha=dst[...,3:4]
    output_alpha=np.clip(dst_alpha+src_alpha,0.0,1.0)
    premultiplied=np.clip(dst[...,:3]*dst_alpha+src[...,:3]*src_alpha,0.0,1.0)
    safe=np.where(output_alpha>0.0,output_alpha,1.0)
    rgb=np.where(output_alpha>0.0,premultiplied/safe,0.0)
    dst_u8[:]=np.clip(np.rint(np.concatenate((rgb,output_alpha),axis=2)*255.0),0,255).astype(np.uint8)
    return True
