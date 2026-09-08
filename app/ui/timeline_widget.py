"""Integrated layer-by-frame timeline controls."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QRubberBand,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from app.models.project import Project
from app.ui.timeline_scrub_controller import TimelineScrubController
from app.ui.tooltip_helper import apply_tooltip
from app.ui.focus_wheel_widgets import ScrollSafeSpinBox
from app.ui.hierarchy_display import parent_display_labels
from app.ui.layout_metrics import EFFECT_TIMELINE_MAX_HEIGHT, EFFECT_TIMELINE_MIN_HEIGHT, HIERARCHY_LABEL_WIDTH
from app.ui.timeline_multi_key import TimelineKey, TimelineKeySelection, clamp_group_delta, read_timeline_clipboard_payload, timeline_clipboard_matches
from app.ui.timeline_snapping import batch_delta_issue, collect_snap_targets, compute_batch_snap
from app.ui.timeline_time_view import TimelineTimeView,navigation_frame
from app.ui.timeline_command_bar import InactiveTimelineTable,command_group,command_separator


class TimelineWidget(QWidget):
    """Show layers as rows and sequential frame numbers as columns."""

    cell_selected = Signal(int, int)
    cell_selected_with_modifiers=Signal(int,int,object);select_all_layers_requested=Signal()
    add_requested = Signal()
    duplicate_requested = Signal()
    delete_requested = Signal()
    add_layer_requested = Signal()
    delete_layer_requested = Signal()
    delete_layer_context_requested = Signal(int)
    play_requested = Signal()
    fps_changed = Signal(int)
    layer_visibility_requested = Signal(int, bool)
    scrub_started = Signal()
    scrub_finished = Signal()
    multi_key_move_requested=Signal(object,int)
    multi_key_duplicate_requested=Signal(object,int)
    multi_key_delete_requested=Signal(object)
    multi_key_easing_requested=Signal(object,str)
    multi_key_copy_requested=Signal(object)
    multi_key_paste_requested=Signal()
    key_frame_requested=Signal(int)
    VISIBILITY_COLUMN = 0
    NAME_COLUMN = 1
    FRAME_COLUMN_OFFSET = 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self._playing = False
        self._preview = False
        self._display_frame_count = 1
        self._current_frame = 0
        self._play_shortcuts = []
        self._previous_shortcuts = []
        self._next_shortcuts = []
        self.rows=[];self.key_selection=TimelineKeySelection();self._visible_keys=set();self._occupied_keys=set();self.reveal_mode="all";self.snap_enabled=True;self._selected_logical_ids=set();self._primary_logical_id=None;self._time_view=TimelineTimeView();self._time_pan=None;self._key_drag=None;self._marquee=None;self._marquee_origin=None;self._marquee_ctrl=False
        layout = QVBoxLayout(self);layout.setContentsMargins(6,6,6,6);layout.setSpacing(5)
        status_toolbar = QHBoxLayout()
        self.selection_label = QLabel("Layer 1 · Frame 1")
        self.selection_label.setStyleSheet("font-weight: bold;")
        status_toolbar.addWidget(self.selection_label)
        self.playback_status_label = QLabel("Stopped · Frame 1 / 1 · 12 FPS")
        status_toolbar.addWidget(self.playback_status_label)
        status_toolbar.addStretch(1)
        self.previous_key=QPushButton("◆◀");self.next_key=QPushButton("▶◆");self.fit_timeline_button=QPushButton("Fit Timeline");self.fit_keys_button=QPushButton("Fit Visible Keys");self.fit_selected_button=QPushButton("Fit Selected Keys");self.reveal_combo=QComboBox();self.reveal_combo.addItems(["All","Animated","Selected Layer"]);self.snap_toggle=QPushButton("Snap");self.snap_toggle.setCheckable(True);self.snap_toggle.setChecked(True)
        self.previous_key.setFixedWidth(38);self.next_key.setFixedWidth(38);self.fit_timeline_button.setMinimumWidth(76);self.fit_keys_button.setMinimumWidth(96);self.fit_selected_button.setMinimumWidth(104);self.reveal_combo.setMinimumWidth(96);self.snap_toggle.setMinimumWidth(52)
        self.previous_key.clicked.connect(lambda:self.navigate_key(-1));self.next_key.clicked.connect(lambda:self.navigate_key(1));self.fit_timeline_button.clicked.connect(self.fit_timeline);self.fit_keys_button.clicked.connect(self.fit_visible_keys);self.fit_selected_button.clicked.connect(self.fit_selected_keys);self.reveal_combo.currentIndexChanged.connect(lambda index:self.set_reveal_mode(("all","animated","selected")[index]));self.snap_toggle.toggled.connect(self.set_snap_enabled)

        self.edit_buttons: list[QPushButton] = []
        for label, signal, tooltip in (
            ("+ Frame", self.add_requested, "Add frame"),
            ("⧉ Frame", self.duplicate_requested, "Duplicate selected frame"),
            ("− Frame", self.delete_requested, "Delete selected frame"),
            ("+ Layer", self.add_layer_requested, "Add layer"),
            ("Delete Selected Layer", self.delete_layer_requested, "Delete selected layer"),
        ):
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.clicked.connect(signal)
            self.edit_buttons.append(button)
        self.delete_layer_button = self.edit_buttons[-1]
        self.edit_buttons[2].setProperty("commandRole","danger");self.delete_layer_button.setProperty("commandRole","danger")

        self.play_button = QPushButton("▶")
        self.play_button.clicked.connect(self.play_requested)
        self.fps_label = QLabel("FPS")
        self.fps_spin = ScrollSafeSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.valueChanged.connect(self.fps_changed)
        layout.addLayout(status_toolbar)
        self.timeline_command_bar=QWidget(self);self.timeline_command_bar.setObjectName("effectTimelineCommandBar");timeline_controls=QHBoxLayout(self.timeline_command_bar);timeline_controls.setContentsMargins(0,0,0,0);timeline_controls.setSpacing(5);self.timeline_command_groups={}
        for name,widgets in (("playback",(self.play_button,self.fps_label,self.fps_spin)),("key_navigation",(self.previous_key,self.next_key)),("view",(self.fit_timeline_button,self.fit_keys_button,self.fit_selected_button,self.reveal_combo)),("assist",(self.snap_toggle,))):
            group=command_group(self.timeline_command_bar,name,widgets);self.timeline_command_groups[name]=group
            if timeline_controls.count():timeline_controls.addWidget(command_separator(self.timeline_command_bar))
            timeline_controls.addWidget(group)
        timeline_controls.addStretch();layout.addWidget(self.timeline_command_bar)
        self.structure_command_bar=QWidget(self);self.structure_command_bar.setObjectName("effectStructureCommandBar");structure_controls=QHBoxLayout(self.structure_command_bar);structure_controls.setContentsMargins(0,0,0,0);structure_controls.setSpacing(5);self.structure_command_groups={}
        for name,widgets in (("frame_structure",tuple(self.edit_buttons[:3])),("layer_structure",tuple(self.edit_buttons[3:]))):
            group=command_group(self.structure_command_bar,name,widgets);self.structure_command_groups[name]=group
            if structure_controls.count():structure_controls.addWidget(command_separator(self.structure_command_bar))
            structure_controls.addWidget(group)
        structure_controls.addStretch();layout.addWidget(self.structure_command_bar)

        self.table = InactiveTimelineTable()
        self.frame_cell_width = 36
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setMinimumHeight(EFFECT_TIMELINE_MIN_HEIGHT)
        self.table.setMaximumHeight(EFFECT_TIMELINE_MAX_HEIGHT)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setMinimumSectionSize(self._time_view.minimum_width)
        self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.scrub_controller = TimelineScrubController(
            self.table, self._scrub_to, self.scrub_started.emit, self,
            first_column=self.FRAME_COLUMN_OFFSET,finish=self.scrub_finished.emit,
        )
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)
        self.table.verticalHeader().setVisible(False)
        self._snap_guide=QFrame(self.table.viewport());self._snap_guide.setStyleSheet(f"background:{self.table.palette().highlight().color().name()};");self._snap_guide.hide()
        layout.addWidget(self.table)

    def _scrub_to(self, row: int, column: int) -> None:
        self.table.setCurrentCell(row, column)

    def set_frame_cell_width(self, width: int) -> None:
        self.frame_cell_width = self._time_view.clamp_width(width)
        self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        for column in range(self.FRAME_COLUMN_OFFSET, self.table.columnCount()):
            self.table.setColumnWidth(column, self.frame_cell_width)
        if self.table.columnCount() >= self.FRAME_COLUMN_OFFSET:
            self.table.setColumnWidth(self.VISIBILITY_COLUMN, 26)
            self.table.setColumnWidth(self.NAME_COLUMN, HIERARCHY_LABEL_WIDTH)
        stride=max(1,(28+self.frame_cell_width-1)//self.frame_cell_width)
        for frame in range(max(0,self.table.columnCount()-self.FRAME_COLUMN_OFFSET)):
            item=self.table.horizontalHeaderItem(frame+self.FRAME_COLUMN_OFFSET)
            if item:item.setText(str(frame+1) if frame%stride==0 else "")

    def zoom_time(self,steps,viewport_x):
        old=self.frame_cell_width;new=self._time_view.zoom_width(old,steps)
        if new==old:return False
        header=self.table.horizontalHeader();first_x=header.sectionViewportPosition(self.FRAME_COLUMN_OFFSET) if self.table.columnCount()>self.FRAME_COLUMN_OFFSET else 0;coordinate=self._time_view.frame_coordinate(viewport_x,first_x,old);self.set_frame_cell_width(new);new_first=header.sectionViewportPosition(self.FRAME_COLUMN_OFFSET) if self.table.columnCount()>self.FRAME_COLUMN_OFFSET else 0;bar=self.table.horizontalScrollBar();bar.setValue(int(round(bar.value()+self._time_view.anchored_scroll_delta(viewport_x,coordinate,new_first,new))));return True

    def _fit_range(self,frames):
        values=sorted(set(int(frame) for frame in frames))
        if not values:return False
        width=self._time_view.fit_width(self.table.viewport().width(),values[0],values[-1]);self.set_frame_cell_width(width);center=(values[0]+values[-1])/2;bar=self.table.horizontalScrollBar();bar.setValue(int(round((center+.5)*width-self.table.viewport().width()/2)));return True

    def fit_timeline(self):return self._fit_range(range(self._display_frame_count))
    def fit_visible_keys(self):return self._fit_range(key.frame for key in self._visible_keys) or self.fit_timeline()
    def fit_selected_keys(self):return self._fit_range(key.frame for key in self.key_selection.selected)
    def navigate_key(self,direction):
        target=navigation_frame((key.frame for key in self._visible_keys),self._current_frame,direction)
        if target is None:return False
        self.key_frame_requested.emit(target);return True
    def set_reveal_mode(self,mode):
        mode=str(mode)
        if mode not in {"all","animated","selected"} or mode==self.reveal_mode:return False
        self.reveal_mode=mode
        if self._project is not None:self.refresh(self._project,getattr(self,"_selected_layer_index",0),self._current_frame,self._display_frame_count,self._preview)
        return True

    def _toggle_visibility(self, row: int) -> None:
        if self._project is None:return
        descriptor=self.rows[row] if 0<=row<len(self.rows) else None
        if not descriptor or descriptor["kind"]!="layer":return
        index=descriptor["layer_index"]
        if 0<=index<len(self._project.layers):
            layer=self._project.layers[index]; self.layer_visibility_requested.emit(index,not layer.visible)

    def _on_cell_clicked(self, row: int, column: int) -> None:
        if column == self.VISIBILITY_COLUMN:
            self._toggle_visibility(row)

    def _show_context_menu(self, position) -> None:
        if self._project is None:
            return
        index = self.table.indexAt(position)
        item=self.table.item(index.row(),index.column()) if index.isValid() else None;key=item.data(Qt.ItemDataRole.UserRole+2) if item else None
        descriptor=self.rows[index.row()] if index.isValid() and 0<=index.row()<len(self.rows) else None
        if isinstance(key,TimelineKey) or descriptor and descriptor.get("kind")=="property":self._key_context_menu(key if isinstance(key,TimelineKey) else None,position);return
        if not index.isValid() or index.column() != self.NAME_COLUMN:
            return
        descriptor=self.rows[index.row()] if 0<=index.row()<len(self.rows) else None
        if not descriptor or descriptor["kind"]!="layer":return
        layer_index=descriptor["layer_index"]
        self.table.setCurrentCell(index.row(), self.NAME_COLUMN)
        localization = getattr(self, "_localization", None)
        label = localization.text("action.delete_layer") if localization else "Delete Selected Effect Layer"
        menu = QMenu(self.table)
        action = menu.addAction(label)
        action.setEnabled(self.delete_layer_button.isEnabled())
        if menu.exec(self.table.viewport().mapToGlobal(position)) is action:
            self.delete_layer_context_requested.emit(layer_index)

    def set_delete_layer_enabled(self, enabled: bool) -> None:
        self.delete_layer_button.setEnabled(enabled)
        localization = getattr(self, "_localization", None)
        if localization:
            apply_tooltip(
                self.delete_layer_button,
                localization,
                "tooltip.timeline.delete_layer" if enabled else "tooltip.main.select_layer_to_delete",
            )

    def retranslate_ui(self, localization) -> None:
        self._localization = localization
        texts = ("+ Frame", "⧉ Frame", "− Frame", "+ Layer", "Delete Selected Layer") if localization.language == "en" else ("+ 프레임", "⧉ 프레임", "− 프레임", "+ 레이어", "선택한 레이어 삭제")
        keys = ("tooltip.timeline.add_frame", "tooltip.timeline.duplicate_frame", "tooltip.timeline.delete_frame", "tooltip.timeline.add_layer", "tooltip.timeline.delete_layer")
        shortcut_keys = ("new_empty_frame", "new_frame", None, "new_layer", None)
        for button, text, key, shortcut_key in zip(self.edit_buttons, texts, keys, shortcut_keys, strict=True):
            button.setText(text)
            button.setAccessibleName(text.replace("+ ","").replace("− ","").replace("⧉ ",""))
            shortcuts = getattr(self, "_configured_shortcuts", {}).get(shortcut_key, []) if shortcut_key else None
            apply_tooltip(button, localization, key, shortcuts)
            button.setAccessibleDescription(button.toolTip())
        apply_tooltip(self.fps_spin, localization, "tooltip.timeline.fps")
        apply_tooltip(self.table, localization, "tooltip.timeline.table", status=False)
        self.fit_timeline_button.setText(localization.text("timeline.fit_timeline"));self.fit_keys_button.setText(localization.text("timeline.fit_visible_keys"));self.fit_selected_button.setText(localization.text("timeline.fit_selected_keys"));self.snap_toggle.setText(localization.text("timeline.snap"));self.snap_toggle.setAccessibleName(localization.text("timeline.snap"));self.reveal_combo.blockSignals(True);[self.reveal_combo.setItemText(index,localization.text(key)) for index,key in enumerate(("timeline.reveal_all","timeline.reveal_animated","timeline.reveal_selected"))];self.reveal_combo.blockSignals(False);apply_tooltip(self.previous_key,localization,"tooltip.timeline.previous_key");apply_tooltip(self.next_key,localization,"tooltip.timeline.next_key");apply_tooltip(self.fit_timeline_button,localization,"tooltip.timeline.fit");apply_tooltip(self.fit_keys_button,localization,"tooltip.timeline.fit_keys");apply_tooltip(self.fit_selected_button,localization,"tooltip.timeline.fit_selected");apply_tooltip(self.reveal_combo,localization,"tooltip.timeline.reveal");apply_tooltip(self.snap_toggle,localization,"tooltip.timeline.snap");self.previous_key.setAccessibleName(localization.text("timeline.previous_key"));self.next_key.setAccessibleName(localization.text("timeline.next_key"));self.fit_timeline_button.setAccessibleName(localization.text("timeline.fit_timeline"));self.fit_keys_button.setAccessibleName(localization.text("timeline.fit_visible_keys"));self.fit_selected_button.setAccessibleName(localization.text("timeline.fit_selected_keys"));self.reveal_combo.setAccessibleName(localization.text("timeline.reveal"));self.play_button.setAccessibleName(localization.text("tooltip.timeline.play"));[widget.setAccessibleDescription(widget.toolTip()) for widget in (self.previous_key,self.next_key,self.fit_timeline_button,self.fit_keys_button,self.fit_selected_button,self.reveal_combo,self.snap_toggle)];self.snap_toggle.setAccessibleDescription(self.snap_toggle.toolTip())
        self._update_play_tooltip()
        header = self.table.horizontalHeaderItem(self.NAME_COLUMN)
        if header is not None: header.setText(localization.text("timeline.layer"))

    def set_shortcuts(self, play, previous, next_, configured=None) -> None:
        self._play_shortcuts, self._previous_shortcuts, self._next_shortcuts = play, previous, next_
        self._configured_shortcuts = configured or {}
        if hasattr(self, "_localization"):
            self.retranslate_ui(self._localization)

    def _update_play_tooltip(self) -> None:
        localization = getattr(self, "_localization", None)
        if localization:
            apply_tooltip(self.play_button, localization, "tooltip.timeline.pause" if self._playing else "tooltip.timeline.play", self._play_shortcuts)

    def set_playing(self, playing: bool) -> None:
        """Synchronize the button display with the main playback QAction."""
        self._playing = playing
        self.play_button.setText("■" if playing else "▶")
        self._update_play_tooltip()
        if self._project is not None:
            self.update_playback_status(
                playing,
                self._current_frame,
                self._display_frame_count,
                self._project.fps,
                preview=self._preview,
            )

    def update_playback_status(
        self,
        playing: bool,
        frame_index: int,
        frame_count: int,
        fps: int,
        preview: bool = False,
        preparing: bool = False,
        ready: int = 0,
        required: int = 0,
    ) -> None:
        """Show playback state even when every project pixel is transparent."""
        self._playing = playing
        self._preview = preview
        self._display_frame_count = frame_count
        localization = getattr(self, "_localization", None)
        if preparing:
            state = ("Preparing playback…" if localization is None else localization.text("play.preparing")).format(ready=ready,total=required)
            self.playback_status_label.setText(f"{state} {ready} / {required}")
            return
        if localization is None:
            state = "Playing" if playing else "Stopped"
            if preview:
                state = f"Preview {state}"
            frame_word = "Frame"
        else:
            key = (
                "play.preview_playing" if preview and playing
                else "play.preview_stopped" if preview
                else "play.playing" if playing
                else "play.stopped"
            )
            state = localization.text(key)
            frame_word = localization.text("play.frame")
        current = min(max(frame_index + 1, 1), max(frame_count, 1))
        self.playback_status_label.setText(
            f"{state} · {frame_word} {current} / {frame_count} · {fps} FPS"
        )

    def _on_current_cell_changed(
        self, row: int, column: int, previous_row: int, previous_column: int
    ) -> None:
        if self._project is None or row < 0 or column < 0:
            return
        descriptor=self.rows[row] if 0<=row<len(self.rows) else None
        if descriptor is None:return
        layer_index=descriptor["layer_index"]
        if not (0 <= layer_index < len(self._project.layers)):
            return
        if not (0 <= column < self.table.columnCount()):
            return
        if column == self.VISIBILITY_COLUMN:
            return
        frame_index = self._current_frame if column == self.NAME_COLUMN else column - self.FRAME_COLUMN_OFFSET
        if not (0 <= frame_index < self._display_frame_count):
            return
        self._current_frame = frame_index
        self._update_selection_label(layer_index, frame_index)
        from PySide6.QtWidgets import QApplication
        modifiers=QApplication.keyboardModifiers();self.cell_selected.emit(layer_index,frame_index);self.cell_selected_with_modifiers.emit(layer_index,frame_index,modifiers)

    def eventFilter(self,watched,event):
        if watched is self.table and event.type()==QEvent.Type.KeyPress:
            if event.modifiers()==(Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier) and event.key() in {Qt.Key.Key_Left,Qt.Key.Key_Right}:self.navigate_key(-1 if event.key()==Qt.Key.Key_Left else 1);return True
            control=event.modifiers()==Qt.KeyboardModifier.ControlModifier
            if control and event.key()==Qt.Key.Key_C and self.key_selection.selected:self.multi_key_copy_requested.emit(list(self.key_selection.selected));return True
            if control and event.key()==Qt.Key.Key_V and read_timeline_clipboard_payload() is not None:self.multi_key_paste_requested.emit();return True
            if self.key_selection.selected:
                if event.key()==Qt.Key.Key_Delete:self.multi_key_delete_requested.emit(list(self.key_selection.selected));return True
                if event.modifiers()&Qt.KeyboardModifier.AltModifier and event.key() in {Qt.Key.Key_Left,Qt.Key.Key_Right}:self.multi_key_move_requested.emit(list(self.key_selection.selected),-1 if event.key()==Qt.Key.Key_Left else 1);return True
                if event.key()==Qt.Key.Key_Escape:self._cancel_key_gesture();return True
            if event.key()==Qt.Key.Key_A and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.select_all_layers_requested.emit();return True
            if event.key()==Qt.Key.Key_Delete:self.delete_layer_requested.emit();return True
        if watched is self.table.viewport():
            if event.type()==QEvent.Type.Wheel and event.modifiers()&Qt.KeyboardModifier.ControlModifier:
                self.zoom_time(1 if event.angleDelta().y()>0 else -1,event.position().x());event.accept();return True
            if event.type()==QEvent.Type.Wheel and event.modifiers()&Qt.KeyboardModifier.ShiftModifier:
                bar=self.table.horizontalScrollBar();bar.setValue(bar.value()-event.angleDelta().y());event.accept();return True
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.MiddleButton:
                self._clear_snap_guide();self._time_pan=(event.position().x(),self.table.horizontalScrollBar().value());self.table.viewport().setCursor(Qt.CursorShape.ClosedHandCursor);event.accept();return True
            if event.type()==QEvent.Type.MouseMove and self._time_pan and event.buttons()&Qt.MouseButton.MiddleButton:
                start,value=self._time_pan;self.table.horizontalScrollBar().setValue(int(value-(event.position().x()-start)));event.accept();return True
            if event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.MiddleButton and self._time_pan:
                self._time_pan=None;self.table.viewport().unsetCursor();event.accept();return True
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                point=event.position().toPoint();index=self.table.indexAt(point);item=self.table.item(index.row(),index.column()) if index.isValid() else None;key=item.data(Qt.ItemDataRole.UserRole+2) if item else None
                if isinstance(key,TimelineKey) and not self._effect_key_locked(key):
                    modifiers=event.modifiers();ctrl=bool(modifiers&Qt.KeyboardModifier.ControlModifier);shift=bool(modifiers&Qt.KeyboardModifier.ShiftModifier);preserve_click=key in self.key_selection.selected and not ctrl and not shift;track_keys=[value for value in self._visible_keys if value.track_id==key.track_id]
                    if not preserve_click:self.key_selection.click(key,ctrl=ctrl,shift=shift,track_keys=track_keys)
                    playhead_before=self._current_frame;self._key_drag=(key,index.column(),point,False,None,(),preserve_click,None,playhead_before);self.table.blockSignals(True);self.table.setCurrentCell(index.row(),index.column());self.table.blockSignals(False);self._current_frame=key.frame;self._apply_key_visuals();event.accept();return True
                if index.isValid() and self._row_is_property(index.row()):
                    self._clear_snap_guide();self._marquee_origin=point;self._marquee_ctrl=bool(event.modifiers()&Qt.KeyboardModifier.ControlModifier);self._marquee=QRubberBand(QRubberBand.Shape.Rectangle,self.table.viewport());self._marquee.setGeometry(QRect(point,point));self._marquee.show();event.accept();return True
            elif event.type()==QEvent.Type.MouseMove and self._key_drag and event.buttons()&Qt.MouseButton.LeftButton:
                key,column,start,was_dragged,duplicate,snapshot,preserve_click,snap_snapshot,playhead_before=self._drag_state();dragged=was_dragged or (event.position().toPoint()-start).manhattanLength()>=QApplication.startDragDistance()
                if dragged and not was_dragged:
                    duplicate=bool(event.modifiers()&Qt.KeyboardModifier.AltModifier);snapshot=tuple(self.key_selection.selected);snap_snapshot=collect_snap_targets(self._visible_keys,snapshot,playhead_before,self._display_frame_count) if self.snap_enabled else None
                self._key_drag=(key,column,start,dragged,duplicate,snapshot,preserve_click,snap_snapshot,playhead_before)
                if dragged:self._preview_key_drag(column,event.position().x(),duplicate=bool(duplicate),keys=snapshot,start_x=start.x(),snap_snapshot=snap_snapshot)
                event.accept();return True
            elif event.type()==QEvent.Type.MouseMove and self._marquee and event.buttons()&Qt.MouseButton.LeftButton:
                self._marquee.setGeometry(QRect(self._marquee_origin,event.position().toPoint()).normalized());event.accept();return True
            elif event.type()==QEvent.Type.MouseButtonRelease and self._key_drag:
                key,source,start,dragged,duplicate,snapshot,preserve_click,snap_snapshot,playhead_before=self._drag_state();self._key_drag=None;self.table.viewport().unsetCursor();self._clear_snap_guide()
                if not dragged and preserve_click:self.key_selection.click(key,track_keys=[value for value in self._visible_keys if value.track_id==key.track_id])
                self._apply_key_visuals()
                if dragged:
                    delta,_snap,_issue=self._resolve_drag_delta(source,start.x(),event.position().x(),bool(duplicate),snapshot,snap_snapshot)
                    if delta:(self.multi_key_duplicate_requested if duplicate else self.multi_key_move_requested).emit(list(snapshot or self.key_selection.selected),delta)
                event.accept();return True
            elif event.type()==QEvent.Type.MouseButtonRelease and self._marquee:
                rect=self._marquee.geometry();self._marquee.hide();self._marquee.deleteLater();self._marquee=None;keys=[]
                for row in range(self.table.rowCount()):
                    if not self._row_is_property(row):continue
                    for column in range(self.FRAME_COLUMN_OFFSET,self.table.columnCount()):
                        item=self.table.item(row,column);key=item.data(Qt.ItemDataRole.UserRole+2) if item else None
                        if isinstance(key,TimelineKey) and rect.intersects(self.table.visualItemRect(item)):keys.append(key)
                self.key_selection.marquee(keys,ctrl=self._marquee_ctrl);self._apply_key_visuals();event.accept();return True
        return super().eventFilter(watched,event)

    def _row_is_property(self,row):return 0<=row<len(self.rows) and self.rows[row]["kind"]=="property"

    def _effect_key_locked(self,key):
        layer=next((item for item in self._project.effect_resource_layers if item.id==key.layer_id),None) if self._project else None
        return layer is None or self._project.effect_effective_locked(layer)

    def _cancel_key_gesture(self):
        self._key_drag=None;self.table.viewport().unsetCursor();self._clear_snap_guide();self._apply_key_visuals()
        if self._marquee:self._marquee.hide();self._marquee.deleteLater();self._marquee=None

    def _drag_state(self):
        if len(self._key_drag)==4:
            key,column,start,dragged=self._key_drag;return key,column,start,dragged,False,tuple(self.key_selection.selected),False,None,self._current_frame
        if len(self._key_drag)==6:return (*self._key_drag,False,None,self._current_frame)
        if len(self._key_drag)==7:return (*self._key_drag,None,self._current_frame)
        if len(self._key_drag)==8:return (*self._key_drag,self._current_frame)
        return self._key_drag

    def _apply_key_visuals(self):
        selected_brush=self.table.palette().highlight();base_brush=self.table.palette().base();primary=self.key_selection.primary
        for row in range(self.table.rowCount()):
            for column in range(self.FRAME_COLUMN_OFFSET,self.table.columnCount()):
                item=self.table.item(row,column);key=item.data(Qt.ItemDataRole.UserRole+2) if item else None
                if item is not None and self._row_is_property(row):item.setText("◆" if isinstance(key,TimelineKey) else "");item.setBackground(self.table.palette().alternateBase() if column==self._current_frame+self.FRAME_COLUMN_OFFSET else base_brush)
                if not isinstance(key,TimelineKey):continue
                item.setBackground(selected_brush if key in self.key_selection.selected else base_brush);font=item.font();font.setBold(key==primary);item.setFont(font);item.setText("⬥" if key==primary else "◆")
        count=len(self.key_selection.selected)
        if count:self.selection_label.setText((self._localization.text("timeline.keys_selected") if hasattr(self,"_localization") else "{count} Keys Selected").format(count=count))

    def _resolve_drag_delta(self,source_column,start_x,x,duplicate,keys,snap_snapshot):
        selected=set(keys);target=self.table.columnAt(int(x));target=(self.FRAME_COLUMN_OFFSET if x<0 else self.table.columnCount()-1) if target<0 else target;target=max(self.FRAME_COLUMN_OFFSET,min(self.table.columnCount()-1,target));requested=target-source_column;base=requested if duplicate else clamp_group_delta(selected,requested,self._display_frame_count);snap=None
        if self.snap_enabled and snap_snapshot is not None:
            raw=(float(x)-float(start_x))/max(1,self.frame_cell_width);valid=lambda delta:batch_delta_issue(selected,delta,self._display_frame_count,self._occupied_keys,duplicate) is None;snap=compute_batch_snap(snap_snapshot,selected,raw,base,self.frame_cell_width,valid)
        delta=snap.delta if snap else base;return delta,snap,batch_delta_issue(selected,delta,self._display_frame_count,self._occupied_keys,duplicate)

    def _preview_key_drag(self,source_column,x,duplicate=False,keys=None,start_x=None,snap_snapshot=None):
        selected=set(keys or self.key_selection.selected);delta,snap,issue=self._resolve_drag_delta(source_column,x if start_x is None else start_x,x,duplicate,selected,snap_snapshot);noop=delta==0;invalid=not noop and issue is not None;self._apply_key_visuals();self.table.viewport().setCursor(Qt.CursorShape.ForbiddenCursor if invalid else Qt.CursorShape.DragCopyCursor if duplicate else Qt.CursorShape.SizeHorCursor);self._show_snap_guide(snap if not invalid else None)
        for key in selected:
            row=next((index for index,value in enumerate(self.rows) if value.get("kind")=="property" and value.get("logical") is not None and value["logical"].id==key.layer_id and value.get("scope")==key.scope and value.get("property_id")==key.property_id),-1);source=self.table.item(row,key.frame+self.FRAME_COLUMN_OFFSET) if row>=0 else None;destination=self.table.item(row,key.frame+delta+self.FRAME_COLUMN_OFFSET) if row>=0 and 0<=key.frame+delta<self._display_frame_count else None
            if source and not duplicate:source.setText("◇")
            if destination and not noop:destination.setText("×" if invalid else "+" if duplicate else "⬥");destination.setBackground(self.table.palette().alternateBase())
        count=len(selected);mode="Duplicate" if duplicate else "Move";suffix=" · No change" if noop else " · Boundary" if issue=="boundary" else " · Collision" if invalid else "";text=f"{count} Keys · {mode} · Δ {delta:+d}"+suffix
        if snap:text+=self._snap_status(snap)
        self.selection_label.setText(text)

    def _show_snap_guide(self,result):
        if result is None:self._clear_snap_guide();return
        first_x=self.table.horizontalHeader().sectionViewportPosition(self.FRAME_COLUMN_OFFSET);x=int(round(self._time_view.frame_to_x(result.guide_frame,first_x,self.frame_cell_width)));self._snap_guide.setGeometry(x-1,0,2,self.table.viewport().height());self._snap_guide.raise_();self._snap_guide.show()

    def _clear_snap_guide(self):self._snap_guide.hide()
    def _snap_status(self,result):
        localization=getattr(self,"_localization",None);label=localization.text("timeline.snap_"+result.target_kind) if localization else result.target_kind.title();frame=localization.text("play.frame") if localization else "Frame";return f" · {label} · {frame} {result.guide_frame+1}"
    def set_snap_enabled(self,enabled):
        enabled=bool(enabled);changed=enabled!=self.snap_enabled;self.snap_enabled=enabled
        if self.snap_toggle.isChecked()!=enabled:self.snap_toggle.blockSignals(True);self.snap_toggle.setChecked(enabled);self.snap_toggle.blockSignals(False)
        self._clear_snap_guide();return changed

    def _clipboard_context_id(self):return f"effect:{id(self._project):x}" if self._project is not None else ""

    def _key_context_menu(self,key,position):
        if isinstance(key,TimelineKey) and key not in self.key_selection.selected:self.key_selection.click(key,track_keys=[value for value in self._visible_keys if value.track_id==key.track_id]);self._apply_key_visuals()
        localization=getattr(self,"_localization",None);menu=QMenu(self.table);copy_action=menu.addAction(localization.text("timeline.copy_keys") if localization else "Copy Keys");paste_action=menu.addAction(localization.text("timeline.paste_keys") if localization else "Paste Keys");copy_action.setEnabled(bool(self.key_selection.selected));paste_action.setEnabled(timeline_clipboard_matches("effect",self._clipboard_context_id()));menu.addSeparator();delete=menu.addAction(localization.text("timeline.delete_selected_keys") if localization else "Delete Selected Keys");delete.setEnabled(bool(self.key_selection.selected));easing_menu=menu.addMenu(localization.text("property.easing") if localization else "Easing");easing_menu.setEnabled(bool(self.key_selection.selected));actions={easing_menu.addAction(localization.text("easing."+name.lower().replace(" ","_").replace("/","_")) if localization else name):name for name in ("Linear","Ease In","Ease Out","Ease In/Out")};chosen=menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is copy_action:self.multi_key_copy_requested.emit(list(self.key_selection.selected))
        elif chosen is paste_action:self.multi_key_paste_requested.emit()
        elif chosen is delete:self.multi_key_delete_requested.emit(list(self.key_selection.selected))
        elif chosen in actions:self.multi_key_easing_requested.emit(list(self.key_selection.selected),actions[chosen])

    def refresh(
        self,
        project: Project,
        selected_layer: int = 0,
        selected_frame: int = 0,
        display_frame_count: int | None = None,
        preview: bool = False,
    ) -> None:
        """Rebuild the table while preserving a valid model selection."""
        self._project=project;self._selected_layer_index=selected_layer;self.table.blockSignals(True);self.table.clear();frame_count=display_frame_count or len(project.frames);self._display_frame_count=frame_count;self._preview=preview;localization=getattr(self,"_localization",None);parent_labels=parent_display_labels(project.effect_resource_layers,project.effect_layer_groups);logical_by_generated={item.generated_layer_id:item for item in project.effect_resource_layers};main_rows=[];property_rows=[];self._occupied_keys=set()
        for layer_index in reversed(range(len(project.layers))):
            generated=project.layers[layer_index];logical=logical_by_generated.get(generated.id);main_rows.append({"kind":"layer","layer_index":layer_index,"generated":generated,"logical":logical})
            if logical:
                self._occupied_keys.update(TimelineKey(logical.id,"effect_transform",property_id,key.frame) for property_id,track in logical.layer_transform.tracks.items() for key in track.keyframes)
                if logical.placement_mode=="particle":self._occupied_keys.update(TimelineKey(logical.id,"effect_motion",property_id,key.frame) for property_id,track in logical.particle_settings.motion.tracks.items() for key in track.keyframes)
                for property_id,track in sorted(logical.layer_transform.tracks.items()):
                    if track.keyframes:property_rows.append({"kind":"property","layer_index":layer_index,"generated":generated,"logical":logical,"scope":"effect_transform","property_id":property_id,"track":track})
                if logical.placement_mode=="particle":
                    for property_id,track in sorted(logical.particle_settings.motion.tracks.items()):
                        if track.keyframes:property_rows.append({"kind":"property","layer_index":layer_index,"generated":generated,"logical":logical,"scope":"effect_motion","property_id":property_id,"track":track})
        animated_ids={item.id for item in project.effect_resource_layers if any(track.keyframes for track in item.layer_transform.tracks.values()) or item.placement_mode=="particle" and any(track.keyframes for track in item.particle_settings.motion.tracks.values())}
        if self.reveal_mode=="animated":main_rows=[row for row in main_rows if row["logical"] is not None and row["logical"].id in animated_ids];property_rows=[row for row in property_rows if row["logical"].id in animated_ids]
        elif self.reveal_mode=="selected":main_rows=[row for row in main_rows if row["logical"] is not None and row["logical"].id in self._selected_logical_ids];property_rows=[row for row in property_rows if row["logical"].id in self._selected_logical_ids]
        self.rows=main_rows+property_rows
        stride=max(1,(28+self.frame_cell_width-1)//self.frame_cell_width);self.table.setRowCount(len(self.rows));self.table.setColumnCount(frame_count+self.FRAME_COLUMN_OFFSET);self.table.setHorizontalHeaderLabels(["",localization.text("timeline.layer") if localization else "Layer"]+[str(index) if (index-1)%stride==0 else "" for index in range(1,frame_count+1)]);self._visible_keys=set()
        for display_row,descriptor in enumerate(self.rows):
            generated=descriptor["generated"];logical=descriptor["logical"]
            if descriptor["kind"]=="layer":
                visibility=QTableWidgetItem();visibility.setTextAlignment(Qt.AlignmentFlag.AlignCenter);visibility.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton if generated.visible else QStyle.StandardPixmap.SP_DialogNoButton))
                if localization:visibility.setToolTip(localization.text("tooltip.visibility.hide" if generated.visible else "tooltip.visibility.show"))
                self.table.setItem(display_row,self.VISIBILITY_COLUMN,visibility);lock="L" if logical and logical.locked else "L*" if logical and project.effect_effective_locked(logical) else " ";solo="S" if logical and logical.solo else " ";parent_label=parent_labels.get(logical.id,"") if logical else "";base=f"{lock:2} {solo} {generated.name}{f' [P: {parent_label}]' if parent_label else ''}";name_item=QTableWidgetItem("  "+base);name_item.setData(Qt.ItemDataRole.UserRole,logical.id if logical else None);name_item.setData(Qt.ItemDataRole.UserRole+1,base);tooltip=[generated.name]
                if parent_label and localization:tooltip.append(localization.text("hierarchy.parent_tooltip").format(name=parent_label))
                if logical and localization:tooltip.append(localization.text("hierarchy.own_lock") if logical.locked else localization.text("hierarchy.inherited_lock") if project.effect_effective_locked(logical) else "")
                name_item.setToolTip("\n".join(value for value in tooltip if value));self.table.setItem(display_row,self.NAME_COLUMN,name_item)
            else:
                self.table.setItem(display_row,self.VISIBILITY_COLUMN,QTableWidgetItem());label_key="property."+descriptor["property_id"];label=localization.text(label_key) if localization else label_key
                if label==label_key:label=descriptor["property_id"].replace("_"," ").title()
                name_item=QTableWidgetItem(f"    └ {generated.name} · {label}");name_item.setToolTip(f"{generated.name} · {label}");self.table.setItem(display_row,self.NAME_COLUMN,name_item)
            for frame_index in range(frame_count):
                column=frame_index+self.FRAME_COLUMN_OFFSET
                if descriptor["kind"]=="property":
                    key=descriptor["track"].keyframe_at(frame_index);item=QTableWidgetItem("◆" if key else "");item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if key:key_id=TimelineKey(logical.id,descriptor["scope"],descriptor["property_id"],frame_index);item.setData(Qt.ItemDataRole.UserRole+2,key_id);item.setToolTip(f"{generated.name} · {descriptor['property_id']} · Frame {frame_index+1} · {key.easing}");self._visible_keys.add(key_id)
                else:
                    frame=project.frames[frame_index] if frame_index<len(project.frames) else None;pixels=None if frame is None else frame.layer_pixels.get(generated.id);transform_keys=[] if logical is None else [name for name,track in logical.layer_transform.tracks.items() if track.has_keyframe(frame_index)];motion_keys=[] if logical is None or logical.placement_mode!="particle" else [name for name,track in logical.particle_settings.motion.tracks.items() if track.has_keyframe(frame_index)];marker="◆" if transform_keys or motion_keys else "■" if pixels is not None and pixels[...,3].any() else "·";item=QTableWidgetItem(marker);item.setTextAlignment(Qt.AlignmentFlag.AlignCenter);key_detail=(" · Keys: "+", ".join(transform_keys+motion_keys)) if transform_keys or motion_keys else "";item.setToolTip(f"{generated.name} · Frame {frame_index+1}{key_detail}")
                self.table.setItem(display_row,column,item)
        self.table.setColumnWidth(self.VISIBILITY_COLUMN, 26)
        self.table.setColumnWidth(self.NAME_COLUMN, HIERARCHY_LABEL_WIDTH)
        for column in range(self.FRAME_COLUMN_OFFSET, self.table.columnCount()):
            self.table.setColumnWidth(column, self.frame_cell_width)
        self.key_selection.repair(self._visible_keys);self.table.blockSignals(False)
        self.set_current_cell(
            project,
            selected_layer,
            selected_frame,
            display_frame_count=frame_count,
        )
        self.fps_spin.blockSignals(True)
        self.fps_spin.setValue(project.fps)
        self.fps_spin.blockSignals(False)
        self._apply_key_visuals()

    def set_current_cell(
        self,
        project: Project,
        layer_index: int,
        frame_index: int,
        display_frame_count: int | None = None,
    ) -> None:
        """Select the cell corresponding to model indices without emitting edits."""
        if not project.layers or not project.frames:
            return
        layer_index = max(0, min(layer_index, len(project.layers) - 1))
        frame_count = display_frame_count or len(project.frames)
        frame_index = max(0, min(frame_index, frame_count - 1))
        display_row=next((row for row,value in enumerate(self.rows) if value["kind"]=="layer" and value["layer_index"]==layer_index),0)
        self.table.blockSignals(True)
        self._current_frame = frame_index
        self.table.setCurrentCell(display_row, frame_index + self.FRAME_COLUMN_OFFSET)
        self.table.blockSignals(False)
        self._highlight_frame_column(frame_index)
        current_item = self.table.currentItem()
        if current_item is not None:
            self.table.scrollToItem(
                current_item, QAbstractItemView.ScrollHint.PositionAtCenter
            )
        self._update_selection_label(layer_index, frame_index)
        self.update_playback_status(
            self._playing,
            frame_index,
            frame_count,
            project.fps,
            preview=self._preview,
        )

    def set_resource_layer_key_marker(self,project,resource_layer,frame_index):
        """Refresh one transient Effect key marker without committing the drag model."""
        generated=next((layer for layer in project.layers if layer.id==resource_layer.generated_layer_id),None)
        if generated is None or not 0<=int(frame_index)<self._display_frame_count:return
        layer_index=project.layers.index(generated);row=next((index for index,value in enumerate(self.rows) if value["kind"]=="layer" and value["layer_index"]==layer_index),-1);column=int(frame_index)+self.FRAME_COLUMN_OFFSET;item=self.table.item(row,column) if row>=0 else None
        if item is None:return
        transform_keys=[name for name,track in resource_layer.layer_transform.tracks.items() if track.has_keyframe(frame_index)]
        motion_keys=[] if resource_layer.placement_mode!="particle" else [name for name,track in resource_layer.particle_settings.motion.tracks.items() if track.has_keyframe(frame_index)]
        if transform_keys or motion_keys:
            item.setText("◆");item.setToolTip(f"{generated.name} · Frame {int(frame_index)+1} · Keys: {', '.join(transform_keys+motion_keys)}")
            return
        frame=project.frames[frame_index] if frame_index<len(project.frames) else None;pixels=None if frame is None else frame.layer_pixels.get(generated.id);item.setText("■" if pixels is not None and pixels[...,3].any() else "·");item.setToolTip(f"{generated.name} · Frame {int(frame_index)+1}")

    def set_effect_selection(self,project,selected_ids,primary_id):
        selected_ids=set(selected_ids);changed=selected_ids!=self._selected_logical_ids;self._selected_logical_ids=set(selected_ids);self._primary_logical_id=primary_id
        if changed and self.reveal_mode=="selected":self.refresh(project,getattr(self,"_selected_layer_index",0),self._current_frame,self._display_frame_count,self._preview)
        logical_by_generated={item.generated_layer_id:item for item in project.effect_resource_layers}
        for row,descriptor in enumerate(self.rows):
            generated=descriptor["generated"];logical=logical_by_generated.get(generated.id);selected=logical is not None and logical.id in selected_ids;color=QColor("#315a78" if logical is not None and logical.id==primary_id else "#29465b")
            for column in range(self.table.columnCount()):
                item=self.table.item(row,column)
                if item:item.setBackground(QBrush(color) if selected else QBrush())
            name_item=self.table.item(row,self.NAME_COLUMN)
            if name_item and logical is not None and descriptor["kind"]=="layer":
                marker="▌" if logical.id==primary_id else "•" if selected else " ";name_item.setText(marker+" "+str(name_item.data(Qt.ItemDataRole.UserRole+1) or generated.name));font=name_item.font();font.setBold(logical.id==primary_id);name_item.setFont(font)
        self._apply_key_visuals()

    def _update_selection_label(self, layer_index: int, frame_index: int) -> None:
        if self._project is None:
            return
        self.selection_label.setText(
            f"{self._project.layers[layer_index].name} · Frame {frame_index + 1}"
        )

    def _highlight_frame_column(self, frame_index: int) -> None:
        highlight = QBrush(QColor("#34495e"))
        clear = QBrush()
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    item.setBackground(
                        highlight if column == frame_index + self.FRAME_COLUMN_OFFSET else clear
                    )
        self._apply_key_visuals()
