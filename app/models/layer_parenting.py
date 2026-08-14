"""Stable-ID leaf parenting metadata and corruption-safe graph repair."""

from __future__ import annotations

import logging

IDENTITY_PARENT_OFFSET=(1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0)


def normalize_parent_offset(value):
    if not isinstance(value,(list,tuple)) or len(value)!=9:return IDENTITY_PARENT_OFFSET
    try:return tuple(float(part) for part in value)
    except (TypeError,ValueError):return IDENTITY_PARENT_OFFSET


def parent_offset_is_identity(value,tolerance=1e-9):
    return all(abs(a-b)<=tolerance for a,b in zip(normalize_parent_offset(value),IDENTITY_PARENT_OFFSET))


def would_create_parent_cycle(layers,child_id,parent_id):
    if parent_id is None:return False
    if child_id==parent_id:return True
    by_id={item.id:item for item in layers};current=parent_id;visited=set()
    while current is not None and current not in visited:
        if current==child_id:return True
        visited.add(current);layer=by_id.get(current)
        if layer is None:return False
        current=layer.parent_id
    return current is not None


def repair_parent_links(layers):
    """Clear missing/self/cyclic references deterministically, preserving leaves."""
    by_id={item.id:item for item in layers};repaired=[]
    for layer in layers:
        layer.parent_offset=normalize_parent_offset(getattr(layer,"parent_offset",None))
        parent=getattr(layer,"parent_id",None)
        if parent is not None:parent=str(parent)
        if parent==layer.id or parent not in by_id:
            if parent is not None:repaired.append(layer.id)
            layer.parent_id=None
        else:layer.parent_id=parent
    # Stable leaf order decides which edge completing a corrupt cycle is cut.
    for start in layers:
        order=[];positions={};current=start
        while current is not None:
            if current.id in positions:
                offender=order[-1];offender.parent_id=None;repaired.append(offender.id);break
            positions[current.id]=len(order);order.append(current)
            current=by_id.get(current.parent_id) if current.parent_id is not None else None
    if repaired:
        logging.getLogger("pixel_effect_maker").warning(
            "repaired invalid layer parent links: %s", ",".join(dict.fromkeys(repaired))
        )
    return repaired


def surviving_parent_dependencies(layers,delete_ids):
    deleting=set(delete_ids)
    return [(item.id,item.parent_id) for item in layers if item.id not in deleting and item.parent_id in deleting]
