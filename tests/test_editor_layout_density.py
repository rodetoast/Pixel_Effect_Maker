import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFrame

from app.ui.layout_metrics import (
    COMPACT_TOOL_BUTTON_SIZE,
    EFFECT_INSPECTOR_MIN_WIDTH,
    EFFECT_LIBRARY_MIN_WIDTH,
    EFFECT_TIMELINE_MIN_HEIGHT,
    HIERARCHY_LABEL_WIDTH,
    RESOURCE_BROWSER_MIN_WIDTH,
    RESOURCE_INSPECTOR_MIN_WIDTH,
    RESOURCE_TIMELINE_MIN_HEIGHT,
)
from app.ui.resource_editor_v2.composition_inspector import LayerInspector
from app.ui.resource_editor_v2.composition_timeline import CompositionTimeline
from app.ui.resource_editor_v2.resource_editor_widget import ResourceEditorWidget
from app.ui.timeline_widget import TimelineWidget


APP = QApplication.instance() or QApplication([])


class _Localization:
    language = "en"

    @staticmethod
    def text(key):
        return key


def test_shared_layout_metrics_keep_both_workspaces_readable():
    assert 180 <= RESOURCE_BROWSER_MIN_WIDTH <= 220
    assert 280 <= RESOURCE_INSPECTOR_MIN_WIDTH <= 340
    assert 220 <= EFFECT_LIBRARY_MIN_WIDTH <= 280
    assert 300 <= EFFECT_INSPECTOR_MIN_WIDTH <= 360
    assert HIERARCHY_LABEL_WIDTH >= 200
    assert RESOURCE_TIMELINE_MIN_HEIGHT >= 150
    assert EFFECT_TIMELINE_MIN_HEIGHT >= 180


def test_resource_editor_uses_flexible_center_and_protected_side_panels(tmp_path):
    settings=QSettings(str(tmp_path/"layout.ini"),QSettings.Format.IniFormat)
    editor=ResourceEditorWidget(settings);editor.resize(1280,720);editor.show();APP.processEvents();editor._restore_splitters();APP.processEvents()
    sizes=editor.splitter.sizes()
    assert sizes[0] >= RESOURCE_BROWSER_MIN_WIDTH
    assert sizes[1] > sizes[0]
    assert sizes[2] >= RESOURCE_INSPECTOR_MIN_WIDTH
    assert editor.composition_timeline.minimumHeight() == RESOURCE_TIMELINE_MIN_HEIGHT
    editor.close()


def test_resource_timeline_groups_controls_and_exposes_compact_actions():
    timeline=CompositionTimeline();timeline.retranslate(_Localization())
    separators=timeline.findChildren(QFrame)
    assert sum(item.frameShape()==QFrame.Shape.VLine for item in separators) >= 3
    for button in (timeline.lock_layer,timeline.solo_layer,timeline.move_up,timeline.move_down):
        assert button.width()==COMPACT_TOOL_BUTTON_SIZE
        assert button.height()==COMPACT_TOOL_BUTTON_SIZE
        assert button.accessibleName()
        assert button.accessibleDescription()
    assert timeline.table.verticalHeader().minimumWidth()==HIERARCHY_LABEL_WIDTH


def test_inspector_transform_grid_is_uniform_and_scroll_safe():
    inspector=LayerInspector()
    heights={button.minimumHeight() for button in inspector.mode_buttons.values()}
    assert heights=={32}
    assert inspector.horizontalScrollBarPolicy().name=="ScrollBarAlwaysOff"


def test_effect_timeline_uses_common_hierarchy_density():
    timeline=TimelineWidget();timeline.set_frame_cell_width(36)
    timeline.table.setColumnCount(timeline.FRAME_COLUMN_OFFSET+1)
    timeline.set_frame_cell_width(36)
    assert timeline.table.columnWidth(timeline.NAME_COLUMN)==HIERARCHY_LABEL_WIDTH
    assert timeline.table.minimumHeight()==EFFECT_TIMELINE_MIN_HEIGHT
