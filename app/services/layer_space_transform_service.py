"""Shared Layer Space 2.5D evaluation for renderers, guides, and gizmos."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from app.models.effect_resource_layer import EffectLayerTransform3D
from app.services.effect_layer_transform_3d_render_service import focal_length
from app.models.frame import empty_pixels
from app.services.effect_render_service import _homography_from_unit_square,_source_over
from app.services.layer_parenting_service import apply_affine_xy

_NEAR_RATIO = 0.05


@dataclass(frozen=True)
class ProjectedLayerPoint:
    x: float
    y: float
    view_z: float
    perspective_scale: float
    valid: bool


def rotation_matrix(transform: EffectLayerTransform3D, *, local_z_spin: bool = False) -> np.ndarray:
    """Return the canonical Rx -> Ry -> Rz layer-space rotation matrix."""
    x, y, z = map(math.radians, (transform.rotation_x, transform.rotation_y, transform.rotation_z))
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    rx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=np.float64)
    ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=np.float64)
    rz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=np.float64)
    # Effect Layer Space retains its established X -> Y -> world-Z order.
    # Resource Sprite 2.5D uses local Z first so Z spins content inside the
    # already-tilted plane without changing that plane's normal.
    return (ry @ rx @ rz) if local_z_spin else (rz @ ry @ rx)


def transform_local_points(
    points: np.ndarray,
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
    frame: int = 0,
    *, local_z_spin: bool = False,
) -> np.ndarray:
    """Transform absolute canvas-local XYZ points into Layer Space."""
    value = transform.evaluated(frame)
    result = np.asarray(points, dtype=np.float64).reshape((-1, 3)).copy()
    pivot = np.array((canvas_width / 2.0 + value.pivot_x, canvas_height / 2.0 + value.pivot_y, 0.0))
    result -= pivot
    result[:, 0] *= value.scale_x
    result[:, 1] *= value.scale_y
    result = result @ rotation_matrix(value,local_z_spin=local_z_spin).T
    result += pivot + np.array((value.position_x, value.position_y, value.position_z))
    return result


def project_world_points(
    points: np.ndarray,
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
    frame: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Project Layer Space points through the fixed editor camera."""
    value = transform.evaluated(frame)
    world = np.asarray(points, dtype=np.float64).reshape((-1, 3))
    projected = world[:, :2].copy()
    factors = np.ones(len(world), dtype=np.float64)
    valid = np.isfinite(world).all(axis=1)
    if value.perspective_strength > 0.0:
        focal = focal_length(canvas_width, canvas_height, value.perspective_strength)
        denominator = focal - world[:, 2]
        valid &= denominator > focal * _NEAR_RATIO
        factors = np.minimum(20.0, focal / np.maximum(denominator, focal * _NEAR_RATIO))
        center = np.array((canvas_width / 2.0, canvas_height / 2.0))
        projected = center + (projected - center) * factors[:, None]
    valid &= np.isfinite(projected).all(axis=1)
    return projected, world[:, 2].copy(), factors, valid


def project_local_points(
    points: np.ndarray,
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
    frame: int = 0,
    *, local_z_spin: bool = False,
    post_affine=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    world = transform_local_points(points, transform, canvas_width, canvas_height, frame,local_z_spin=local_z_spin)
    projected,depth,factor,valid=project_world_points(world, transform, canvas_width, canvas_height, frame)
    if post_affine is not None:
        projected=apply_affine_xy(np.column_stack((projected,np.zeros(len(projected)))),post_affine)[:,:2]
        valid&=np.isfinite(projected).all(axis=1)
    return projected,depth,factor,valid


def project_local_point(
    x: float,
    y: float,
    z: float,
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
    frame: int = 0,
    *, local_z_spin: bool = False, post_affine=None,
) -> ProjectedLayerPoint:
    projected, depth, factor, valid = project_local_points(
        np.array(((x, y, z),), dtype=np.float64), transform, canvas_width, canvas_height, frame,local_z_spin=local_z_spin,post_affine=post_affine
    )
    return ProjectedLayerPoint(
        float(projected[0, 0]), float(projected[0, 1]), float(depth[0]),
        float(factor[0]), bool(valid[0]),
    )


def projected_local_axes(
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
    frame: int = 0,
    length: float = 24.0,
    *, local_z_spin: bool = False, post_affine=None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the shared projected pivot and +X/+Y/+Z endpoints."""
    value = transform.evaluated(frame)
    pivot = np.array((canvas_width / 2.0 + value.pivot_x, canvas_height / 2.0 + value.pivot_y, 0.0))
    points = np.vstack((pivot, pivot + (length, 0, 0), pivot + (0, length, 0), pivot + (0, 0, length)))
    projected, _, _, valid = project_local_points(points, transform, canvas_width, canvas_height, frame,local_z_spin=local_z_spin,post_affine=post_affine)
    return projected, valid


def projected_layer_quad(
    bounds: tuple[float,float,float,float],
    transform: EffectLayerTransform3D,
    canvas_width: int,
    canvas_height: int,
    frame: int = 0,
    *, local_z_spin: bool = False,
    post_affine=None,
) -> tuple[np.ndarray,np.ndarray]:
    left,top,right,bottom=bounds
    points=np.array(((left,top,0),(right,top,0),(right,bottom,0),(left,bottom,0)),dtype=np.float64)
    projected,_,_,valid=project_local_points(points,transform,canvas_width,canvas_height,frame,local_z_spin=local_z_spin,post_affine=post_affine)
    return projected,valid


def transform_layer_space_rgba_frame(
    frame_rgba: np.ndarray,
    transform: EffectLayerTransform3D,
    effect_frame: int = 0,
    *, local_z_spin: bool = False,
    post_affine=None,
) -> np.ndarray:
    """Rasterize a flat Single resource with the canonical Layer Space camera."""
    value=transform.evaluated(effect_frame)
    if value.is_identity() and post_affine is None:return frame_rgba
    height,width=frame_rgba.shape[:2];output=empty_pixels(width,height);alpha_y,alpha_x=np.nonzero(frame_rgba[...,3])
    if not len(alpha_x) or value.opacity<=0:return output
    left,right=int(alpha_x.min()),int(alpha_x.max())+1;top,bottom=int(alpha_y.min()),int(alpha_y.max())+1
    # Project half-open source pixel cells by their outer edges, then sample
    # destination pixel centers.  Resource selection uses the same convention.
    destination,valid=projected_layer_quad((left,top,right,bottom),value,width,height,local_z_spin=local_z_spin,post_affine=post_affine)
    if not valid.all() or not np.isfinite(destination).all():return output
    try:inverse=np.linalg.inv(_homography_from_unit_square(destination))
    except np.linalg.LinAlgError:return output
    x0=max(0,int(math.floor(destination[:,0].min())));x1=min(width,int(math.ceil(destination[:,0].max())))
    y0=max(0,int(math.floor(destination[:,1].min())));y1=min(height,int(math.ceil(destination[:,1].max())))
    if x1<=x0 or y1<=y0:return output
    gx,gy=np.meshgrid(np.arange(x0,x1,dtype=np.float64)+.5,np.arange(y0,y1,dtype=np.float64)+.5)
    mapped=np.stack((gx,gy,np.ones_like(gx)),axis=-1)@inverse.T;den=mapped[...,2];safe=np.where(np.abs(den)>1e-10,den,1.0)
    u=mapped[...,0]/safe;v=mapped[...,1]/safe;inside=(np.abs(den)>1e-10)&(u>=0)&(u<1)&(v>=0)&(v<1)
    crop=frame_rgba[top:bottom,left:right];raw_sx=np.floor(u*crop.shape[1]).astype(int);raw_sy=np.floor(v*crop.shape[0]).astype(int)
    inside&=(raw_sx>=0)&(raw_sx<crop.shape[1])&(raw_sy>=0)&(raw_sy<crop.shape[0]);sx=np.where(inside,raw_sx,0);sy=np.where(inside,raw_sy,0)
    sampled=crop[sy,sx].copy();sampled[~inside]=0
    if value.opacity<1:sampled[...,3]=np.rint(sampled[...,3].astype(np.float64)*value.opacity).astype(np.uint8)
    _source_over(output[y0:y1,x0:x1],sampled);return output


def unproject_layer_space_point(
    x: float,y: float,transform: EffectLayerTransform3D,
    canvas_width: int,canvas_height: int,frame: int = 0,
) -> tuple[float,float] | None:
    """Map a projected canvas point back to the local Z=0 layer plane."""
    destination,valid=projected_layer_quad((0,0,canvas_width,canvas_height),transform,canvas_width,canvas_height,frame)
    if not valid.all():return None
    try:inverse=np.linalg.inv(_homography_from_unit_square(destination))
    except np.linalg.LinAlgError:return None
    mapped=inverse@np.array((float(x),float(y),1.0))
    if abs(mapped[2])<1e-10 or not np.isfinite(mapped).all():return None
    u,v=mapped[0]/mapped[2],mapped[1]/mapped[2]
    return float(u*canvas_width),float(v*canvas_height)
