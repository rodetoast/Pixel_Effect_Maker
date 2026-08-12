from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QPointF,QSettings
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.models.source_asset import SourceAsset
from app.services.resource_composition_render_service import render_composition_frame
from app.ui.resource_editor_v2.composition_canvas import CompositionCanvas
from app.ui.resource_editor_v2.composition_inspector import LayerInspector
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget


APP=QApplication.instance() or QApplication([])


def context(size=28):
    pixels=np.zeros((size,size,4),dtype=np.uint8);pixels[2:-1,2:-1]=[220,60,30,255]
    project=Project.create_default(width=size,height=size,frame_count=1);asset=SourceAsset("pivot",pixels)
    composition=ResourceComposition("pivot",size,size,12,1,True);layer=CompositionLayer("pivot","source_asset",asset.id,0,0,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y)
    composition.layers.append(layer);project.source_assets.append(asset);project.resource_compositions.append(composition)
    canvas=CompositionCanvas();canvas.resize(520,420);canvas.set_context(project,composition,layer,0);canvas.show();APP.processEvents()
    return project,asset,composition,layer,canvas


def test_28x28_default_pivot_and_marker_are_geometric_center():
    _,asset,_,layer,canvas=context(28)
    assert (asset.pivot_x,asset.pivot_y)==(layer.pivot_x,layer.pivot_y)==(14,14)
    assert canvas.pivot_marker_position()==canvas.to_widget(QPointF(14,14))
    canvas.close()


@pytest.mark.parametrize("size,expected",[(28,14.0),(29,14.5)])
def test_center_layer_pivot_uses_source_outer_edge_center(size,expected):
    project,asset,composition,layer,canvas=context(size);editor=ResourceEditorWidget(QSettings());editor.refresh(project);editor.composition=composition;editor.selected_layer=layer
    editor._center_layer_pivot();assert (layer.pivot_x,layer.pivot_y)==(expected,expected)
    editor.close();canvas.close()


def test_pivot_change_updates_sprite_relative_to_projected_marker():
    project,_,composition,layer,canvas=context(28);before=canvas.selection_polygon_comp(layer);marker=canvas.pivot_marker_position()
    layer.pivot_x=7;layer.pivot_y=9;composition.touch();canvas.update();APP.processEvents();after=canvas.selection_polygon_comp(layer)
    assert after!=before and canvas.pivot_marker_position()==marker
    # Position semantics keep the world pivot fixed; changing its local value
    # moves the sprite footprint immediately relative to that visible marker.
    rendered=render_composition_frame(project,composition,0);assert np.any(rendered[...,3])
    canvas.close()


def test_selection_quad_uses_half_open_alpha_outer_edges():
    _,_,_,layer,canvas=context(28);points=canvas.selection_polygon_comp(layer)
    assert [(point.x(),point.y()) for point in points]==[(2,2),(27,2),(27,27),(2,27)]
    canvas.close()


def test_pivot_spinbox_change_updates_canvas_geometry_immediately():
    project,asset,composition,layer,canvas=context(28);before=canvas.selection_polygon_comp(layer);inspector=LayerInspector();inspector.set_layer(layer,asset,0);inspector.pivot_x.setValue(7);APP.processEvents();after=canvas.selection_polygon_comp(layer)
    assert layer.pivot_x==7 and after!=before and canvas.pivot_marker_position()==canvas.to_widget(QPointF(14,14))
    inspector.close();canvas.close()


def test_pivot_marker_tracks_zoom_pan_and_rotation():
    _,_,composition,layer,canvas=context(28);base=canvas.pivot_marker_position();canvas.zoom=4;canvas.pan=QPointF(23,-17);moved=canvas.pivot_marker_position()
    assert moved!=base and moved==canvas.to_widget(QPointF(14,14))
    layer.add_property("rotation_x").default_value=55;layer.add_property("rotation_y").default_value=20;layer.add_property("rotation").default_value=70;composition.touch()
    assert canvas.pivot_marker_position()==moved
    canvas.close()


def test_pivot_marker_is_canvas_overlay_not_resource_pixels():
    project,_,composition,_,canvas=context(28);before=render_composition_frame(project,composition,0).copy();canvas.set_mode("pivot","Pivot");canvas.repaint();APP.processEvents();after=render_composition_frame(project,composition,0)
    assert np.array_equal(before,after)
    canvas.close()
