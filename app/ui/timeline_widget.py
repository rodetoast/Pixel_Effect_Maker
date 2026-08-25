"""Integrated layer-by-frame timeline controls."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
from app.ui.timeline_multi_key import TimelineKey, TimelineKeySelection, clamp_group_delta


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
    multi_key_delete_requested=Signal(object)
    multi_key_easing_requested=Signal(object,str)
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
        self.rows=[];self.key_selection=TimelineKeySelection();self._visible_keys=set();self._key_drag=None;self._marquee=None;self._marquee_origin=None;self._marquee_ctrl=False
        layout = QVBoxLayout(self)
        status_toolbar = QHBoxLayout()
        self.selection_label = QLabel("Layer 1 · Frame 1")
        self.selection_label.setStyleSheet("font-weight: bold;")
        status_toolbar.addWidget(self.selection_label)
        self.playback_status_label = QLabel("Stopped · Frame 1 / 1 · 12 FPS")
        status_toolbar.addWidget(self.playback_status_label)
        status_toolbar.addStretch(1)
        edit_toolbar = QHBoxLayout()

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
            edit_toolbar.addWidget(button)
            self.edit_buttons.append(button)
        self.delete_layer_button = self.edit_buttons[-1]

        self.play_button = QPushButton("▶")
        self.play_button.clicked.connect(self.play_requested)
        status_toolbar.addWidget(self.play_button)
        self.fps_label = QLabel("FPS")
        status_toolbar.addWidget(self.fps_label)
        self.fps_spin = ScrollSafeSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.valueChanged.connect(self.fps_changed)
        status_toolbar.addWidget(self.fps_spin)
        edit_toolbar.addStretch(1)
        layout.addLayout(status_toolbar)
        layout.addLayout(edit_toolbar)

        self.table = QTableWidget()
        self.frame_cell_width = 36
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setMinimumHeight(EFFECT_TIMELINE_MIN_HEIGHT)
        self.table.setMaximumHeight(EFFECT_TIMELINE_MAX_HEIGHT)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setMinimumSectionSize(20)
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
        layout.addWidget(self.table)

    def _scrub_to(self, row: int, column: int) -> None:
        self.table.setCurrentCell(row, column)

    def set_frame_cell_width(self, width: int) -> None:
        self.frame_cell_width = max(20, min(96, int(width)))
        self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        for column in range(self.FRAME_COLUMN_OFFSET, self.table.columnCount()):
            self.table.setColumnWidth(column, self.frame_cell_width)
        if self.table.columnCount() >= self.FRAME_COLUMN_OFFSET:
            self.table.setColumnWidth(self.VISIBILITY_COLUMN, 26)
            self.table.setColumnWidth(self.NAME_COLUMN, HIERARCHY_LABEL_WIDTH)

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
        if isinstance(key,TimelineKey):self._key_context_menu(key,position);return
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
            shortcuts = getattr(self, "_configured_shortcuts", {}).get(shortcut_key, []) if shortcut_key else None
            apply_tooltip(button, localization, key, shortcuts)
        apply_tooltip(self.fps_spin, localization, "tooltip.timeline.fps")
        apply_tooltip(self.table, localization, "tooltip.timeline.table", status=False)
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
            if self.key_selection.selected:
                if event.key()==Qt.Key.Key_Delete:self.multi_key_delete_requested.emit(list(self.key_selection.selected));return True
                if event.modifiers()&Qt.KeyboardModifier.AltModifier and event.key() in {Qt.Key.Key_Left,Qt.Key.Key_Right}:self.multi_key_move_requested.emit(list(self.key_selection.selected),-1 if event.key()==Qt.Key.Key_Left else 1);return True
                if event.key()==Qt.Key.Key_Escape:self._cancel_key_gesture();return True
            if event.key()==Qt.Key.Key_A and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.select_all_layers_requested.emit();return True
            if event.key()==Qt.Key.Key_Delete:self.delete_layer_requested.emit();return True
        if watched is self.table.viewport():
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                point=event.position().toPoint();index=self.table.indexAt(point);item=self.table.item(index.row(),index.column()) if index.isValid() else None;key=item.data(Qt.ItemDataRole.UserRole+2) if item else None
                if isinstance(key,TimelineKey) and not self._effect_key_locked(key):
                    modifiers=event.modifiers();track_keys=[value for value in self._visible_keys if value.track_id==key.track_id];self.key_selection.click(key,ctrl=bool(modifiers&Qt.KeyboardModifier.ControlModifier),shift=bool(modifiers&Qt.KeyboardModifier.ShiftModifier),track_keys=track_keys);self._key_drag=(key,index.column(),point,False);self.table.blockSignals(True);self.table.setCurrentCell(index.row(),index.column());self.table.blockSignals(False);self._current_frame=key.frame;self._apply_key_visuals();event.accept();return True
                if index.isValid() and self._row_is_property(index.row()):
                    self._marquee_origin=point;self._marquee_ctrl=bool(event.modifiers()&Qt.KeyboardModifier.ControlModifier);self._marquee=QRubberBand(QRubberBand.Shape.Rectangle,self.table.viewport());self._marquee.setGeometry(QRect(point,point));self._marquee.show();event.accept();return True
            elif event.type()==QEvent.Type.MouseMove and self._key_drag and event.buttons()&Qt.MouseButton.LeftButton:
                key,column,start,_=self._key_drag;dragged=(event.position().toPoint()-start).manhattanLength()>=QApplication.startDragDistance();self._key_drag=(key,column,start,dragged)
                if dragged:self._preview_key_drag(column,event.position().x())
                event.accept();return True
            elif event.type()==QEvent.Type.MouseMove and self._marquee and event.buttons()&Qt.MouseButton.LeftButton:
                self._marquee.setGeometry(QRect(self._marquee_origin,event.position().toPoint()).normalized());event.accept();return True
            elif event.type()==QEvent.Type.MouseButtonRelease and self._key_drag:
                key,source,_,dragged=self._key_drag;self._key_drag=None;self.table.viewport().unsetCursor();self._apply_key_visuals()
                if dragged:
                    target=self.table.columnAt(int(event.position().x()));target=(self.FRAME_COLUMN_OFFSET if event.position().x()<0 else self.table.columnCount()-1) if target<0 else target;target=max(self.FRAME_COLUMN_OFFSET,min(self.table.columnCount()-1,target));delta=target-source
                    if delta:self.multi_key_move_requested.emit(list(self.key_selection.selected),delta)
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
        self._key_drag=None;self.table.viewport().unsetCursor();self._apply_key_visuals()
        if self._marquee:self._marquee.hide();self._marquee.deleteLater();self._marquee=None

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

    def _preview_key_drag(self,source_column,x):
        target=self.table.columnAt(int(x));target=(self.FRAME_COLUMN_OFFSET if x<0 else self.table.columnCount()-1) if target<0 else target;requested=target-source_column;delta=clamp_group_delta(self.key_selection.selected,requested,self._display_frame_count);destinations={key.at_frame(key.frame+delta) for key in self.key_selection.selected};invalid=bool((destinations&self._visible_keys)-self.key_selection.selected);self._apply_key_visuals();self.table.viewport().setCursor(Qt.CursorShape.ForbiddenCursor if invalid else Qt.CursorShape.SizeHorCursor)
        for key in self.key_selection.selected:
            row=next((index for index,value in enumerate(self.rows) if value.get("kind")=="property" and value.get("logical") is not None and value["logical"].id==key.layer_id and value.get("scope")==key.scope and value.get("property_id")==key.property_id),-1);source=self.table.item(row,key.frame+self.FRAME_COLUMN_OFFSET) if row>=0 else None;destination=self.table.item(row,key.frame+delta+self.FRAME_COLUMN_OFFSET) if row>=0 and 0<=key.frame+delta<self._display_frame_count else None
            if source:source.setText("◇")
            if destination:destination.setText("×" if invalid else "⬥");destination.setBackground(self.table.palette().alternateBase())
        count=len(self.key_selection.selected);self.selection_label.setText(f"{count} Keys · Δ {delta:+d}"+(" · Collision" if invalid else ""))

    def _key_context_menu(self,key,position):
        if key not in self.key_selection.selected:self.key_selection.click(key,track_keys=[value for value in self._visible_keys if value.track_id==key.track_id]);self._apply_key_visuals()
        localization=getattr(self,"_localization",None);menu=QMenu(self.table);delete=menu.addAction(localization.text("timeline.delete_selected_keys") if localization else "Delete Selected Keys");easing_menu=menu.addMenu(localization.text("property.easing") if localization else "Easing");actions={easing_menu.addAction(localization.text("easing."+name.lower().replace(" ","_").replace("/","_")) if localization else name):name for name in ("Linear","Ease In","Ease Out","Ease In/Out")};chosen=menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen is delete:self.multi_key_delete_requested.emit(list(self.key_selection.selected))
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
        self._project=project;self.table.blockSignals(True);self.table.clear();frame_count=display_frame_count or len(project.frames);self._display_frame_count=frame_count;self._preview=preview;localization=getattr(self,"_localization",None);parent_labels=parent_display_labels(project.effect_resource_layers,project.effect_layer_groups);logical_by_generated={item.generated_layer_id:item for item in project.effect_resource_layers};main_rows=[];property_rows=[]
        for layer_index in reversed(range(len(project.layers))):
            generated=project.layers[layer_index];logical=logical_by_generated.get(generated.id);main_rows.append({"kind":"layer","layer_index":layer_index,"generated":generated,"logical":logical})
            if logical:
                for property_id,track in sorted(logical.layer_transform.tracks.items()):
                    if track.keyframes:property_rows.append({"kind":"property","layer_index":layer_index,"generated":generated,"logical":logical,"scope":"effect_transform","property_id":property_id,"track":track})
                if logical.placement_mode=="particle":
                    for property_id,track in sorted(logical.particle_settings.motion.tracks.items()):
                        if track.keyframes:property_rows.append({"kind":"property","layer_index":layer_index,"generated":generated,"logical":logical,"scope":"effect_motion","property_id":property_id,"track":track})
        self.rows=main_rows+property_rows
        self.table.setRowCount(len(self.rows));self.table.setColumnCount(frame_count+self.FRAME_COLUMN_OFFSET);self.table.setHorizontalHeaderLabels(["",localization.text("timeline.layer") if localization else "Layer"]+[str(index) for index in range(1,frame_count+1)]);self._visible_keys=set()
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
        selected_ids=set(selected_ids);logical_by_generated={item.generated_layer_id:item for item in project.effect_resource_layers}
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
