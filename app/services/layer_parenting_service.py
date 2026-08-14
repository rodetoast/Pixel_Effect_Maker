"""Memoized 2D affine transform inheritance for Resource and Effect leaves."""

from __future__ import annotations

import math
import numpy as np

from app.models.layer_parenting import IDENTITY_PARENT_OFFSET,normalize_parent_offset,would_create_parent_cycle
from app.models.effect_resource_layer import EffectLayerTransform3D


def offset_matrix(value):return np.asarray(normalize_parent_offset(value),dtype=np.float64).reshape((3,3))
def offset_data(value):return tuple(float(part) for part in np.asarray(value,dtype=np.float64).reshape(9))


def affine_trs(x,y,rotation_z,scale_x,scale_y,center_x,center_y,pivot_x=0.0,pivot_y=0.0):
    angle=math.radians(float(rotation_z));c,s=math.cos(angle),math.sin(angle);sx,sy=float(scale_x),float(scale_y);cx=float(center_x)+float(pivot_x);cy=float(center_y)+float(pivot_y)
    linear=np.array(((c*sx,-s*sy),(s*sx,c*sy)),dtype=np.float64);translation=np.array((cx+float(x),cy+float(y)))-linear@np.array((cx,cy))
    return np.array(((linear[0,0],linear[0,1],translation[0]),(linear[1,0],linear[1,1],translation[1]),(0.0,0.0,1.0)),dtype=np.float64)


def resource_local_affine(layer,frame,composition):
    position=layer.value("position",frame);scale=layer.value("scale",frame)
    return affine_trs(position[0],position[1],layer.value("rotation",frame),scale[0],scale[1],composition.width/2,composition.height/2)


def effect_local_affine(layer,frame,project):
    value=(layer.layer_space_transform if layer.advanced_transform_enabled else EffectLayerTransform3D()).evaluated(frame)
    return affine_trs(value.position_x,value.position_y,value.rotation_z,value.scale_x,value.scale_y,project.width/2,project.height/2,value.pivot_x,value.pivot_y)


def resolve_world_affines(layers,frame,local_builder):
    """Resolve every world matrix once for this evaluation pass."""
    by_id={item.id:item for item in layers};memo={};visiting=set()
    def resolve(identifier):
        if identifier in memo:return memo[identifier]
        layer=by_id[identifier]
        if identifier in visiting:
            # Load repair should prevent this; identity fallback guarantees render safety.
            return local_builder(layer,frame)
        visiting.add(identifier);parent=np.eye(3,dtype=np.float64)
        if layer.parent_id in by_id:parent=resolve(layer.parent_id)
        result=parent@offset_matrix(layer.parent_offset)@local_builder(layer,frame);visiting.discard(identifier);memo[identifier]=result;return result
    for layer in layers:resolve(layer.id)
    return memo


def set_parent_keep_world(layers,child_id,parent_id,frame,local_builder):
    by_id={item.id:item for item in layers};child=by_id.get(child_id)
    if child is None or (parent_id is not None and parent_id not in by_id) or child.parent_id==parent_id:return False
    if would_create_parent_cycle(layers,child_id,parent_id):return False
    before=resolve_world_affines(layers,frame,local_builder)[child_id];local=local_builder(child,frame)
    parent=np.eye(3,dtype=np.float64) if parent_id is None else resolve_world_affines(layers,frame,local_builder)[parent_id]
    try:offset=np.linalg.inv(parent)@before@np.linalg.inv(local)
    except np.linalg.LinAlgError:return False
    child.parent_id=parent_id;child.parent_offset=offset_data(offset);return True


def apply_affine_xy(points,matrix):
    values=np.asarray(points,dtype=np.float64).reshape((-1,3)).copy();homogeneous=np.column_stack((values[:,:2],np.ones(len(values))))@np.asarray(matrix,dtype=np.float64).T;values[:,:2]=homogeneous[:,:2];return values


def affine_axis_scales(matrix):
    linear=np.asarray(matrix,dtype=np.float64)[:2,:2];return float(np.linalg.norm(linear[:,0])),float(np.linalg.norm(linear[:,1]))


def local_only_transform(transform,frame):
    value=transform.evaluated(frame)
    return EffectLayerTransform3D(position_z=value.position_z,rotation_x=value.rotation_x,rotation_y=value.rotation_y,opacity=value.opacity,pivot_x=value.pivot_x,pivot_y=value.pivot_y,perspective_strength=value.perspective_strength)
