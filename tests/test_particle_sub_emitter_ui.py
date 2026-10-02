from copy import deepcopy
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from app.models.particle_emitter import ParticleSubEmitterEventSettings as Event
from app.services.settings_service import ShortcutSettingsService
from app.services.localization_service import LocalizationService
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer,render_effect_resource_layer_current_frame
from app.services.particle_sub_emitter_service import validate_project_sub_emitters
from app.ui.main_window import MainWindow
from tests.test_particle_sub_emitter import setup
from tests.test_particle_scale_over_lifetime import _close

APP=QApplication.instance() or QApplication([])


def window(tmp_path,kind="none"):
    project,parent,target=setup(kind,speed_min=2,speed_max=2)
    other=deepcopy(target);other.id="other";other.name=target.name;project.effect_resource_layers.append(other)
    parent.particle_settings.birth_sub_emitter.target_layer_id=target.id
    parent.particle_settings.death_sub_emitter.target_layer_id=target.id
    project.repair_effect_hierarchy()
    for item in project.effect_resource_layers:apply_effect_resource_layer(project,item)
    win=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"sub.ini"),QSettings.Format.IniFormat)),project)
    win.select_resource_layer(parent.id);win.application_undo_stack.clear();win.application_undo_stack.setClean();win.dirty=False;win._non_undo_dirty=False
    return win,parent,target,other


@pytest.mark.parametrize("field,value",[("birth_sub_enabled",True),("death_sub_enabled",True),("birth_sub_target","other"),("death_sub_target","other")])
def test_four_accepted_actions_one_undo_redo_exact(tmp_path,field,value):
    win,parent,target,other=window(tmp_path,"both" if "target" in field else "none")
    before=deepcopy(parent.particle_settings);control=getattr(win.particle_properties,field)
    if "enabled" in field:control.setChecked(value)
    else:control.setCurrentIndex(control.findData(value))
    APP.processEvents();after=deepcopy(parent.particle_settings)
    assert after!=before and win.application_undo_stack.count()==1 and after.motion.tracks=={}
    win.application_undo_stack.undo();assert parent.particle_settings==before
    win.application_undo_stack.redo();assert parent.particle_settings==after
    _close(win)


def test_combo_filter_id_disabled_preservation_and_refresh_noop(tmp_path):
    win,parent,target,other=window(tmp_path)
    panel=win.particle_properties
    before=deepcopy(parent.particle_settings);revision=win._project_edit_revision
    ids={panel.birth_sub_target.itemData(i) for i in range(panel.birth_sub_target.count())}
    assert ids=={None,target.id,other.id} and parent.id not in ids
    assert not panel.birth_sub_target.isEnabled() and panel.birth_sub_target.currentData()==target.id
    assert panel.birth_sub_target.itemText(1)!=panel.birth_sub_target.itemText(2)
    for language in ("ko","en","ko"):
        localization=LocalizationService(QSettings(str(tmp_path/"language.ini"),QSettings.Format.IniFormat));localization.set_language(language)
        panel.retranslate_ui(localization);panel.set_resource_layer(other,win.project);panel.set_resource_layer(parent,win.project);panel.set_settings(before)
        assert panel.settings()==before
        assert panel.sub_form.labelForField(panel.death_sub_target).text() and "L-1" in panel.death_sub_target.toolTip()
    panel.birth_sub_target.setCurrentIndex(panel.birth_sub_target.findData(target.id))
    assert win.application_undo_stack.count()==0 and not win.dirty and win._project_edit_revision==revision
    _close(win)


@pytest.mark.parametrize("bad",[None,"parent","missing"])
def test_invalid_target_revert_no_undo_dirty_revision(tmp_path,bad):
    win,parent,target,other=window(tmp_path,"both")
    before=deepcopy(parent.particle_settings);revision=win._project_edit_revision;panel=win.particle_properties
    if bad is None:index=0
    else:panel.birth_sub_target.addItem("bad",bad);index=panel.birth_sub_target.count()-1
    panel.birth_sub_target.setCurrentIndex(index)
    assert parent.particle_settings==before and win.application_undo_stack.count()==0 and not win.dirty and win._project_edit_revision==revision
    assert panel.birth_sub_target.currentData()==target.id and panel.sub_status.text()
    _close(win)


def test_enable_requires_target_and_combined_budget_rejected(tmp_path):
    win,parent,target,other=window(tmp_path)
    parent.particle_settings.birth_sub_emitter.target_layer_id=None;win.particle_properties.set_settings(parent.particle_settings)
    win.particle_properties.birth_sub_enabled.setChecked(True)
    assert not parent.particle_settings.birth_sub_emitter.enabled and win.application_undo_stack.count()==0 and not win.dirty
    parent.particle_settings.birth_sub_emitter.target_layer_id=target.id
    target.particle_settings.particle_count_min=target.particle_settings.particle_count_max=4096
    win.particle_properties.set_settings(parent.particle_settings);win.particle_properties.birth_sub_enabled.setChecked(True)
    assert not parent.particle_settings.birth_sub_emitter.enabled and "4096" in win.particle_properties.sub_status.text()
    assert win.application_undo_stack.count()==0 and not win.dirty
    _close(win)


def test_default_off_none_has_reachable_runtime_target_selection_flow(tmp_path):
    win,parent,target,other=window(tmp_path)
    parent.particle_settings.birth_sub_emitter=Event();win.particle_properties.set_settings(parent.particle_settings)
    panel=win.particle_properties;revision=win._project_edit_revision
    assert not panel.birth_sub_target.isEnabled()
    panel.birth_sub_enabled.setChecked(True)
    assert panel.birth_sub_target.isEnabled() and parent.particle_settings.birth_sub_emitter==Event()
    assert win.application_undo_stack.count()==0 and not win.dirty and win._project_edit_revision==revision
    panel.birth_sub_target.setCurrentIndex(panel.birth_sub_target.findData(target.id))
    assert parent.particle_settings.birth_sub_emitter==Event(True,target.id) and win.application_undo_stack.count()==1
    win.application_undo_stack.undo();assert parent.particle_settings.birth_sub_emitter==Event()
    assert not panel.birth_sub_target.isEnabled()
    _close(win)


def test_target_delete_single_transaction_and_undo_restores_references(tmp_path):
    win,parent,target,other=window(tmp_path,"both")
    win.select_resource_layer(target.id)
    assert win.delete_selected_effect_layers()
    survivor=next(item for item in win.project.effect_resource_layers if item.id==parent.id)
    assert survivor.particle_settings.birth_sub_emitter==Event() and survivor.particle_settings.death_sub_emitter==Event()
    for frame in (0,5,8,23):assert np.array_equal(win.project.frames[frame].layer_pixels[survivor.generated_layer_id],render_effect_resource_layer_current_frame(win.project,survivor,frame))
    assert win.application_undo_stack.count()==1
    win.application_undo_stack.undo()
    restored=next(item for item in win.project.effect_resource_layers if item.id==parent.id)
    assert restored.particle_settings.birth_sub_emitter==Event(True,target.id)
    assert restored.particle_settings.death_sub_emitter==Event(True,target.id)
    validate_project_sub_emitters(win.project)
    win.application_undo_stack.redo();validate_project_sub_emitters(win.project)
    _close(win)


@pytest.mark.parametrize("which",["parent","target"])
def test_duplicate_new_id_and_existing_references_unchanged(tmp_path,which):
    win,parent,target,other=window(tmp_path,"both")
    original=parent if which=="parent" else target;win.select_resource_layer(original.id)
    duplicates=win.duplicate_selected_effect_layers();assert len(duplicates)==1 and duplicates[0].id!=original.id
    assert parent.particle_settings.birth_sub_emitter.target_layer_id==target.id
    if which=="parent":assert duplicates[0].particle_settings.death_sub_emitter.target_layer_id==target.id
    _close(win)


def test_target_setting_change_regenerates_parent_and_rename_display_only_ref(tmp_path):
    win,parent,target,other=window(tmp_path,"both")
    before=win.project.frames[8].layer_pixels[parent.generated_layer_id].copy()
    after=deepcopy(target.particle_settings);after.speed_min=after.speed_max=3
    win.update_particle_draft(target.id,after)
    assert not np.array_equal(before,win.project.frames[8].layer_pixels[parent.generated_layer_id])
    assert np.array_equal(win.project.frames[8].layer_pixels[parent.generated_layer_id],render_effect_resource_layer_current_frame(win.project,parent,8))
    reference=deepcopy(parent.particle_settings.birth_sub_emitter)
    win.rename_resource_layer(target.id,"Renamed")
    win.particle_properties.set_resource_layer(parent,win.project)
    index=win.particle_properties.birth_sub_target.findData(target.id)
    assert "Renamed" in win.particle_properties.birth_sub_target.itemText(index) and parent.particle_settings.birth_sub_emitter==reference
    _close(win)


def test_preview_snapshot_contains_read_only_templates(tmp_path):
    from app.services.particle_preview_service import ParticlePreviewSnapshot,render_particle_snapshot
    win,parent,target,other=window(tmp_path,"both")
    snapshot=ParticlePreviewSnapshot.from_project(win.project,parent.id,1,parent.particle_settings)
    assert snapshot.resource is not win.project
    frames=render_particle_snapshot(snapshot)
    for t in (0,5,8,23):assert np.array_equal(frames[t],render_effect_resource_layer_current_frame(win.project,parent,t))
    _close(win)


def test_a_b_target_sentinels_selection_language_scrub_and_disabled_state(tmp_path):
    win,parent,target,other=window(tmp_path,"none")
    parent.particle_settings.birth_sub_emitter=Event(True,target.id)
    parent.particle_settings.death_sub_emitter=Event(False,other.id)
    b=deepcopy(parent);b.id="parent-b";b.generated_layer_id=None
    z=deepcopy(target);z.id="z";z.generated_layer_id=None
    w=deepcopy(target);w.id="w";w.generated_layer_id=None
    b.particle_settings.birth_sub_emitter=Event(False,z.id);b.particle_settings.death_sub_emitter=Event(True,w.id)
    win.project.effect_resource_layers.extend((b,z,w));win.project.repair_effect_hierarchy()
    before_a=deepcopy(parent.particle_settings);before_b=deepcopy(b.particle_settings)
    revision=win._project_edit_revision
    panel=win.particle_properties
    for language in ("ko","en","ko"):
        localization=LocalizationService(QSettings(str(tmp_path/"sentinel.ini"),QSettings.Format.IniFormat));localization.set_language(language)
        panel.retranslate_ui(localization)
        panel.set_resource_layer(b,win.project);assert panel.settings()==before_b
        assert not panel.birth_sub_target.isEnabled() and panel.death_sub_target.isEnabled()
        panel.set_resource_layer(parent,win.project);panel._set_motion_frame(parent.particle_settings.motion,6)
        assert panel.settings()==before_a and panel.birth_sub_target.isEnabled() and not panel.death_sub_target.isEnabled()
    assert win.application_undo_stack.count()==0 and not win.dirty and win._project_edit_revision==revision
    _close(win)


@pytest.mark.parametrize("language",["ko","en"])
@pytest.mark.parametrize("width,factor",[(280,1.0),(300,1.5)])
def test_compact_sub_group_localized_layout(tmp_path,language,width,factor):
    win,parent,target,other=window(tmp_path,"both");panel=win.particle_properties
    localization=LocalizationService(QSettings(str(tmp_path/"compact.ini"),QSettings.Format.IniFormat));localization.set_language(language);panel.retranslate_ui(localization)
    group=panel.sub_group;font=group.font();font.setPointSizeF(font.pointSizeF()*factor);group.setFont(font);group.setFixedWidth(width);group.show();group.layout().activate();APP.processEvents()
    assert panel.layout.indexOf(panel.trail_group)<panel.layout.indexOf(group)<panel.layout.indexOf(panel.lifetime_group)
    for control in (panel.birth_sub_enabled,panel.birth_sub_target,panel.death_sub_enabled,panel.death_sub_target):
        label=panel.sub_form.labelForField(control)
        assert label.fontMetrics().horizontalAdvance(label.text())<=label.width()
        assert control.geometry().right()<width and control.toolTip()
    _close(win)
