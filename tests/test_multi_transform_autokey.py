from __future__ import annotations

from app.models.effect_resource_layer import EffectResourceLayer
from app.models.resource_composition import CompositionLayer
from app.services.multi_transform_service import set_effect_local_property,set_resource_local_component


def test_batch_conditional_autokey_only_keys_animated_layers():
    static=CompositionLayer("static","source_asset","a",0,12);animated=CompositionLayer("animated","source_asset","b",0,12)
    animated.add_property("rotation").set_keyframe(0,0)
    set_resource_local_component(static,"rotation",0,6,720);set_resource_local_component(animated,"rotation",0,6,720)
    assert static.tracks["rotation"].default_value==720 and not static.tracks["rotation"].keyframes
    assert animated.tracks["rotation"].keyframe_at(6).value==720


def test_effect_batch_conditional_autokey_is_layer_local():
    static=EffectResourceLayer("static","r",end_frame=12);animated=EffectResourceLayer("animated","r",end_frame=12)
    animated.layer_transform.set_keyframe("scale_x",0,1)
    set_effect_local_property(static,"scale_x",6,2);set_effect_local_property(animated,"scale_x",6,2)
    assert static.layer_transform.scale_x==2 and "scale_x" not in static.layer_transform.tracks
    assert animated.layer_transform.tracks["scale_x"].keyframe_at(6).value==2
