"""Closed-window background work must not contaminate later navigation."""
import pytest
from PySide6.QtCore import QThreadPool
from app.services import particle_render_service
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame
from app.ui.main_window import MainWindow
from tests.test_v9_editor_lifecycle_integration import APP, finish, production_project, window_for, test_ui_navigation_state_does_not_dirty_project as navigation_contract


def test_close_cancels_pending_idle_prewarm(tmp_path):
    project,_,_,_,effect=production_project(tmp_path, 'orbit', animated=True)
    window=window_for(tmp_path,project)
    window.select_resource_layer(effect.id)
    manager=window.interactive_proxy_prewarm
    assert manager._pending is not None and manager._timer.isActive()
    try:
        window.play_timer.start(1000);window.resource_editor.timer.start(1000)
        window.close()
        assert manager._pending is None, 'closed window retained idle prewarm request'
        assert not manager._timer.isActive() and not manager._poll.isActive()
        assert not window.play_timer.isActive()
        assert not window.resource_editor.timer.isActive()
    finally:
        manager.cancel();manager._poll.stop();finish(window)
        manager.cancel();manager._poll.stop();window.deleteLater()
        assert QThreadPool.globalInstance().waitForDone(2500)
        APP.processEvents()


def test_closed_window_followed_by_navigation_has_no_late_render(tmp_path,monkeypatch):
    project,_,_,_,effect=production_project(tmp_path, 'orbit', animated=True)
    window=window_for(tmp_path,project,'previous')
    calls=[]
    original=particle_render_service.render_particle_frame
    def observe(project_arg,*args,**kwargs):
        if project_arg is project:calls.append(1)
        return original(project_arg,*args,**kwargs)
    monkeypatch.setattr(particle_render_service,'render_particle_frame',observe)
    try:
        window.select_resource_layer(effect.id)
        # Due at the very next event dispatch, not a wall-clock race.
        window.interactive_proxy_prewarm._timer.start(0)
        window.close()
        navigation_contract(tmp_path)
        assert QThreadPool.globalInstance().waitForDone(2500)
        assert calls==[]
    finally:
        finish(window)


def test_navigation_contract_rejects_unnecessary_render(tmp_path,monkeypatch):
    original=MainWindow.select_resource_layer
    selections=[]
    def inject(window,identifier,*args,**kwargs):
        original(window,identifier,*args,**kwargs)
        selections.append(1)
        if len(selections)==2:
            render_effect_resource_layer_current_frame(window.project,window.project.effect_resource_layers[0],0)
    monkeypatch.setattr(MainWindow,'select_resource_layer',inject)
    with pytest.raises(AssertionError,match='navigation changed particle render statistics'):
        navigation_contract(tmp_path)
