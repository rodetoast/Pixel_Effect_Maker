import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from time import perf_counter
import numpy as np
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from app.models.layer_group import LayerGroup,group_node
from app.ui.resource_editor_v2.composition_canvas import CompositionCanvas
from app.services.resource_composition_render_service import render_editor_region
from tests.test_resource_composition_clip import scene

APP=QApplication.instance() or QApplication([])

def test_overscan_undo_redo_after_selection_change(tmp_path):
    from tests.test_multi_transform_workflow import _resource_editor
    editor,stack,composition=_resource_editor(tmp_path);a,b=composition.layers[:2]
    canvas=editor.composition_canvas;canvas.resize(640,480)
    before=a.value('position',0)
    editor._gizmo_change('position',[20,0],False)
    editor.controller.select_layer(b.id)
    editor._gizmo_change('position',[22,0],True)
    moved=canvas.preview_image()[0].copy()
    assert a.value('position',0)==[22,0] and b.value('position',0)==[0,0]
    stack.undo();assert a.value('position',0)==before
    assert canvas.preview_image()[0]!=moved
    stack.redo();assert a.value('position',0)==[22,0]
    assert canvas.preview_image()[0]==moved
    editor.close()

def test_multi_transform_parent_child_overscan_roots(tmp_path):
    from tests.test_multi_transform_workflow import _resource_editor
    from PySide6.QtCore import Qt
    editor,stack,composition=_resource_editor(tmp_path);a,b=composition.layers[:2]
    b.parent_id=a.id;b.add_property('position').default_value=[4,0]
    child_before=deepcopy(b.tracks);offset=b.parent_offset
    editor.select_layer_with_modifiers(a.id);editor.select_layer_with_modifiers(b.id,Qt.KeyboardModifier.ControlModifier)
    editor._multi_gizmo_change('position',(20,0),False);editor._multi_gizmo_change('position',(20,0),True)
    assert b.tracks==child_before and b.parent_offset==offset
    canvas=editor.composition_canvas;canvas.resize(640,480)
    assert canvas.selection_polygon_comp(a).boundingRect().left()>32
    assert canvas.selection_polygon_comp(b).boundingRect().left()>32
    assert canvas.preview_image()[0].pixelColor(0,0).alpha()==0
    stack.undo();assert a.value('position',0)==[0,0] and b.tracks==child_before
    stack.redo();assert a.value('position',0)==[20,0]
    editor.close()

def test_overscan_hit_test_cache_zoom_pan_and_no_model_mutation(monkeypatch):
    project,composition,layer=scene();layer.add_property('position').default_value=[18,0]
    canvas=CompositionCanvas();canvas.resize(640,480);canvas.set_context(project,composition,layer,0)
    before=deepcopy(project.to_dict());image,region=canvas.preview_image()
    assert image.pixelColor(int(32-region[0]),int(14-region[1])).alpha()>0
    assert canvas._hit_layer(QPointF(32,14)) is layer
    import app.ui.resource_editor_v2.composition_canvas as module
    original=module.render_editor_region
    monkeypatch.setattr(module,'render_editor_region',lambda *a:pytest.fail('hover repaint rebuilt preview'))
    assert canvas.preview_image()[0] is image
    canvas.grab();canvas.grab()
    monkeypatch.setattr(module,'render_editor_region',original)
    for zoom in (1,8,32):
        canvas.zoom=zoom;canvas.pan=QPointF(17,-23)
        point=canvas.to_widget(QPointF(28,28))
        assert point==canvas.output_frame_rect().bottomRight()
        image,region=canvas.preview_image()
        assert image.width()<=canvas.width()+2 and image.height()<=canvas.height()+2
    assert project.to_dict()==before
    layer.add_property('position').default_value=[-18,0]
    canvas.set_context(project,composition,layer,0)
    assert canvas._hit_layer(QPointF(-4,14)) is layer
    canvas.close()

def test_group_solo_visibility_temporal_and_lock():
    project,composition,layer=scene();layer.add_property('position').default_value=[18,0]
    layer.locked=True
    region=(-28,-28,84,84)
    assert render_editor_region(project,composition,0,region)[...,3].any()
    layer.start_frame=1
    assert not render_editor_region(project,composition,0,region).any()
    layer.start_frame=0
    group=LayerGroup('G',children=[layer.id],visible=False)
    composition.groups=[group];composition.root_order=[group_node(group.id)]
    assert not render_editor_region(project,composition,0,region).any()
    group.visible=True;group.solo=True
    assert render_editor_region(project,composition,0,region)[...,3].any()
    canvas=CompositionCanvas();canvas.set_context(project,composition,None,0)
    assert canvas._hit_layer(QPointF(32,14)) is layer
    group.visible=False
    assert canvas._hit_layer(QPointF(32,14)) is None

@pytest.mark.parametrize('count',[10,50,100])
def test_viewport_bounded_render_and_warm_paint_profile(count,capsys):
    project,composition,layer=scene()
    for index in range(1,count):
        other=deepcopy(layer);other.id=f'layer-{index}'
        other.add_property('position').default_value=[100000 if index%3==0 else 18 if index%3==1 else 0,0]
        if index%2:other.add_property('rotation_x').default_value=25
        composition.layers.append(other)
    canvas=CompositionCanvas();canvas.resize(640,480);canvas.set_context(project,composition,layer,0)
    start=perf_counter();image,region=canvas.preview_image();rebuild=(perf_counter()-start)*1000
    start=perf_counter()
    for _ in range(10):canvas.grab()
    paint=(perf_counter()-start)*100
    layer.add_property('position').default_value=[-18,0]
    start=perf_counter();canvas.set_context(project,composition,layer,0);canvas.preview_image();update=(perf_counter()-start)*1000
    assert image.width()*image.height()<=640*480
    with capsys.disabled():print(f'OVERSCAN {count}: rebuild={rebuild:.2f}ms warm-paint={paint:.2f}ms update={update:.2f}ms region={region}')
    canvas.close()
