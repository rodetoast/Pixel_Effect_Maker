"""Deterministic nearest-neighbor projection for flat Resource Layer output."""

from __future__ import annotations

import math
import numpy as np

from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.frame import empty_pixels
from app.services.effect_render_service import _homography_from_unit_square, _source_over

_NEAR_RATIO = 0.05


def focal_length(canvas_width: int, canvas_height: int, strength: float) -> float:
    """Map 0..1 strength to one shared, bounded camera focal length."""
    strength = max(1e-6, min(1.0, float(strength)))
    return max(1.0, float(max(canvas_width, canvas_height))) * (2.0 / strength)


def _rotation_matrix(transform: EffectLayerTransform3D) -> np.ndarray:
    x, y, z = map(math.radians, (transform.rotation_x, transform.rotation_y, transform.rotation_z))
    cx, sx = math.cos(x), math.sin(x); cy, sy = math.cos(y), math.sin(y); cz, sz = math.cos(z), math.sin(z)
    rx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=np.float64)
    ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=np.float64)
    rz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=np.float64)
    return rz @ ry @ rx


def project_points_3d(
    points: np.ndarray, transform: EffectLayerTransform3D,
    canvas_width: int, canvas_height: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Project local XYZ points using S -> Rx -> Ry -> Rz -> T."""
    values = np.asarray(points, dtype=np.float64).copy()
    values[:, 0] *= transform.scale_x; values[:, 1] *= transform.scale_y
    values = values @ _rotation_matrix(transform).T
    values += np.array((transform.position_x, transform.position_y, transform.position_z))
    valid = np.isfinite(values).all(axis=1)
    if transform.perspective_strength > 0.0:
        focal = focal_length(canvas_width, canvas_height, transform.perspective_strength)
        denominator = focal - values[:, 2]
        valid &= denominator > focal * _NEAR_RATIO
        safe = np.maximum(denominator, focal * _NEAR_RATIO)
        factor = focal / safe
        values[:, 0] *= factor; values[:, 1] *= factor
    return values[:, :2], valid


def projected_quad(
    bounds: tuple[int, int, int, int], transform: EffectLayerTransform3D,
    canvas_width: int, canvas_height: int,
) -> tuple[np.ndarray, np.ndarray]:
    left, top, right, bottom = bounds
    pivot_x = canvas_width / 2.0 + transform.pivot_x
    pivot_y = canvas_height / 2.0 + transform.pivot_y
    points = np.array(((left-pivot_x, top-pivot_y, 0), (right-pivot_x, top-pivot_y, 0),
                       (right-pivot_x, bottom-pivot_y, 0), (left-pivot_x, bottom-pivot_y, 0)), dtype=np.float64)
    projected, valid = project_points_3d(points, transform, canvas_width, canvas_height)
    projected[:, 0] += pivot_x; projected[:, 1] += pivot_y
    return projected, valid


def unproject_point_2d(x: float, y: float, transform: EffectLayerTransform3D, canvas_width: int, canvas_height: int) -> tuple[float,float] | None:
    """Map a projected canvas point back onto the untransformed layer plane."""
    destination,valid=projected_quad((-.5,-.5,canvas_width-.5,canvas_height-.5),transform,canvas_width,canvas_height)
    if not valid.all():return None
    try:inverse=np.linalg.inv(_homography_from_unit_square(destination))
    except np.linalg.LinAlgError:return None
    mapped=inverse@np.array((float(x),float(y),1.0));
    if abs(mapped[2])<1e-10 or not np.isfinite(mapped).all():return None
    u,v=mapped[0]/mapped[2],mapped[1]/mapped[2]
    return float(u*canvas_width-.5),float(v*canvas_height-.5)


def transform_rgba_frame(frame: np.ndarray, transform: EffectLayerTransform3D, effect_frame: int = 0) -> np.ndarray:
    """Transform one canvas-sized RGBA frame; identity returns the input object."""
    evaluated = transform.evaluated(effect_frame)
    if evaluated.is_identity():
        return frame
    height, width = frame.shape[:2]
    output = empty_pixels(width, height)
    alpha_y, alpha_x = np.nonzero(frame[..., 3])
    if not len(alpha_x) or evaluated.opacity <= 0.0:
        return output
    left, right = int(alpha_x.min()), int(alpha_x.max())
    top, bottom = int(alpha_y.min()), int(alpha_y.max())
    # Pixel-edge quad keeps inverse nearest sampling stable at integer centers.
    destination, valid_corners = projected_quad((left-.5, top-.5, right+.5, bottom+.5), evaluated, width, height)
    if not valid_corners.all() or not np.isfinite(destination).all():
        return output
    try:
        inverse = np.linalg.inv(_homography_from_unit_square(destination))
    except np.linalg.LinAlgError:
        return output
    x0=max(0,int(math.floor(destination[:,0].min())));x1=min(width-1,int(math.ceil(destination[:,0].max())))
    y0=max(0,int(math.floor(destination[:,1].min())));y1=min(height-1,int(math.ceil(destination[:,1].max())))
    if x1 < x0 or y1 < y0:
        return output
    gx,gy=np.meshgrid(np.arange(x0,x1+1,dtype=np.float64)+.5,np.arange(y0,y1+1,dtype=np.float64)+.5)
    mapped=np.stack((gx,gy,np.ones_like(gx)),axis=-1)@inverse.T;den=mapped[...,2]
    safe=np.where(np.abs(den)>1e-10,den,1.0);u=mapped[...,0]/safe;v=mapped[...,1]/safe
    inside=(np.abs(den)>1e-10)&(u>=0)&(u<=1)&(v>=0)&(v<=1)
    crop=frame[top:bottom+1,left:right+1]
    sx=np.clip(np.floor(u*crop.shape[1]),0,crop.shape[1]-1).astype(int)
    sy=np.clip(np.floor(v*crop.shape[0]),0,crop.shape[0]-1).astype(int)
    sampled=crop[sy,sx].copy();sampled[~inside]=0
    if evaluated.opacity < 1.0:
        sampled[...,3]=np.rint(sampled[...,3].astype(np.float64)*evaluated.opacity).astype(np.uint8)
    _source_over(output[y0:y1+1,x0:x1+1],sampled)
    return output
