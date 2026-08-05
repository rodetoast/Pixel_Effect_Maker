"""Render dispatch for unified Effect Resource Layers."""

from __future__ import annotations

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.services.effect_composition_layer_render_service import (
    apply_effect_composition_layer,
    render_effect_composition_layer,
)
from app.services.particle_render_service import apply_particle_frames, render_particle_frames


def render_effect_resource_layer(project, layer: EffectResourceLayer):
    if layer.placement_mode == PLACEMENT_PARTICLE:
        return render_particle_frames(project, layer.as_particle_emitter())
    return render_effect_composition_layer(project, layer.as_composition_layer())


def apply_effect_resource_layer(project, layer: EffectResourceLayer, frames=None):
    frames = render_effect_resource_layer(project, layer) if frames is None else frames
    if layer.placement_mode == PLACEMENT_PARTICLE:
        generated = apply_particle_frames(project, layer.as_particle_emitter(), frames)
    else:
        generated = apply_effect_composition_layer(project, layer.as_composition_layer(), frames)
    layer.generated_layer_id = generated.id
    layer.sync_active_adapter()
    generated.visible = layer.visible
    return generated
