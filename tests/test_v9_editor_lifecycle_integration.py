"""Offscreen editor-state integration for the v9 production workflow."""

from __future__ import annotations

from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
from PySide6.QtCore import QPointF,QSettings
from PySide6.QtWidgets import QApplication,QFileDialog

from app.services import effect_resource_layer_render_service,particle_render_service,resource_composition_render_service
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame
from app.services.project_io import save_project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow
from tests.test_v9_integrated_workflow import production_project


APP=QApplication.instance() or QApplication([])


def window_for(tmp_path,project,name="window"):
    settings=QSettings(str(tmp_path/f"{name}.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language","en")
    value=MainWindow(ShortcutSettingsService(settings),project);value.dirty=False;value._non_undo_dirty=False;value.application_undo_stack.setClean()
    return value


def finish(window):
    window.set_playing(False);window.dirty=False;window._non_undo_dirty=False;window.close();APP.processEvents()


def select_resource_layer_editor(window,composition,layer):
    editor=window.resource_editor;editor.refresh(window.project);editor.controller.select_composition(composition.id,layer.id);editor._apply_state(editor.controller.state)
    return editor


def test_ui_navigation_state_does_not_dirty_project(tmp_path):
    project,_,composition,resource_layer,effect=production_project(tmp_path,"orbit",animated=True);window=window_for(tmp_path,project)
    editor=select_resource_layer_editor(window,composition,resource_layer);generation=window.effect_playback.generation
    render_stats=dict(particle_render_service.PARTICLE_RENDER_STATS);before=project.to_dict()
    editor.composition_canvas.zoom=2.0;editor.composition_canvas.pan_offset=QPointF(17,-9);editor.controller.set_frame(8);editor._apply_state(editor.controller.state)
    window.select_resource_layer(effect.id);panel=window.particle_properties.transform_panel
    panel.set_advanced_expanded(True);panel.set_advanced_expanded(False);window.canvas.zoom=1.5;window.canvas.pan_offset=QPointF(-12,7);APP.processEvents()
    assert not window.dirty and not window._non_undo_dirty
    assert window.effect_playback.generation==generation and particle_render_service.PARTICLE_RENDER_STATS==render_stats
    assert project.to_dict()==before
    finish(window)


def test_undo_redo_across_resource_and_effect_edits(tmp_path):
    project,_,composition,resource_layer,effect=production_project(tmp_path,"helix",animated=True);window=window_for(tmp_path,project)
    editor=select_resource_layer_editor(window,composition,resource_layer);editor.add_property_to_layer("rotation_x");stack=window.application_undo_stack;stack.clear();window._non_undo_dirty=False;window.dirty=False;stack.setClean()
    editor._property_value("rotation_x",32);assert resource_layer.value("rotation_x",0)==32
    system=deepcopy(effect.layer_space_transform);system.position_x=11;system.rotation_y=-24;system.revision+=1
    window.update_resource_layer_transform(effect.id,system);assert effect.layer_space_transform.position_x==11
    assert stack.count()==2 and window.dirty
    stack.undo();assert effect.layer_space_transform.position_x==0 and resource_layer.value("rotation_x",0)==32
    stack.undo();assert resource_layer.value("rotation_x",0)==0 and not window.dirty
    stack.redo();stack.redo();assert resource_layer.value("rotation_x",0)==32 and effect.layer_space_transform.rotation_y==-24
    finish(window)


def test_project_switch_does_not_reuse_stale_render_cache(tmp_path,monkeypatch):
    project_a,_,_,_,_=production_project(tmp_path,"orbit",animated=True);project_a.name="Project A"
    project_b,_,composition_b,resource_b,effect_b=production_project(tmp_path,"helix",animated=True);project_b.name="Project B"
    resource_b.add_property("rotation_y").set_keyframe(0,48);composition_b.touch();effect_b.layer_space_transform.position_x=13;effect_b.layer_space_transform.revision+=1
    path_a=save_project(project_a,tmp_path/"project-a");path_b=save_project(project_b,tmp_path/"project-b")
    window=window_for(tmp_path,project_a,"switch");paths=iter([str(path_b),str(path_a)]*10)
    monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args:(next(paths),""))
    for index in range(20):
        window.open_project();expected_name="Project B" if index%2==0 else "Project A"
        assert window.project.name==expected_name and len(window.effect_playback.cache)==0
        layer=window.project.effect_resource_layers[0];exact=render_exact_playback_frame(window.project,5)[0]
        window.select_frame(5);assert np.array_equal(window.canvas._compose_display_frame(),exact)
        effect_resource_layer_render_service.render_effect_resource_layer(window.project,layer)
        assert all(key[0]==layer.id for key in effect_resource_layer_render_service._TRANSFORM_CACHE)
    assert resource_composition_render_service._CACHE
    finish(window)


def test_new_project_clears_all_render_and_transient_state(tmp_path):
    project,_,_,_,_=production_project(tmp_path,"orbit",animated=True);window=window_for(tmp_path,project,"new")
    window.set_playing(True);APP.processEvents();window.canvas.pan_offset=QPointF(3,4)
    from app.ui.new_project_dialog import NewProjectSettings
    window.apply_new_project_settings(NewProjectSettings("Clean",32,32,12,True,12))
    assert window.project.name=="Clean" and not window.play_timer.isActive() and len(window.effect_playback.cache)==0
    assert window.canvas.playback_pixmap is None and window.canvas.interactive_transform_proxy is None
    assert not effect_resource_layer_render_service._BASE_CACHE and not effect_resource_layer_render_service._TRANSFORM_CACHE
    finish(window)
