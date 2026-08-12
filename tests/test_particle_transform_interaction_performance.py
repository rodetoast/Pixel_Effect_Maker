import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.models.project import Project
from app.models.resource_composition import ResourceComposition
from app.services import effect_resource_layer_render_service as render_service
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])


def _particle_context():
    project = Project.create_default(width=32, height=32)
    composition = ResourceComposition("Particle Base", width=8, height=8, frame_count=3)
    project.resource_compositions.append(composition)
    layer = EffectResourceLayer("Sparks", composition.id, placement_mode=PLACEMENT_PARTICLE, end_frame=2)
    project.effect_resource_layers.append(layer)
    return project, layer


def test_transform_direct_render_avoids_full_sequence_and_invalidates_layer_space_sequence(monkeypatch):
    project, layer = _particle_context(); render_service.invalidate_effect_resource_layer_base()
    original = render_service.render_particle_frames; calls = []
    def counted(*args, **kwargs):
        calls.append(1); return original(*args, **kwargs)
    monkeypatch.setattr(render_service, "render_particle_frames", counted)
    render_service.apply_effect_resource_layer(project, layer)
    assert len(calls) == 1
    base = render_service.render_effect_resource_layer_base(project, layer)
    for value in range(20):
        layer.layer_transform.rotation_y = value; layer.layer_transform.revision += 1
        render_service.apply_effect_resource_layer_current_frame(project, layer, 0)
    assert len(calls) == 1
    rebuilt=render_service.render_effect_resource_layer_base(project,layer)
    assert len(calls)==2 and rebuilt is not base
    layer.particle_settings.seed += 1
    render_service.invalidate_effect_resource_layer_base(layer.id)
    render_service.apply_effect_resource_layer(project, layer)
    assert len(calls) == 3
    render_service.invalidate_effect_resource_layer_base()


def test_current_transform_renders_one_frame_and_only_selected_layer(monkeypatch):
    project, first = _particle_context(); second = EffectResourceLayer("Smoke",first.resource_composition_id,placement_mode=PLACEMENT_PARTICLE,end_frame=2);project.effect_resource_layers.append(second)
    render_service.invalidate_effect_resource_layer_base();render_service.apply_effect_resource_layer(project,first);render_service.apply_effect_resource_layer(project,second)
    first_base=render_service.render_effect_resource_layer_base(project,first);second_base=render_service.render_effect_resource_layer_base(project,second)
    calls=[];original=render_service.transform_rgba_frame
    monkeypatch.setattr(render_service,"transform_rgba_frame",lambda *args,**kwargs:calls.append(args[2]) or original(*args,**kwargs))
    first.layer_transform.rotation_x=30;first.layer_transform.revision+=1
    render_service.apply_effect_resource_layer_current_frame(project,first,0)
    assert calls==[0]
    assert render_service.render_effect_resource_layer_base(project,first) is not first_base
    assert render_service.render_effect_resource_layer_base(project,second) is second_base
    render_service.invalidate_effect_resource_layer_base(first.id)
    assert render_service.render_effect_resource_layer_base(project,second) is second_base
    render_service.invalidate_effect_resource_layer_base()


def test_transform_timer_is_latest_wins_and_rejects_stale_revision(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(ShortcutSettingsService(settings)); composition = ResourceComposition("R", width=8, height=8, frame_count=2)
    window.project.resource_compositions.append(composition); layer = window.create_resource_layer_from_resource(composition.id, PLACEMENT_PARTICLE)
    generated = next(item for item in window.project.layers if item.id == layer.generated_layer_id)
    current_calls = []; final_calls = []
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer_current_frame", lambda project,item,frame: current_calls.append((item.layer_transform.revision,item.layer_transform.rotation_y)) or generated)
    monkeypatch.setattr("app.ui.main_window.apply_effect_resource_layer", lambda project,item: final_calls.append(item.layer_transform.revision) or generated)
    for value in range(20):
        layer.layer_transform.rotation_y = value; layer.layer_transform.revision += 1; window._queue_resource_transform_render(layer)
    window.resource_transform_finalize_timer.stop()
    elapsed = 0
    while elapsed < 2000:
        state=window.canvas.interactive_transform_proxy
        if state is not None and state.active and state.last_applied_revision==20:break
        QTest.qWait(10);elapsed+=10
    assert current_calls == [] and final_calls == []
    assert window.canvas.interactive_transform_proxy.last_applied_revision==20
    window._pending_resource_transforms[layer.id] = 19; window._flush_resource_transform_current()
    assert current_calls == []
    installed=window.interactive_gizmo_renderer.collector.final_exact_installs
    window._pending_resource_transforms[layer.id] = 20; window._flush_resource_transform_final()
    elapsed=0
    while elapsed<2000 and window.interactive_gizmo_renderer.collector.final_exact_installs==installed:QTest.qWait(10);elapsed+=10
    assert current_calls == [] and final_calls == []
    window._materialize_resource_transform_sequences()
    assert final_calls == [20]
    window.dirty = False; window._non_undo_dirty = False; window.close()


def test_transform_changes_do_not_rebuild_particle_inspector(tmp_path):
    settings = QSettings(str(tmp_path / "inspector.ini"), QSettings.Format.IniFormat)
    window = MainWindow(ShortcutSettingsService(settings)); composition = ResourceComposition("R",width=8,height=8,frame_count=2)
    window.project.resource_compositions.append(composition);layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE)
    identities=[id(group) for _,group,_,_ in window.particle_properties._group_records]
    for value in range(8):
        layer.layer_transform.position_x=value;layer.layer_transform.revision+=1;window._queue_resource_transform_render(layer)
    QTest.qWait(40)
    assert [id(group) for _,group,_,_ in window.particle_properties._group_records]==identities
    window.resource_transform_finalize_timer.stop();window.dirty=False;window._non_undo_dirty=False;window.close()


def test_particle_resource_layer_display_name_follows_language(tmp_path):
    settings = QSettings(str(tmp_path / "names.ini"), QSettings.Format.IniFormat); settings.setValue("ui/language","en")
    window=MainWindow(ShortcutSettingsService(settings));composition=ResourceComposition("R",width=8,height=8,frame_count=2);window.project.resource_compositions.append(composition)
    layer=window.create_resource_layer_from_resource(composition.id,PLACEMENT_PARTICLE);generated=next(item for item in window.project.layers if item.id==layer.generated_layer_id)
    assert generated.name==f"{layer.name} · Particle Emission" and "Particle System" not in generated.name
    window.localization.set_language("ko");window.retranslate_ui()
    assert generated.name==f"{layer.name} · 파티클 방출"
    window.dirty=False;window._non_undo_dirty=False;window.close()
