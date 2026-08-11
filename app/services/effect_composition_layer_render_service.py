"""Render a directly placed Resource Composition into an Effect layer."""

from __future__ import annotations

from uuid import uuid4

from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.frame import empty_pixels
from app.models.layer import Layer
from app.models.project import Project
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import EffectRenderError, render_transformed_source
from app.services.resource_composition_render_service import render_composition_frame, render_composition_frames


def composition_layer_position(layer: EffectCompositionLayer, frame: int) -> tuple[float, float]:
    """Return the same linear position used by rendering and editing guides."""
    span = max(1, layer.end_frame - layer.start_frame)
    amount = max(0.0, min(1.0, (frame - layer.start_frame) / span))
    return (
        layer.start_x + (layer.end_x - layer.start_x) * amount,
        layer.start_y + (layer.end_y - layer.start_y) * amount,
    )


def render_effect_composition_layer(project: Project, layer: EffectCompositionLayer) -> list:
    layer.validate()
    composition = next(
        (item for item in project.resource_compositions if item.id == layer.resource_composition_id),
        None,
    )
    if composition is None:
        raise EffectRenderError("the Resource Composition does not exist")
    resource_frames = render_composition_frames(project, composition)
    output_count = max(len(project.frames), layer.end_frame + 1)
    outputs = [empty_pixels(project.width, project.height) for _ in range(output_count)]
    for effect_frame in range(layer.start_frame, min(output_count, layer.end_frame + 1)):
        elapsed = effect_frame - layer.start_frame
        resource_index = int(elapsed * composition.fps / max(1, project.fps))
        if composition.loop:
            resource_index %= len(resource_frames)
        else:
            resource_index = min(resource_index, len(resource_frames) - 1)
        x, y = composition_layer_position(layer, effect_frame)
        asset = SourceAsset(
            composition.name,
            resource_frames[resource_index],
            pivot_x=float(composition.pivot_x),
            pivot_y=float(composition.pivot_y),
        )
        render_transformed_source(
            outputs[effect_frame], asset,
            position_x=x, position_y=y, rotation=0.0, scale_x=1.0, scale_y=1.0,
            horizontal_tilt=0.0, vertical_tilt=0.0, perspective=0.0, opacity=1.0,
        )
    return outputs


def render_effect_composition_layer_current_frame(project: Project, layer: EffectCompositionLayer, effect_frame: int):
    """Render one exact placement frame without allocating the full sequence."""
    layer.validate();effect_frame=int(effect_frame);output=empty_pixels(project.width,project.height)
    if effect_frame<layer.start_frame or effect_frame>layer.end_frame:return output
    composition=next((item for item in project.resource_compositions if item.id==layer.resource_composition_id),None)
    if composition is None:raise EffectRenderError("the Resource Composition does not exist")
    elapsed=effect_frame-layer.start_frame;resource_index=int(elapsed*composition.fps/max(1,project.fps))
    if composition.loop:resource_index%=composition.frame_count
    else:resource_index=min(resource_index,composition.frame_count-1)
    pixels=render_composition_frame(project,composition,resource_index);x,y=composition_layer_position(layer,effect_frame)
    asset=SourceAsset(composition.name,pixels,pivot_x=float(composition.pivot_x),pivot_y=float(composition.pivot_y))
    render_transformed_source(output,asset,position_x=x,position_y=y,rotation=0.0,scale_x=1.0,scale_y=1.0,
        horizontal_tilt=0.0,vertical_tilt=0.0,perspective=0.0,opacity=1.0)
    return output


def apply_effect_composition_layer(project: Project, effect_layer: EffectCompositionLayer, outputs: list) -> Layer:
    layer = next((item for item in project.layers if item.id == effect_layer.generated_layer_id), None)
    if layer is None:
        layer = Layer(
            id=uuid4().hex, name=effect_layer.name, kind="generated",
            generator_id=effect_layer.id,
        )
        project.layers.append(layer)
    while len(project.frames) < len(outputs):
        project.add_frame()
    for index, frame in enumerate(project.frames):
        frame.layer_pixels[layer.id] = (
            outputs[index].copy() if index < len(outputs)
            else empty_pixels(project.width, project.height)
        )
    layer.name = effect_layer.name
    layer.kind = "generated"
    layer.generator_id = effect_layer.id
    effect_layer.generated_layer_id = layer.id
    return layer
