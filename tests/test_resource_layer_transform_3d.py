from copy import deepcopy

import numpy as np
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectLayerTransform3D, EffectResourceLayer
from app.models.project import Project
from app.models.resource_composition import ResourceComposition
from app.services.effect_layer_transform_3d_render_service import (
    focal_length, project_points_3d, transform_rgba_frame,
)
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow

APP=QApplication.instance() or QApplication([])


def test_effect_layer_transform_identity_defaults_and_v6_round_trip():
    transform=EffectLayerTransform3D()
    assert transform.is_identity() and transform.to_dict()["position"]==[0,0,0]
    transform.rotation_x=25;transform.position_z=8;transform.set_keyframe("rotation_y",3,40,"Ease In")
    loaded=EffectLayerTransform3D.from_dict(transform.to_dict())
    assert loaded.to_dict()==transform.to_dict() and loaded.value("rotation_y",3)==40
    layer=EffectResourceLayer("R","composition",layer_transform=transform)
    assert EffectResourceLayer.from_dict(layer.to_dict()).layer_transform.to_dict()==transform.to_dict()


def test_existing_v6_without_transform_and_migrated_v5_are_identity():
    project=Project.create_default();composition=ResourceComposition("R");project.resource_compositions.append(composition)
    layer=EffectResourceLayer("Layer",composition.id);project.effect_resource_layers.append(layer)
    data=project.to_dict();data["effect_resource_layers"][0].pop("layer_transform")
    assert Project.from_dict(data).effect_resource_layers[0].layer_transform.is_identity()
    data=project.to_dict();data["format_version"]=5;data.pop("effect_resource_layers")
    assert all(item.layer_transform.is_identity() for item in Project.from_dict(data).effect_resource_layers)


def test_transform_tracks_reuse_easing_and_do_not_shortest_path_rotation():
    transform=EffectLayerTransform3D(rotation_z=0)
    transform.set_keyframe("rotation_z",0,0,"Linear");transform.set_keyframe("rotation_z",10,360,"Linear")
    assert transform.value("rotation_z",5)==180
    transform.set_keyframe("position_z",0,0,"Ease In");transform.set_keyframe("position_z",10,100)
    assert transform.value("position_z",5)==25


def test_identity_transform_is_pixel_exact_and_returns_fast_path():
    frame=np.zeros((9,11,4),dtype=np.uint8);frame[2:7,3:8]=[20,40,60,127]
    result=transform_rgba_frame(frame,EffectLayerTransform3D())
    assert result is frame and np.array_equal(result,frame)


def test_rotation_xyz_and_perspective_are_deterministic_nearest_rgba():
    frame=np.zeros((17,17,4),dtype=np.uint8);frame[6:11,7:10]=[10,80,200,173]
    for transform in (EffectLayerTransform3D(rotation_z=90),EffectLayerTransform3D(rotation_x=35),EffectLayerTransform3D(rotation_y=-35),EffectLayerTransform3D(position_z=12,perspective_strength=.8)):
        first=transform_rgba_frame(frame,transform);second=transform_rgba_frame(frame,transform)
        assert np.array_equal(first,second);assert first.shape==frame.shape;assert set(np.unique(first[...,3]))<={0,173}
        assert not np.array_equal(first,frame)


def test_projection_safety_and_orthographic_depth_policy():
    point=np.array(((4.0,3.0,0.0),))
    a,valid=project_points_3d(point,EffectLayerTransform3D(position_z=100000,perspective_strength=1),64,64)
    assert np.isfinite(a).all() and not valid[0]
    b,valid=project_points_3d(point,EffectLayerTransform3D(position_z=100),64,64)
    assert valid[0] and np.array_equal(b,[[4,3]])
    assert focal_length(64,32,1)==128 and focal_length(64,32,.5)==256


def test_positive_z_composites_in_front_and_equal_z_is_stable():
    project=Project.create_default(width=2,height=2);back=project.layers[0];front=project.add_layer("front")
    project.frames[0].layer_pixels[back.id][:]=[255,0,0,255];project.frames[0].layer_pixels[front.id][:]=[0,0,255,255]
    a=EffectResourceLayer("a","",generated_layer_id=back.id);b=EffectResourceLayer("b","",generated_layer_id=front.id)
    project.effect_resource_layers=[a,b]
    assert np.array_equal(project.compose_frame(0)[0,0],[0,0,255,255])
    a.layer_transform.position_z=10
    assert np.array_equal(project.compose_frame(0)[0,0],[255,0,0,255])


def _window(tmp_path):
    settings=QSettings(str(tmp_path/"settings.ini"),QSettings.Format.IniFormat)
    return MainWindow(ShortcutSettingsService(settings))


def test_resource_layer_inspector_fields_reset_keyframe_and_gizmo_undo(tmp_path):
    window=_window(tmp_path);composition=ResourceComposition("R",width=8,height=8,frame_count=1);window.project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id);window.canvas.resize(700,500);window.show();APP.processEvents()
    panel=window.composition_layer_properties.transform_panel
    assert set(panel.fields)=={"position_x","position_y","position_z","rotation_x","rotation_y","rotation_z","scale_x","scale_y","opacity","perspective_strength","pivot_x","pivot_y"}
    panel.fields["rotation_x"].setValue(30);APP.processEvents();assert layer.layer_transform.rotation_x==30
    panel._add_key("rotation_y");assert "rotation_y" in layer.layer_transform.tracks
    panel._select_mode("move");handle=window.canvas.resource_transform_handle_positions()["z"].toPoint();before=window.application_undo_stack.count()
    QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=handle);QTest.mouseMove(window.canvas,handle+QPoint(16,-16));QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=handle+QPoint(16,-16));APP.processEvents()
    assert layer.layer_transform.position_z!=0 and window.application_undo_stack.count()==before+1
    window.application_undo_stack.undo();assert layer.layer_transform.position_z==0
    window.dirty=False;window._non_undo_dirty=False;window.close()


def test_reset_base_preserves_animation_tracks():
    transform=EffectLayerTransform3D(position_x=5,rotation_x=20,scale_x=2,perspective_strength=.5)
    transform.set_keyframe("position_x",2,9);tracks=deepcopy(transform.tracks);transform.reset_base()
    assert transform.is_identity() and transform.tracks==tracks
