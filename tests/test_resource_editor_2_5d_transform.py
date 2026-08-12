from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.animation_clip import AnimationClipAsset
from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.effect_render_service import render_transformed_source
from app.services.resource_composition_render_service import composition_as_clip,render_composition_frame
from app.services.resource_composition_render_service import composition_layer_transform
from app.services.layer_space_transform_service import projected_layer_quad,rotation_matrix
from app.ui.resource_editor_v2.composition_canvas import CompositionCanvas


APPLICATION=QApplication.instance() or QApplication([])


def context(animated=False):
    project=Project.create_default(width=24,height=24)
    first=np.zeros((8,10,4),dtype=np.uint8);first[1:7,1:4]=[255,40,20,255];first[5:7,4:9]=[20,170,255,255]
    if animated:
        second=first.copy();second[first[...,3]>0,:3]=[40,255,90]
        source=AnimationClipAsset("animated",[first,second],fps=12,pivot_x=2,pivot_y=4,frame_durations_ms=[83,83]);project.animation_clips.append(source);source_type="animation_clip"
    else:
        source=SourceAsset("sprite",first,pivot_x=2,pivot_y=4);project.source_assets.append(source);source_type="source_asset"
    composition=ResourceComposition("resource",24,24,12,2,True)
    layer=CompositionLayer("sprite",source_type,source.id,0,1,pivot_x=2,pivot_y=4);composition.layers.append(layer);project.resource_compositions.append(composition)
    return project,composition,layer,source


def test_existing_resource_rotation_z_is_backward_compatible():
    project,composition,layer,source=context();layer.add_property("position").set_keyframe(0,[3,-2]);layer.add_property("rotation").set_keyframe(0,37);layer.add_property("scale").set_keyframe(0,[1.4,.8]);layer.add_property("opacity").set_keyframe(0,.65)
    expected=np.zeros((24,24,4),dtype=np.uint8)
    render_transformed_source(expected,source,position_x=15,position_y=10,rotation=37,scale_x=1.4,scale_y=.8,horizontal_tilt=0,vertical_tilt=0,perspective=0,opacity=.65)
    assert np.array_equal(render_composition_frame(project,composition,0),expected)


def test_animated_resource_applies_same_plane_transform_each_frame():
    project,composition,layer,_=context(animated=True);layer.add_property("rotation_x").set_keyframe(0,55);layer.add_property("perspective_strength").set_keyframe(0,.7)
    clip=composition_as_clip(project,composition)
    assert len(clip.frames)==2
    assert np.array_equal(clip.frames[0][...,3],clip.frames[1][...,3])
    assert not np.array_equal(clip.frames[0][...,:3],clip.frames[1][...,:3])


def test_resource_2_5d_pivot_changes_plane_rotation_origin():
    project,composition,layer,_=context();layer.add_property("rotation_y").set_keyframe(0,55);layer.add_property("perspective_strength").set_keyframe(0,.7)
    centered=render_composition_frame(project,composition,0);layer.pivot_x=0;shifted=render_composition_frame(project,composition,0)
    assert not np.array_equal(centered,shifted)


def test_resource_2_5d_gizmo_updates_projected_quad_and_rotation_x():
    project,composition,layer,_=context();canvas=CompositionCanvas();canvas.resize(640,480);canvas.set_context(project,composition,layer,0);canvas.set_mode("rotate_x","Rotate X");canvas.show();APPLICATION.processEvents()
    before=list(canvas.selection_polygon_comp(layer));before_handle=canvas.rotation_handle_position("x")
    def update(property_id,value,final):
        layer.add_property(property_id).set_keyframe(0,value);canvas.update()
    canvas.transform_changed.connect(update)
    handle=before_handle.toPoint();center=canvas.projected_axis_positions()["center"].toPoint();QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(canvas,center+QPoint(45,20));QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=center+QPoint(45,20));APPLICATION.processEvents()
    after=list(canvas.selection_polygon_comp(layer));axes=canvas.projected_axis_positions()
    assert "rotation_x" in layer.tracks and abs(layer.value("rotation_x",0))>1
    assert before!=after and set(axes)=={"center","x","y","z"} and len(canvas._rotation_ring("x"))>12
    canvas.close()


def test_resource_local_z_spin_preserves_tilted_plane_normal_and_rotates_axes():
    project,composition,layer,_=context();layer.add_property("rotation_x").set_keyframe(0,55);layer.add_property("rotation_y").set_keyframe(0,20)
    normals=[];axes=[]
    for angle in (0,45,180):
        layer.add_property("rotation").set_keyframe(0,angle);matrix=rotation_matrix(composition_layer_transform(layer,0),local_z_spin=True)
        normals.append(matrix@np.array((0.0,0.0,1.0)));axes.append(matrix@np.array((1.0,0.0,0.0)))
    assert np.allclose(normals[0],normals[1]) and np.allclose(normals[0],normals[2])
    assert not np.allclose(axes[0],axes[1]) and not np.allclose(axes[0],axes[2])


def test_resource_local_z_spin_differs_from_world_z_after_xy_tilt():
    project,composition,layer,_=context();layer.add_property("rotation_x").set_keyframe(0,55);layer.add_property("rotation_y").set_keyframe(0,20);layer.add_property("rotation").set_keyframe(0,45);layer.add_property("perspective_strength").set_keyframe(0,.7)
    transform=composition_layer_transform(layer,0);bounds=(7,8,17,16)
    desired,desired_valid=projected_layer_quad(bounds,transform,24,24,local_z_spin=True);wrong,wrong_valid=projected_layer_quad(bounds,transform,24,24)
    assert desired_valid.all() and wrong_valid.all() and not np.allclose(desired,wrong)
    canvas=CompositionCanvas();canvas.set_context(project,composition,layer,0)
    actual=np.array([(point.x(),point.y()) for point in canvas.selection_polygon_comp(layer)])
    source_bounds=canvas._source_alpha_bounds(canvas._source(layer));x0,y0,x1,y1=source_bounds;expected,_=projected_layer_quad((12+x0-layer.pivot_x,12+y0-layer.pivot_y,12+x1-layer.pivot_x,12+y1-layer.pivot_y),transform,24,24,local_z_spin=True)
    assert np.allclose(actual,expected)


def test_resource_local_z_spin_gizmo_ring_follows_tilted_plane():
    project,composition,layer,_=context();layer.add_property("rotation_x").set_keyframe(0,60);layer.add_property("rotation_y").set_keyframe(0,15);layer.add_property("perspective_strength").set_keyframe(0,.6)
    canvas=CompositionCanvas();canvas.resize(640,480);canvas.set_context(project,composition,layer,0);ring=canvas._rotation_ring("z")
    bounds=ring.boundingRect();assert len(ring)==49 and abs(bounds.width()-bounds.height())>5
    before=rotation_matrix(composition_layer_transform(layer,0),local_z_spin=True)@np.array((0.0,0.0,1.0));layer.add_property("rotation").set_keyframe(0,135);after=rotation_matrix(composition_layer_transform(layer,0),local_z_spin=True)@np.array((0.0,0.0,1.0))
    assert np.allclose(before,after)
