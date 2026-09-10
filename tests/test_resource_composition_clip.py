"""Composition clipping is destination-space, never a pre-transform crop."""
import numpy as np
import pytest
from app.models.project import Project
from app.models.resource_composition import ResourceComposition,CompositionLayer
from app.models.source_asset import SourceAsset
from app.services.resource_composition_render_service import render_composition_frame,render_editor_region,composition_as_clip

def scene(size=8):
    project=Project.create_default(width=28,height=28)
    composition=ResourceComposition('Clip',28,28,12,3)
    source=SourceAsset('Sprite',np.full((size,size,4),255,dtype=np.uint8))
    layer=CompositionLayer('Sprite','source_asset',source.id,0,2,pivot_x=size/2,pivot_y=size/2)
    composition.layers=[layer];project.source_assets=[source];project.resource_compositions=[composition]
    return project,composition,layer

@pytest.mark.parametrize('position',[(-14,0),(14,0),(0,-14),(0,14)])
@pytest.mark.parametrize('rotation',[0,45,90,-45,720,1080])
@pytest.mark.parametrize('scale',[(1,1),(2,2),(.5,.5),(2,.5)])
def test_final_clip_and_overscan_share_transformed_pixels(position,rotation,scale):
    project,composition,layer=scene()
    for key,value in [('position',position),('rotation',rotation),('scale',scale)]:layer.add_property(key).default_value=value
    final=render_composition_frame(project,composition,0)
    editor=render_editor_region(project,composition,0,(-28,-28,84,84))
    assert final.shape==(28,28,4)
    assert np.array_equal(final,editor[28:56,28:56])
    outside=editor.copy();outside[28:56,28:56]=0
    assert outside[...,3].any() and final[...,3].any()

@pytest.mark.parametrize('property,value',[('position_z',1),('rotation_x',25),('rotation_y',35),('perspective_strength',.5)])
def test_large_source_is_not_cropped_before_2_5d_transform(property,value):
    project,composition,layer=scene(60)
    layer.add_property('scale').default_value=[.4,.4]
    layer.add_property(property).default_value=value
    final=render_composition_frame(project,composition,0)
    # A pre-transform 28px crop shrinks to only ~11px, losing most source pixels.
    assert np.count_nonzero(final[...,3])>250
    editor=render_editor_region(project,composition,0,(-28,-28,84,84))
    assert np.array_equal(final,editor[28:56,28:56])

def test_pivot_parent_transform_and_effect_clip_remain_strict():
    project,composition,child=scene(60)
    parent=CompositionLayer('Parent','source_asset','missing',0,2)
    parent.add_property('position').default_value=[15,0]
    parent.add_property('rotation').default_value=45
    parent.add_property('scale').default_value=[.5,.5]
    child.parent_id=parent.id;child.pivot_x=10;child.pivot_y=20
    composition.layers.insert(0,parent)
    editor=render_editor_region(project,composition,0,(-64,-64,156,156))
    final=render_composition_frame(project,composition,0)
    assert np.array_equal(final,editor[64:92,64:92])
    assert np.count_nonzero(editor[...,3])>np.count_nonzero(final[...,3])
    clip=composition_as_clip(project,composition)
    assert all(frame.shape==(28,28,4) for frame in clip.frames)
    assert np.array_equal(clip.frames[0],final)
