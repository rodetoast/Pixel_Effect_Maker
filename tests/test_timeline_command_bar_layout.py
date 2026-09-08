from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings,Qt
from PySide6.QtWidgets import QApplication,QWidget

from app.services.localization_service import LocalizationService
from app.ui.resource_editor_v2.composition_timeline import CompositionTimeline
from app.ui.timeline_command_bar import InactiveTimelineTable
from app.ui.timeline_widget import TimelineWidget


APP = QApplication.instance() or QApplication([])


def _localization(tmp_path, language):
    settings=QSettings(str(tmp_path/f"command-bar-{language}.ini"),QSettings.Format.IniFormat)
    service=LocalizationService(settings,language);service.set_language(language);return service


def test_resource_command_bar_has_semantic_group_order_and_two_rows():
    timeline=CompositionTimeline()
    assert list(timeline.timeline_command_groups)==["playback","key_navigation","view","assist","key_editing"]
    assert list(timeline.layer_command_groups)==["layer","hierarchy","state","order"]
    assert timeline.timeline_command_bar.objectName()=="resourceTimelineCommandBar"
    assert timeline.layer_command_bar.objectName()=="resourceLayerCommandBar"
    assert timeline.snap_toggle.property("commandGroup")=="assist"
    assert timeline.delete_keyframe.property("commandGroup")=="key_editing"


def test_effect_command_bar_separates_timeline_from_frame_and_layer_structure():
    timeline=TimelineWidget()
    assert list(timeline.timeline_command_groups)==["playback","key_navigation","view","assist"]
    assert list(timeline.structure_command_groups)==["frame_structure","layer_structure"]
    assert timeline.snap_toggle.property("commandGroup")=="assist"
    assert all(button.property("commandGroup")=="frame_structure" for button in timeline.edit_buttons[:3])
    assert all(button.property("commandGroup")=="layer_structure" for button in timeline.edit_buttons[3:])


@pytest.mark.parametrize("language",("en","ko"))
@pytest.mark.parametrize("timeline_type",(TimelineWidget,CompositionTimeline))
def test_fit_labels_are_understandable_and_glyph_buttons_are_accessible(tmp_path,language,timeline_type):
    timeline=timeline_type();localization=_localization(tmp_path,language)
    (timeline.retranslate_ui(localization) if isinstance(timeline,TimelineWidget) else timeline.retranslate(localization))
    labels=[timeline.fit_timeline_button.text(),timeline.fit_keys_button.text(),timeline.fit_selected_button.text()]
    assert not {"Fit","Keys","Sel"}&set(labels)
    assert all(labels) and all(button.accessibleName() for button in (timeline.previous_key,timeline.next_key))
    assert timeline.snap_toggle.accessibleName() and timeline.snap_toggle.accessibleDescription()


@pytest.mark.parametrize("width",(1280,1600,1920))
@pytest.mark.parametrize("timeline_type",(TimelineWidget,CompositionTimeline))
def test_command_bars_do_not_overlap_or_clip_essential_controls(width,timeline_type):
    timeline=timeline_type();timeline.resize(width,360);timeline.show();APP.processEvents()
    bars=[timeline.timeline_command_bar,timeline.structure_command_bar] if isinstance(timeline,TimelineWidget) else [timeline.timeline_command_bar,timeline.layer_command_bar]
    for bar in bars:
        groups=[child for child in bar.findChildren(QWidget,options=Qt.FindChildOption.FindDirectChildrenOnly) if child.property("commandGroup")]
        ordered=sorted(groups,key=lambda group:group.geometry().left())
        assert all(group.geometry().left()>=0 and group.geometry().width()>0 for group in ordered)
        assert all(left.geometry().right()<right.geometry().left() for left,right in zip(ordered,ordered[1:]))
    for button in (timeline.previous_key,timeline.next_key,timeline.fit_timeline_button,timeline.fit_keys_button,timeline.fit_selected_button,timeline.snap_toggle):
        assert button.width()>=button.fontMetrics().horizontalAdvance(button.text())+12
    timeline.close()


def test_inactive_timeline_area_is_one_rect_after_duration():
    table=InactiveTimelineTable();table.setRowCount(2);table.setColumnCount(3)
    for column in range(3):table.setColumnWidth(column,40)
    table.resize(420,180);table.show();APP.processEvents();inactive=table.inactive_area_rect()
    assert inactive.width()>0 and inactive.left()>=sum(table.columnWidth(column) for column in range(3))-table.horizontalScrollBar().value()-2
    assert table.inactive_paint_complexity()=="one-rect-plus-visible-rows"
    assert table.property("outsideDurationTreatment")=="inactive" and table.horizontalHeader().autoFillBackground()
    table.close()
