"""Closed blend-mode vocabulary shared by model, renderer, and UI code."""

from __future__ import annotations


BLEND_NORMAL = "normal"
BLEND_ADDITIVE = "additive"
BLEND_MODES = (BLEND_NORMAL, BLEND_ADDITIVE)


def validate_blend_mode(value: str) -> str:
    """Return a supported persisted blend mode or reject unknown input."""
    mode = str(value)
    if mode not in BLEND_MODES:
        raise ValueError(f"unsupported blend mode: {mode!r}")
    return mode


def project_layer_blend_mode(project, generated_layer_id: str) -> str:
    """Resolve the logical particle emitter that owns a generated raster layer."""
    for layer in getattr(project, "effect_resource_layers", ()):
        if layer.generated_layer_id == generated_layer_id and layer.placement_mode == "particle":
            return validate_blend_mode(layer.particle_settings.blend_mode)
    for emitter in getattr(project, "particle_emitters", ()):
        if emitter.generated_layer_id == generated_layer_id:
            return validate_blend_mode(emitter.settings.blend_mode)
    return BLEND_NORMAL
