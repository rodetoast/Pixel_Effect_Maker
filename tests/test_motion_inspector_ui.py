from __future__ import annotations

from PySide6.QtCore import QSettings

from app.services.localization_service import LocalizationService
from app.ui.particle_properties_panel import ParticlePropertiesPanel


def panel(tmp_path,language):
    settings=QSettings(str(tmp_path/f"{language}.ini"),QSettings.Format.IniFormat);settings.setValue("ui/language",language)
    localization=LocalizationService(settings,system_locale="en_US");widget=ParticlePropertiesPanel();widget.retranslate_ui(localization);return widget


def test_motion_mode_and_direction_labels_are_localized(tmp_path):
    english=panel(tmp_path,"en");korean=panel(tmp_path,"ko")
    assert [english.motion_mode.itemText(i) for i in range(3)]==["Linear","Orbit","Helix"]
    assert [korean.motion_mode.itemText(i) for i in range(3)]==["직선","궤도","나선"]
    assert [english.motion_direction.itemText(i) for i in range(2)]==["Clockwise","Counter-clockwise"]
    assert [korean.motion_direction.itemText(i) for i in range(2)]==["시계 방향","반시계 방향"]
    assert english.motion_mode.itemData(0)==korean.motion_mode.itemData(0)=="linear"


def test_internal_property_ids_are_not_user_visible(tmp_path):
    widget=panel(tmp_path,"ko")
    visible=[widget.motion_keyframe_property.itemText(i) for i in range(widget.motion_keyframe_property.count())]
    assert not any("_" in text or text in {"center_x","counter_clockwise","helix"} for text in visible)


def test_motion_mode_groups_show_only_relevant_fields(tmp_path):
    widget=panel(tmp_path,"en")
    widget.motion_mode.setCurrentIndex(widget.motion_mode.findData("linear"));widget._update_motion_visibility()
    assert widget.motion_basic_group.isVisibleTo(widget) and not widget.motion_center_group.isVisibleTo(widget) and not widget.motion_helix_group.isVisibleTo(widget)
    widget.motion_mode.setCurrentIndex(widget.motion_mode.findData("orbit"));widget._update_motion_visibility()
    assert widget.motion_center_group.isVisibleTo(widget) and widget.motion_shape_group.isVisibleTo(widget) and not widget.motion_helix_group.isVisibleTo(widget)
    widget.motion_mode.setCurrentIndex(widget.motion_mode.findData("helix"));widget._update_motion_visibility()
    assert widget.motion_center_group.isVisibleTo(widget) and widget.motion_shape_group.isVisibleTo(widget) and widget.motion_helix_group.isVisibleTo(widget)


def test_motion_labels_do_not_character_wrap_and_properties_have_help(tmp_path):
    widget=panel(tmp_path,"ko")
    motion_groups=(widget.motion_basic_group,widget.motion_center_group,widget.motion_shape_group,widget.motion_helix_group,widget.motion_easing_group,widget.motion_advanced_group)
    for group in motion_groups:
        form=group.layout()
        for row in range(form.rowCount()):
            item=form.itemAt(row,form.ItemRole.LabelRole)
            if item and item.widget():assert not item.widget().wordWrap() and item.widget().minimumWidth()>=130
    for control in (widget.motion_center_x,widget.motion_radius_start,widget.motion_radius_end,widget.motion_ellipse_x,widget.motion_turns,widget.motion_direction,widget.motion_phase_spread,widget.motion_plane_rotation,widget.motion_helix_axis,widget.motion_axis_start,widget.motion_perspective):assert control.toolTip().strip()
    assert widget.motion_start_angle.suffix()=="°" and widget.motion_turns.suffix().strip()=="회"
