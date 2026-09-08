from PySide6.QtCore import QEvent, QMimeData, QRect, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import QApplication, QAbstractItemView, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu, QPushButton, QRubberBand, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from app.ui.timeline_scrub_controller import TimelineScrubController
from app.ui.tooltip_helper import apply_tooltip
from app.models.layer_group import LayerGroup
from app.models.layer_parenting import would_create_parent_cycle
from app.ui.hierarchy_display import (
    DROP_AFTER, DROP_BEFORE, DROP_INTO, build_hierarchy_rows, classify_drop_zone,
    context_action_states, drop_is_allowed, elide_text, layer_display_labels, resolve_drop_target,
)
from app.ui.layout_metrics import COMPACT_TOOL_BUTTON_SIZE, HIERARCHY_LABEL_WIDTH
from app.ui.timeline_multi_key import TimelineKey, TimelineKeySelection, clamp_group_delta, read_timeline_clipboard_payload, timeline_clipboard_matches
from app.ui.timeline_snapping import batch_delta_issue, collect_snap_targets, compute_batch_snap
from app.ui.timeline_time_view import TimelineTimeView,navigation_frame
from app.ui.timeline_command_bar import InactiveTimelineTable,command_group,command_separator


class LayerOrderTable(InactiveTimelineTable):
    """Timeline table that commits a layer move only when a drop completes."""
    layer_drop_requested=Signal(object,int)
    hierarchy_drop_requested=Signal(object,object,int)
    duplicate_requested=Signal()
    delete_requested=Signal();select_all_layers_requested=Signal()
    MIME="application/x-pixel-effect-resource-layer"

    def __init__(self,parent=None):
        super().__init__(parent);self.layer_rows=[];self.locked_ids=set();self.selected_layer_ids=set();self.node_kind={};self.node_parent={};self.sibling_order={};self.row_node_ids={};self._drop_feedback=None;self.setDragEnabled(True);self.setAcceptDrops(True);self.viewport().setAcceptDrops(True);self.setDropIndicatorShown(False);self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop);self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def startDrag(self,supported_actions):
        row=self.currentRow();record=next((value for value in self.layer_rows if value[0]==row),None)
        if record is None:return
        identifiers=[value for _row,value in self.layer_rows if value in self.selected_layer_ids] if record[1] in self.selected_layer_ids else [record[1]]
        if any(value in self.locked_ids for value in identifiers):return
        drag=QDrag(self);mime=self.model().mimeData(self.selectedIndexes()) or QMimeData();mime.setData(self.MIME,",".join(identifiers).encode());drag.setMimeData(mime);drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat(self.MIME):event.acceptProposedAction()
        else:super().dragEnterEvent(event)

    def dragMoveEvent(self,event):
        if event.mimeData().hasFormat(self.MIME):
            self._update_drop_feedback(event)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor if self._drop_feedback and self._drop_feedback[3] else Qt.CursorShape.ForbiddenCursor);self.viewport().update();event.acceptProposedAction()
        else:super().dragMoveEvent(event)

    def dropEvent(self,event):
        if not event.mimeData().hasFormat(self.MIME):super().dropEvent(event);return
        identifiers=self._drag_identifiers(event)
        if self._drop_feedback is None:self._update_drop_feedback(event)
        feedback=self._drop_feedback;self._clear_drop_feedback()
        if feedback and feedback[3] and feedback[2] is not None:
            parent_id,target=feedback[2];self.hierarchy_drop_requested.emit(identifiers,parent_id,target);event.setDropAction(Qt.DropAction.MoveAction);event.accept();return
        event.ignore()

    def dragLeaveEvent(self,event):
        self._clear_drop_feedback();super().dragLeaveEvent(event)

    def _drag_identifiers(self,event):
        return [value for value in bytes(event.mimeData().data(self.MIME)).decode().split(",") if value]

    def _update_drop_feedback(self,event):
        identifiers=self._drag_identifiers(event);point=event.position().toPoint();index=self.indexAt(point);target_id=self.row_node_ids.get(index.row()) if index.isValid() else None
        if target_id:
            rect=self.visualRect(self.model().index(index.row(),0));zone=classify_drop_zone(self.node_kind.get(target_id,"leaf"),point.y()-rect.top(),rect.height());allowed=drop_is_allowed(identifiers,target_id,zone,self.node_kind,self.node_parent,self.locked_ids);resolved=resolve_drop_target(target_id,zone,self.node_kind,self.node_parent,self.sibling_order,identifiers) if allowed else None;self._drop_feedback=(index.row(),zone,resolved,allowed)
        else:self._drop_feedback=None

    def _clear_drop_feedback(self):
        self._drop_feedback=None;self.viewport().unsetCursor();self.viewport().update()

    def paintEvent(self,event):
        super().paintEvent(event)
        if not self._drop_feedback:return
        row,zone,_resolved,allowed=self._drop_feedback;rect=self.visualRect(self.model().index(row,0));painter=QPainter(self.viewport());color=QColor("#74c0fc") if allowed else QColor("#fa5252");painter.setPen(QPen(color,2))
        if zone==DROP_INTO:painter.drawRect(1,rect.top()+1,self.viewport().width()-3,max(1,rect.height()-3))
        else:
            y=rect.top() if zone==DROP_BEFORE else rect.bottom();painter.drawLine(1,y,self.viewport().width()-2,y)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_D and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.duplicate_requested.emit();event.accept();return
        if event.key()==Qt.Key.Key_A and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.select_all_layers_requested.emit();event.accept();return
        if event.key()==Qt.Key.Key_Delete:self.delete_requested.emit();event.accept();return
        super().keyPressEvent(event)


class CompositionTimeline(QWidget):
    frame_selected = Signal(int)
    layer_selected = Signal(object)
    visibility_requested = Signal(str)
    play_requested = Signal()
    previous_requested = Signal()
    next_requested = Signal()
    delete_keyframe_requested = Signal(object)
    move_keyframe_requested = Signal(str,int,int)
    multi_key_move_requested=Signal(object,int)
    multi_key_duplicate_requested=Signal(object,int)
    multi_key_delete_requested=Signal(object)
    multi_key_easing_requested=Signal(object,str)
    multi_key_copy_requested=Signal(object)
    multi_key_paste_requested=Signal()
    add_layer_requested = Signal(str,str)
    remove_layer_requested = Signal(str)
    move_layer_requested = Signal(str,int)
    reorder_layer_requested = Signal(object,int)
    duplicate_layer_requested = Signal(str)
    lock_requested = Signal(str,bool)
    solo_requested = Signal(str,bool)
    selection_requested=Signal(str,object);select_all_requested=Signal();batch_command_requested=Signal(str)
    group_expanded_requested=Signal(str,bool)
    expand_all_requested=Signal();collapse_all_requested=Signal()
    hierarchy_drop_requested=Signal(object,object,int)
    parent_requested=Signal(str,object)
    scrub_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent); self.rows=[]; self.localization=None; self._playing=False; self._shortcuts=([],[],[]);self.key_selection=TimelineKeySelection();self._visible_keys=set();self._occupied_keys=set();self.clipboard_context_id="";self.reveal_mode="all";self.snap_enabled=True;self._time_view=TimelineTimeView();self._time_pan=None;self._key_drag=None;self._marquee=None;self._marquee_origin=None;self._marquee_ctrl=False; layout=QVBoxLayout(self);layout.setContentsMargins(6,6,6,6);layout.setSpacing(5)
        self.previous=QPushButton("◀"); self.play=QPushButton("▶"); self.play.setObjectName("resourceV2PlayButton"); self.next=QPushButton("▶|"); self.delete_keyframe=QPushButton()
        self.add_layer=QPushButton();self.add_layer.setObjectName("resourceV2AddLayerButton");self.add_layer_menu=QMenu(self.add_layer);self.add_layer.setMenu(self.add_layer_menu)
        self.remove_layer=QPushButton();self.remove_layer.setObjectName("resourceV2RemoveLayerButton");self.duplicate_layer=QPushButton();self.duplicate_layer.setObjectName("resourceV2DuplicateLayerButton");self.group_layer=QPushButton("Group");self.group_layer.setObjectName("resourceV2GroupButton");self.ungroup_layer=QPushButton("Ungroup");self.ungroup_layer.setObjectName("resourceV2UngroupButton");self.lock_layer=QPushButton("L");self.lock_layer.setCheckable(True);self.solo_layer=QPushButton("S");self.solo_layer.setCheckable(True);self.move_up=QPushButton("↑");self.move_up.setObjectName("resourceV2MoveLayerUpButton");self.move_down=QPushButton("↓");self.move_down.setObjectName("resourceV2MoveLayerDownButton")
        self.previous_key=QPushButton("◆◀");self.next_key=QPushButton("▶◆");self.fit_timeline_button=QPushButton("Fit All");self.fit_keys_button=QPushButton("Fit Keys");self.fit_selected_button=QPushButton("Fit Selected");self.reveal_combo=QComboBox();self.reveal_combo.addItems(["All","Animated","Selected Layer"]);self.snap_toggle=QPushButton("Snap");self.snap_toggle.setCheckable(True);self.snap_toggle.setChecked(True)
        self.delete_keyframe.setProperty("commandRole","danger");self.remove_layer.setProperty("commandRole","danger")
        self.previous.setText("|◀");self.next.setText("▶|");self.previous.setFixedWidth(34);self.play.setFixedWidth(34);self.next.setFixedWidth(34);self.previous_key.setFixedWidth(38);self.next_key.setFixedWidth(38);self.fit_timeline_button.setMinimumWidth(58);self.fit_keys_button.setMinimumWidth(64);self.fit_selected_button.setMinimumWidth(82);self.reveal_combo.setMinimumWidth(96);self.snap_toggle.setMinimumWidth(52)
        self.timeline_command_bar=QWidget(self);self.timeline_command_bar.setObjectName("resourceTimelineCommandBar");controls=QHBoxLayout(self.timeline_command_bar);controls.setContentsMargins(0,0,0,0);controls.setSpacing(5);self.timeline_command_groups={}
        for name,widgets in (("playback",(self.previous,self.play,self.next)),("key_navigation",(self.previous_key,self.next_key)),("view",(self.fit_timeline_button,self.fit_keys_button,self.fit_selected_button,self.reveal_combo)),("assist",(self.snap_toggle,)),("key_editing",(self.delete_keyframe,))):
            group=command_group(self.timeline_command_bar,name,widgets);self.timeline_command_groups[name]=group
            if controls.count():controls.addWidget(command_separator(self.timeline_command_bar))
            controls.addWidget(group)
        controls.addStretch();layout.addWidget(self.timeline_command_bar)
        for widget in (self.lock_layer,self.solo_layer,self.move_up,self.move_down):widget.setFixedSize(COMPACT_TOOL_BUTTON_SIZE,COMPACT_TOOL_BUTTON_SIZE)
        self.layer_command_bar=QWidget(self);self.layer_command_bar.setObjectName("resourceLayerCommandBar");layer_controls=QHBoxLayout(self.layer_command_bar);layer_controls.setContentsMargins(0,0,0,0);layer_controls.setSpacing(5);self.layer_command_groups={}
        for name,widgets in (("layer",(self.add_layer,self.duplicate_layer,self.remove_layer)),("hierarchy",(self.group_layer,self.ungroup_layer)),("state",(self.lock_layer,self.solo_layer)),("order",(self.move_up,self.move_down))):
            group=command_group(self.layer_command_bar,name,widgets);self.layer_command_groups[name]=group
            if layer_controls.count():layer_controls.addWidget(command_separator(self.layer_command_bar))
            layer_controls.addWidget(group)
        layer_controls.addStretch();layout.addWidget(self.layer_command_bar)
        self.key_selection_status=QLabel();self.key_selection_status.setObjectName("resourceKeySelectionStatus");layer_controls.addWidget(self.key_selection_status);self.selection_status=QPushButton();self.selection_status.setObjectName("resourceLayerSelectionStatus");self.selection_status.setFlat(True);self.selection_status.setEnabled(False);layer_controls.addWidget(self.selection_status)
        self.frame_cell_width=36; self.table=LayerOrderTable(); self.table.setObjectName("resourceV2CompositionTimeline"); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel); self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width);self.table.verticalHeader().setMinimumWidth(HIERARCHY_LABEL_WIDTH);self.table.verticalHeader().setMaximumWidth(360);self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self._snap_guide=QFrame(self.table.viewport());self._snap_guide.setStyleSheet(f"background:{self.table.palette().highlight().color().name()};");self._snap_guide.hide(); layout.addWidget(self.table)
        self.table.cellClicked.connect(self._clicked); self.table.verticalHeader().sectionClicked.connect(self._header_clicked)
        self.scrub_controller=TimelineScrubController(self.table,self._scrub_to,self.scrub_started.emit,self);self.table.viewport().installEventFilter(self);self.table.installEventFilter(self)
        self.previous.clicked.connect(self.previous_requested); self.next.clicked.connect(self.next_requested); self.play.clicked.connect(self.play_requested); self.delete_keyframe.clicked.connect(self._delete);self.previous_key.clicked.connect(lambda:self.navigate_key(-1));self.next_key.clicked.connect(lambda:self.navigate_key(1));self.fit_timeline_button.clicked.connect(self.fit_timeline);self.fit_keys_button.clicked.connect(self.fit_visible_keys);self.fit_selected_button.clicked.connect(self.fit_selected_keys);self.reveal_combo.currentIndexChanged.connect(lambda index:self.set_reveal_mode(("all","animated","selected")[index]));self.snap_toggle.toggled.connect(self.set_snap_enabled)
        self.remove_layer.clicked.connect(self._remove_selected_layer);self.duplicate_layer.clicked.connect(self._duplicate_selected_layer);self.group_layer.clicked.connect(lambda:self.batch_command_requested.emit("group"));self.ungroup_layer.clicked.connect(lambda:self.batch_command_requested.emit("ungroup"));self.lock_layer.clicked.connect(self._toggle_lock);self.solo_layer.clicked.connect(self._toggle_solo);self.move_up.clicked.connect(lambda:self._move_selected_layer(1));self.move_down.clicked.connect(lambda:self._move_selected_layer(-1));self.table.layer_drop_requested.connect(self.reorder_layer_requested);self.table.hierarchy_drop_requested.connect(self.hierarchy_drop_requested);self.table.duplicate_requested.connect(self._duplicate_selected_layer);self.table.delete_requested.connect(lambda:self.batch_command_requested.emit("delete"));self.table.select_all_layers_requested.connect(self.select_all_requested);self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.table.customContextMenuRequested.connect(self._context_menu)

    def set_available_sources(self,project):
        self.add_layer_menu.clear()
        for kind,items in (("source_asset",project.source_assets),("animation_clip",project.animation_clips)):
            for asset in items:
                action=QAction(asset.name,self.add_layer_menu);action.setData((kind,asset.id));action.triggered.connect(lambda checked=False,k=kind,i=asset.id:self.add_layer_requested.emit(k,i));self.add_layer_menu.addAction(action)
        self.add_layer.setEnabled(bool(self.add_layer_menu.actions()))

    def _scrub_to(self,row,column):
        self.table.setCurrentCell(row,column);self._clicked(row,column)

    def eventFilter(self,watched,event):
        if watched is self.table and event.type()==QEvent.Type.KeyPress:
            if event.modifiers()==(Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier) and event.key() in {Qt.Key.Key_Left,Qt.Key.Key_Right}:self.navigate_key(-1 if event.key()==Qt.Key.Key_Left else 1);return True
            control=event.modifiers()==Qt.KeyboardModifier.ControlModifier
            if control and event.key()==Qt.Key.Key_C and self.key_selection.selected:self.multi_key_copy_requested.emit(list(self.key_selection.selected));return True
            if control and event.key()==Qt.Key.Key_V and read_timeline_clipboard_payload() is not None:self.multi_key_paste_requested.emit();return True
            if self.key_selection.selected:
                if event.key()==Qt.Key.Key_Delete:self.multi_key_delete_requested.emit(list(self.key_selection.selected));return True
                if event.modifiers()&Qt.KeyboardModifier.AltModifier and event.key() in {Qt.Key.Key_Left,Qt.Key.Key_Right}:
                    self.multi_key_move_requested.emit(list(self.key_selection.selected),-1 if event.key()==Qt.Key.Key_Left else 1);return True
                if event.key()==Qt.Key.Key_Escape:self._cancel_key_gesture();return True
        if watched is self.table.viewport():
            if event.type()==QEvent.Type.Wheel and event.modifiers()&Qt.KeyboardModifier.ControlModifier:
                steps=1 if event.angleDelta().y()>0 else -1;self.zoom_time(steps,event.position().x());event.accept();return True
            if event.type()==QEvent.Type.Wheel and event.modifiers()&Qt.KeyboardModifier.ShiftModifier:
                bar=self.table.horizontalScrollBar();bar.setValue(bar.value()-event.angleDelta().y());event.accept();return True
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.MiddleButton:
                self._clear_snap_guide();self._time_pan=(event.position().x(),self.table.horizontalScrollBar().value());self.table.viewport().setCursor(Qt.CursorShape.ClosedHandCursor);event.accept();return True
            if event.type()==QEvent.Type.MouseMove and self._time_pan and event.buttons()&Qt.MouseButton.MiddleButton:
                start,value=self._time_pan;self.table.horizontalScrollBar().setValue(int(value-(event.position().x()-start)));event.accept();return True
            if event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.MiddleButton and self._time_pan:
                self._time_pan=None;self.table.viewport().unsetCursor();event.accept();return True
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                point=event.position().toPoint();index=self.table.indexAt(point);row=index.row();column=index.column();item=self.table.item(row,column) if index.isValid() else None;key=item.data(Qt.ItemDataRole.UserRole) if item else None
                if isinstance(key,TimelineKey) and not self._row_locked(row):
                    modifiers=event.modifiers();ctrl=bool(modifiers&Qt.KeyboardModifier.ControlModifier);shift=bool(modifiers&Qt.KeyboardModifier.ShiftModifier);preserve_click=key in self.key_selection.selected and not ctrl and not shift;track_keys=[value for value in self._visible_keys if value.track_id==key.track_id]
                    if not preserve_click:self.key_selection.click(key,ctrl=ctrl,shift=shift,track_keys=track_keys)
                    playhead_before=self._current_frame;self._key_drag=(key,column,point,False,None,(),preserve_click,None,playhead_before);self.table.setCurrentCell(row,column);self.frame_selected.emit(column);self._apply_key_visuals();event.accept();return True
                if index.isValid() and self._row_is_property(row):
                    self._clear_snap_guide();self._marquee_origin=point;self._marquee_ctrl=bool(event.modifiers()&Qt.KeyboardModifier.ControlModifier);self._marquee=QRubberBand(QRubberBand.Shape.Rectangle,self.table.viewport());self._marquee.setGeometry(QRect(point,point));self._marquee.show();event.accept();return True
            elif event.type()==QEvent.Type.MouseMove and self._key_drag and event.buttons()&Qt.MouseButton.LeftButton:
                key,column,start,was_dragged,duplicate,snapshot,preserve_click,snap_snapshot,playhead_before=self._drag_state();dragged=was_dragged or (event.position().toPoint()-start).manhattanLength()>=QApplication.startDragDistance()
                if dragged and not was_dragged:
                    duplicate=bool(event.modifiers()&Qt.KeyboardModifier.AltModifier);snapshot=tuple(self.key_selection.selected);snap_snapshot=collect_snap_targets(self._visible_keys,snapshot,playhead_before,self.table.columnCount()) if self.snap_enabled else None
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
                    if delta:
                        selected=list(snapshot or self.key_selection.selected)
                        if duplicate:self.multi_key_duplicate_requested.emit(selected,delta)
                        else:
                            self.multi_key_move_requested.emit(selected,delta)
                            if len(selected)==1:self.move_keyframe_requested.emit(selected[0].property_id,selected[0].frame,selected[0].frame+delta)
                event.accept();return True
            elif event.type()==QEvent.Type.MouseButtonRelease and self._marquee:
                rect=self._marquee.geometry();self._marquee.hide();self._marquee.deleteLater();self._marquee=None;keys=[]
                for row in range(self.table.rowCount()):
                    if not self._row_is_property(row):continue
                    for column in range(self.table.columnCount()):
                        item=self.table.item(row,column);key=item.data(Qt.ItemDataRole.UserRole) if item else None
                        if isinstance(key,TimelineKey) and rect.intersects(self.table.visualItemRect(item)):keys.append(key)
                self.key_selection.marquee(keys,ctrl=self._marquee_ctrl);self._apply_key_visuals();event.accept();return True
        return super().eventFilter(watched,event)

    def _row_is_property(self,row):return 0<=row<len(self.rows) and self.rows[row][1] is not None

    def _row_locked(self,row):
        return not 0<=row<len(self.rows) or bool(getattr(self.rows[row][0],"locked",False))

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
        palette=self.table.palette();selected_brush=palette.highlight();primary=self.key_selection.primary
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                item=self.table.item(row,column);key=item.data(Qt.ItemDataRole.UserRole) if item else None
                if item is not None and self._row_is_property(row):item.setText("◆" if isinstance(key,TimelineKey) else "·");item.setBackground(self.table.palette().alternateBase() if column==getattr(self,"_current_frame",-1) else self.table.palette().base())
                if not isinstance(key,TimelineKey):continue
                chosen=key in self.key_selection.selected;item.setBackground(selected_brush if chosen else self.table.palette().base());font=item.font();font.setBold(key==primary);item.setFont(font);item.setText("⬥" if key==primary else "◆")
        count=len(self.key_selection.selected);self.key_selection_status.setText((self.localization.text("timeline.keys_selected").format(count=count) if self.localization else f"{count} Keys Selected") if count else "")

    def _resolve_drag_delta(self,source_column,start_x,x,duplicate,keys,snap_snapshot):
        selected=set(keys);target=self.table.columnAt(int(x));target=(0 if x<0 else self.table.columnCount()-1) if target<0 else target;requested=target-source_column;base=requested if duplicate else clamp_group_delta(selected,requested,self.table.columnCount());snap=None
        if self.snap_enabled and snap_snapshot is not None:
            raw=(float(x)-float(start_x))/max(1,self.frame_cell_width);valid=lambda delta:batch_delta_issue(selected,delta,self.table.columnCount(),self._occupied_keys,duplicate) is None;snap=compute_batch_snap(snap_snapshot,selected,raw,base,self.frame_cell_width,valid)
        delta=snap.delta if snap else base;return delta,snap,batch_delta_issue(selected,delta,self.table.columnCount(),self._occupied_keys,duplicate)

    def _preview_key_drag(self,source_column,x,duplicate=False,keys=None,start_x=None,snap_snapshot=None):
        selected=set(keys or self.key_selection.selected);delta,snap,issue=self._resolve_drag_delta(source_column,x if start_x is None else start_x,x,duplicate,selected,snap_snapshot);noop=delta==0;invalid=not noop and issue is not None;self._apply_key_visuals();self.table.viewport().setCursor(Qt.CursorShape.ForbiddenCursor if invalid else Qt.CursorShape.DragCopyCursor if duplicate else Qt.CursorShape.SizeHorCursor);self._show_snap_guide(snap if not invalid else None)
        for key in selected:
            row=next((index for index,(layer,prop) in enumerate(self.rows) if getattr(layer,"id",None)==key.layer_id and prop==key.property_id),-1);source=self.table.item(row,key.frame) if row>=0 else None;destination=self.table.item(row,key.frame+delta) if row>=0 and 0<=key.frame+delta<self.table.columnCount() else None
            if source and not duplicate:source.setText("◇")
            if destination and not noop:destination.setText("×" if invalid else "+" if duplicate else "⬥");destination.setBackground(self.table.palette().alternateBase())
        count=len(selected);mode="Duplicate" if duplicate else "Move";suffix=" · No change" if noop else " · Boundary" if issue=="boundary" else " · Collision" if invalid else "";text=f"{count} Keys · {mode} · Δ {delta:+d}"+suffix
        if snap:text+=self._snap_status(snap)
        self.key_selection_status.setText(text)

    def _show_snap_guide(self,result):
        if result is None:self._clear_snap_guide();return
        first_x=self.table.horizontalHeader().sectionViewportPosition(0);x=int(round(self._time_view.frame_to_x(result.guide_frame,first_x,self.frame_cell_width)));self._snap_guide.setGeometry(x-1,0,2,self.table.viewport().height());self._snap_guide.raise_();self._snap_guide.show()

    def _clear_snap_guide(self):self._snap_guide.hide()
    def _snap_status(self,result):
        label=self.localization.text("timeline.snap_"+result.target_kind) if self.localization else result.target_kind.title();frame=self.localization.text("play.frame") if self.localization else "Frame";return f" · {label} · {frame} {result.guide_frame+1}"
    def set_snap_enabled(self,enabled):
        enabled=bool(enabled);changed=enabled!=self.snap_enabled;self.snap_enabled=enabled
        if self.snap_toggle.isChecked()!=enabled:self.snap_toggle.blockSignals(True);self.snap_toggle.setChecked(enabled);self.snap_toggle.blockSignals(False)
        self._clear_snap_guide();return changed

    def refresh(self, composition, selected_layer, frame, selected_ids=None, primary_id=None, expanded_ids=None):
        composition.repair_hierarchy();self._composition=composition;self._selected_layer_ref=selected_layer;self._current_frame=int(frame);primary_id=primary_id or (selected_layer.id if selected_layer else None);self.rows=[];self._child_rows=set()
        # The renderer composites later model entries over earlier ones. Reverse
        # the UI rows so list top means Canvas Front / Top.
        expanded_ids=set(expanded_ids or ());self._expanded_ids=expanded_ids;layer_by_id={layer.id:layer for layer in composition.layers};group_by_id={group.id:group for group in composition.groups};selected_ids=set(selected_ids or ({selected_layer.id} if selected_layer else set()));self._selected_ids=set(selected_ids);self._primary_id=primary_id
        display_rows=build_hierarchy_rows(composition.layers,composition.groups,composition.root_order,expanded_ids,selected_ids,primary_id,effective_locked=composition.effective_locked);display_by_id={value.identifier:value for value in display_rows}
        animated={layer.id for layer in composition.layers if any(track.keyframes for track in layer.tracks.values())};wanted={value for value in selected_ids if value in layer_by_id}
        for identifier in selected_ids:
            group=group_by_id.get(identifier)
            if group:wanted.update(group.children)
        if self.reveal_mode=="animated":display_rows=[display for display in display_rows if display.identifier in animated or display.kind=="group" and any(child in animated for child in group_by_id[display.identifier].children)]
        elif self.reveal_mode=="selected":display_rows=[display for display in display_rows if display.identifier in wanted or display.kind=="group" and any(child in wanted for child in group_by_id[display.identifier].children)]
        display_by_id={value.identifier:value for value in display_rows}
        for display in display_rows:
            value=group_by_id.get(display.identifier) if display.kind=="group" else layer_by_id[display.identifier];row=len(self.rows);self.rows.append((value,None))
            if display.depth:self._child_rows.add(row)
            if display.kind=="leaf":
                for property_id in value.tracks:
                    if self.reveal_mode=="animated" and not value.tracks[property_id].keyframes:continue
                    row=len(self.rows);self.rows.append((value,property_id))
                    if display.depth:self._child_rows.add(row)
        self._occupied_keys={TimelineKey(layer.id,"resource",property_id,key.frame) for layer in composition.layers for property_id,track in layer.tracks.items() for key in track.keyframes};self._visible_keys=set();self.table.blockSignals(True); self.table.clear(); self.table.setRowCount(len(self.rows)); self.table.setColumnCount(composition.frame_count);stride=max(1,(28+self.frame_cell_width-1)//self.frame_cell_width);self.table.setHorizontalHeaderLabels([str(index+1) if index%stride==0 else "" for index in range(composition.frame_count)])
        self.table.layer_rows=[(row,layer.id) for row,(layer,property_id) in enumerate(self.rows) if property_id is None]
        self.table.locked_ids={layer.id for layer in composition.layers if composition.effective_locked(layer)}|{group.id for group in composition.groups if group.locked or any(composition.effective_locked(layer_by_id[value]) for value in group.children)};self.table.selected_layer_ids=selected_ids
        self.table.node_kind={value.identifier:value.kind for value in display_rows};self.table.node_parent={value.identifier:value.group_id for value in display_rows};self.table.sibling_order={None:[node["id"] for node in reversed(composition.root_order)]}|{group.id:list(reversed(group.children)) for group in composition.groups};self.table.row_node_ids={row:layer.id for row,(layer,_property) in enumerate(self.rows)}
        headers=[]
        for row,(layer,property_id) in enumerate(self.rows):
            child=row in self._child_rows
            property_name=self.localization.text("property."+property_id) if self.localization and property_id else property_id
            display=display_by_id[layer.id]
            marker="▌" if display.primary else "•" if display.selected else " ";visible="●" if display.visible else "○";lock="L" if display.own_locked else "L*" if display.inherited_locked else " ";solo="S" if display.solo else " ";metrics=self.table.verticalHeader().fontMetrics()
            if isinstance(layer,LayerGroup):
                name=elide_text(metrics,layer.name,150);empty=(self.localization.text("hierarchy.empty") if self.localization else "Empty") if not display.child_count else str(display.child_count);headers.append(f"{'▼' if display.expanded else '▶'} {visible} {lock:2} {solo} {marker} [G] {name}  ({empty})")
            else:
                relation=f"  [P: {elide_text(metrics,display.parent_label,80)}]" if display.parent_label else "";name=elide_text(metrics,layer.name,135 if relation else 205)
                headers.append((("    " if child else "")+f"{visible} {lock:2} {solo} {marker} {name}{relation}") if property_id is None else ("        └ " if child else "    └ ")+property_name)
            for column in range(composition.frame_count):
                marker="" if isinstance(layer,LayerGroup) else "◆" if property_id and any(key.frame==column for key in layer.tracks[property_id].keyframes) else "■" if property_id is None and layer.start_frame<=column<=layer.end_frame else "·"
                item=QTableWidgetItem(marker); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if marker=="◆":key_id=TimelineKey(layer.id,"resource",property_id,column);item.setData(Qt.ItemDataRole.UserRole,key_id);self._visible_keys.add(key_id)
                self.table.setItem(row,column,item)
                if layer.id in selected_ids:item.setBackground(QBrush(QColor("#315a78" if layer.id==primary_id else "#29465b")))
        self.table.setVerticalHeaderLabels(headers)
        if self.localization:
            for row,(layer,property_id) in enumerate(self.rows):
                header=self.table.verticalHeaderItem(row)
                if header and property_id is None:
                    display=display_by_id[layer.id];parts=[layer.name]
                    if isinstance(layer,LayerGroup):parts.append(self.localization.text("hierarchy.group_tooltip"))
                    if display.parent_label:parts.append(self.localization.text("hierarchy.parent_tooltip").format(name=display.parent_label))
                    if display.own_locked:parts.append(self.localization.text("hierarchy.own_lock"))
                    elif display.inherited_locked:parts.append(self.localization.text("hierarchy.inherited_lock"))
                    header.setToolTip("\n".join(parts));font=header.font();font.setBold(isinstance(layer,LayerGroup) or display.primary);header.setFont(font)
        target=next((index for index,value in enumerate(self.rows) if value[0].id==primary_id),0) if self.rows else -1
        if target>=0: self.table.setCurrentCell(target,frame); self.table.scrollToItem(self.table.item(target,frame))
        self.key_selection.repair(self._visible_keys);self.table.blockSignals(False);self._apply_key_visuals()
        count=len(selected_ids);self.selection_status.setText((self.localization.text("layer.selection_count").format(count=count) if self.localization else f"{count} layers selected") if count>1 else "")
        self._sync_layer_controls()

    def set_frame_cell_width(self,width):
        self.frame_cell_width=self._time_view.clamp_width(width);self.table.horizontalHeader().setMinimumSectionSize(self._time_view.minimum_width);self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        for column in range(self.table.columnCount()):self.table.setColumnWidth(column,self.frame_cell_width)
        stride=max(1,(28+self.frame_cell_width-1)//self.frame_cell_width)
        for column in range(self.table.columnCount()):
            item=self.table.horizontalHeaderItem(column)
            if item:item.setText(str(column+1) if column%stride==0 else "")

    def zoom_time(self,steps,viewport_x):
        old=self.frame_cell_width;new=self._time_view.zoom_width(old,steps)
        if new==old:return False
        header=self.table.horizontalHeader();first_x=header.sectionViewportPosition(0) if self.table.columnCount() else 0;coordinate=self._time_view.frame_coordinate(viewport_x,first_x,old);self.set_frame_cell_width(new);new_first=header.sectionViewportPosition(0) if self.table.columnCount() else 0;bar=self.table.horizontalScrollBar();bar.setValue(int(round(bar.value()+self._time_view.anchored_scroll_delta(viewport_x,coordinate,new_first,new))));return True

    def _fit_range(self,frames):
        values=sorted(set(int(frame) for frame in frames))
        if not values:return False
        width=self._time_view.fit_width(self.table.viewport().width(),values[0],values[-1]);self.set_frame_cell_width(width);center=(values[0]+values[-1])/2;bar=self.table.horizontalScrollBar();bar.setValue(int(round((center+.5)*width-self.table.viewport().width()/2)));return True

    def fit_timeline(self):return self._fit_range(range(self.table.columnCount()))
    def fit_visible_keys(self):return self._fit_range(key.frame for key in self._visible_keys) or self.fit_timeline()
    def fit_selected_keys(self):return self._fit_range(key.frame for key in self.key_selection.selected)

    def navigate_key(self,direction):
        target=navigation_frame((key.frame for key in self._visible_keys),self._current_frame,direction)
        if target is None:return False
        self.frame_selected.emit(target);return True

    def set_reveal_mode(self,mode):
        mode=str(mode)
        if mode not in {"all","animated","selected"} or mode==self.reveal_mode:return False
        self.reveal_mode=mode
        if hasattr(self,"_composition"):self.refresh(self._composition,self._selected_layer_ref,self._current_frame,self._selected_ids,self._primary_id,self._expanded_ids)
        return True

    def _clicked(self,row,column):
        self.frame_selected.emit(column)
        if 0<=row<len(self.rows):
            identifier=self.rows[row][0].id;self.layer_selected.emit(identifier);self.selection_requested.emit(identifier,QApplication.keyboardModifiers())
        self._sync_layer_controls()

    def _header_clicked(self,row):
        if 0<=row<len(self.rows):
            layer,property_id=self.rows[row]
            if isinstance(layer,LayerGroup):self.group_expanded_requested.emit(layer.id,layer.id not in getattr(self,"_expanded_ids",set()))
            elif property_id is None:self.visibility_requested.emit(layer.id)

    def _delete(self):
        if self.key_selection.selected:self.multi_key_delete_requested.emit(list(self.key_selection.selected));return
        row=self.table.currentRow()
        if 0<=row<len(self.rows) and not self.rows[row][0].locked:self.delete_keyframe_requested.emit(self.rows[row][1])

    def _selected_layer(self):
        row=self.table.currentRow()
        return self.rows[row][0] if 0<=row<len(self.rows) else None

    def _remove_selected_layer(self):
        layer=self._selected_layer()
        if len(self.table.selected_layer_ids)>1 or isinstance(layer,LayerGroup):self.batch_command_requested.emit("delete")
        elif layer is not None:self.remove_layer_requested.emit(layer.id)

    def _duplicate_selected_layer(self):
        layer=self._selected_layer()
        if len(self.table.selected_layer_ids)>1 or isinstance(layer,LayerGroup):self.batch_command_requested.emit("duplicate")
        elif layer is not None:self.duplicate_layer_requested.emit(layer.id)

    def _move_selected_layer(self,direction):
        layer=self._selected_layer()
        if len(self.table.selected_layer_ids)>1 or isinstance(layer,LayerGroup):self.batch_command_requested.emit("front" if direction>0 else "back")
        elif layer is not None:self.move_layer_requested.emit(layer.id,int(direction))

    def _toggle_lock(self):
        layer=self._selected_layer()
        if len(self.table.selected_layer_ids)>1 or isinstance(layer,LayerGroup):self.batch_command_requested.emit("toggle_lock")
        elif layer:self.lock_requested.emit(layer.id,not layer.locked)

    def _toggle_solo(self):
        layer=self._selected_layer()
        if len(self.table.selected_layer_ids)>1 or isinstance(layer,LayerGroup):self.batch_command_requested.emit("toggle_solo")
        elif layer:self.solo_requested.emit(layer.id,not layer.solo)

    def _context_menu(self,pos):
        index=self.table.indexAt(pos)
        item=self.table.item(index.row(),index.column()) if index.isValid() else None;key=item.data(Qt.ItemDataRole.UserRole) if item else None
        if isinstance(key,TimelineKey) or index.isValid() and self._row_is_property(index.row()):
            if isinstance(key,TimelineKey) and key not in self.key_selection.selected:self.key_selection.click(key,track_keys=[value for value in self._visible_keys if value.track_id==key.track_id]);self._apply_key_visuals()
            menu=QMenu(self);copy_action=menu.addAction(self.localization.text("timeline.copy_keys") if self.localization else "Copy Keys");paste_action=menu.addAction(self.localization.text("timeline.paste_keys") if self.localization else "Paste Keys");copy_action.setEnabled(bool(self.key_selection.selected));paste_action.setEnabled(timeline_clipboard_matches("resource",self.clipboard_context_id));menu.addSeparator();delete=menu.addAction(self.localization.text("timeline.delete_selected_keys") if self.localization else "Delete Selected Keys");delete.setEnabled(bool(self.key_selection.selected));easing_menu=menu.addMenu(self.localization.text("property.easing") if self.localization else "Easing");easing_menu.setEnabled(bool(self.key_selection.selected));easing_actions={easing_menu.addAction(self.localization.text("easing."+name.lower().replace(" ","_").replace("/","_")) if self.localization else name):name for name in ("Linear","Ease In","Ease Out","Ease In/Out")};chosen=menu.exec(self.table.viewport().mapToGlobal(pos))
            if chosen is copy_action:self.multi_key_copy_requested.emit(list(self.key_selection.selected))
            elif chosen is paste_action:self.multi_key_paste_requested.emit()
            elif chosen is delete:self.multi_key_delete_requested.emit(list(self.key_selection.selected))
            elif chosen in easing_actions:self.multi_key_easing_requested.emit(list(self.key_selection.selected),easing_actions[chosen])
            return
        if index.isValid():
            clicked=next((value for row,value in self.table.layer_rows if row==index.row()),None)
            if clicked and clicked not in self.table.selected_layer_ids:
                self.selection_requested.emit(clicked,Qt.KeyboardModifier.NoModifier)
        layer=self._selected_layer()
        if not layer:return
        selected_count=len(self.table.selected_layer_ids);locked=any(value in self.table.locked_ids for value in self.table.selected_layer_ids);states=context_action_states("group" if isinstance(layer,LayerGroup) else "leaf",selected_count,locked,bool(getattr(layer,"parent_id",None)));menu=QMenu(self);actions={};actions["duplicate"]=menu.addAction(self.localization.text("layer.batch.duplicate"));actions["delete"]=menu.addAction(self.localization.text("layer.batch.delete"));menu.addSeparator();actions["group"]=menu.addAction(self.localization.text("group.group_selected"));actions["ungroup"]=menu.addAction(self.localization.text("group.ungroup"));menu.addSeparator()
        actions["group"].setEnabled(states["group"]);actions["ungroup"].setEnabled(states["ungroup"]);actions["delete"].setEnabled(states["delete"])
        parent_actions={}
        if not isinstance(layer,LayerGroup):
            parent_menu=menu.addMenu(self.localization.text("parent.set"));clear=menu.addAction(self.localization.text("parent.clear"));clear.setEnabled(states["clear_parent"]);parent_actions[clear]=None
            composition=getattr(self,"_composition",None)
            labels=layer_display_labels(composition.layers,composition.groups) if composition else {}
            for candidate in composition.layers if composition else ():
                if candidate.id!=layer.id and not would_create_parent_cycle(composition.layers,layer.id,candidate.id):
                    action=parent_menu.addAction(labels.get(candidate.id,candidate.name));action.setEnabled(states["set_parent"]);parent_actions[action]=candidate.id
        menu.addSeparator();state_key="show" if not layer.visible else "hide";lock_key="unlock" if layer.locked else "lock";solo_key="unsolo" if layer.solo else "solo"
        for key in (state_key,lock_key,solo_key):actions[key]=menu.addAction(self.localization.text("layer.batch."+key))
        menu.addSeparator();actions["front"]=menu.addAction(self.localization.text("layer.batch.front"));actions["back"]=menu.addAction(self.localization.text("layer.batch.back"));actions["front"].setEnabled(states["reorder"]);actions["back"].setEnabled(states["reorder"]);menu.addSeparator();actions["expand_all"]=menu.addAction(self.localization.text("hierarchy.expand_all"));actions["collapse_all"]=menu.addAction(self.localization.text("hierarchy.collapse_all"))
        chosen=menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen in parent_actions:self.parent_requested.emit(layer.id,parent_actions[chosen]);return
        command=next((key for key,value in actions.items() if value is chosen),None)
        if command=="expand_all":self.expand_all_requested.emit()
        elif command=="collapse_all":self.collapse_all_requested.emit()
        elif command:self.batch_command_requested.emit(command)

    def _sync_layer_controls(self):
        layer=self._selected_layer();enabled=layer is not None;selected=[value for _row,value in self.table.layer_rows if value in self.table.selected_layer_ids];any_locked=any(value in self.table.locked_ids for value in selected);all_locked=bool(selected) and all(value in self.table.locked_ids for value in selected);self.remove_layer.setEnabled(enabled and not any_locked);self.duplicate_layer.setEnabled(enabled);self.lock_layer.setEnabled(enabled);self.solo_layer.setEnabled(enabled);self.lock_layer.setChecked(all_locked);self.solo_layer.setChecked(bool(layer and layer.solo));self.delete_keyframe.setEnabled(enabled and not isinstance(layer,LayerGroup) and not layer.locked);self.group_layer.setEnabled(len(selected)>=2 and all(not isinstance(value,LayerGroup) for value in selected));self.ungroup_layer.setEnabled(len(selected)==1 and isinstance(layer,LayerGroup))
        layer_rows=[value[0] for value in self.rows if value[1] is None]
        index=layer_rows.index(layer) if layer in layer_rows else -1
        self.move_up.setEnabled(not any_locked and bool(selected));self.move_down.setEnabled(not any_locked and bool(selected))

    def set_playing(self,playing):
        self._playing=playing; self.play.setText("■" if playing else "▶")
        if self.localization:self._update_tooltips()

    def set_shortcuts(self,play,previous,next_):
        self._shortcuts=(play,previous,next_)
        if self.localization:self._update_tooltips()

    def _update_tooltips(self):
        play,previous,next_=self._shortcuts
        apply_tooltip(self.previous,self.localization,"tooltip.timeline.previous",previous)
        apply_tooltip(self.next,self.localization,"tooltip.timeline.next",next_)
        apply_tooltip(self.play,self.localization,"tooltip.timeline.pause" if self._playing else "tooltip.timeline.play",play)
        apply_tooltip(self.delete_keyframe,self.localization,"tooltip.timeline.delete_keyframe")
        apply_tooltip(self.table,self.localization,"tooltip.timeline.table",status=False)
        apply_tooltip(self.previous_key,self.localization,"tooltip.timeline.previous_key");apply_tooltip(self.next_key,self.localization,"tooltip.timeline.next_key");apply_tooltip(self.fit_timeline_button,self.localization,"tooltip.timeline.fit");apply_tooltip(self.fit_keys_button,self.localization,"tooltip.timeline.fit_keys");apply_tooltip(self.fit_selected_button,self.localization,"tooltip.timeline.fit_selected");apply_tooltip(self.reveal_combo,self.localization,"tooltip.timeline.reveal");apply_tooltip(self.snap_toggle,self.localization,"tooltip.timeline.snap")

    def retranslate(self,localization):
        self.localization=localization;self.fit_timeline_button.setText(localization.text("timeline.fit_timeline"));self.fit_keys_button.setText(localization.text("timeline.fit_visible_keys"));self.fit_selected_button.setText(localization.text("timeline.fit_selected_keys"));self.snap_toggle.setText(localization.text("timeline.snap"));self.snap_toggle.setAccessibleName(localization.text("timeline.snap"));self.reveal_combo.blockSignals(True);[self.reveal_combo.setItemText(index,localization.text(key)) for index,key in enumerate(("timeline.reveal_all","timeline.reveal_animated","timeline.reveal_selected"))];self.reveal_combo.blockSignals(False);self.delete_keyframe.setText(localization.text("composition.delete_keyframe"));self.add_layer.setText(localization.text("composition.add_layer"));self.duplicate_layer.setText(localization.text("composition.duplicate_layer"));self.remove_layer.setText(localization.text("composition.remove_layer"));self.group_layer.setText(localization.text("group.group_selected"));self.ungroup_layer.setText(localization.text("group.ungroup"));self.move_up.setToolTip(localization.text("tooltip.resource.layer_up"));self.move_down.setToolTip(localization.text("tooltip.resource.layer_down"));self.add_layer.setToolTip(localization.text("tooltip.resource.add_layer"));self.duplicate_layer.setToolTip(localization.text("tooltip.resource.duplicate_layer"));self.remove_layer.setToolTip(localization.text("tooltip.resource.remove_layer"));self.group_layer.setToolTip(localization.text("tooltip.group.create"));self.ungroup_layer.setToolTip(localization.text("tooltip.group.ungroup"));self.lock_layer.setToolTip(localization.text("tooltip.layer.lock"));self.solo_layer.setToolTip(localization.text("tooltip.layer.solo"));self.selection_status.setToolTip(localization.text("layer.multiselect_help"));self.previous.setAccessibleName(localization.text("timeline.previous_frame"));self.play.setAccessibleName(localization.text("tooltip.timeline.play"));self.next.setAccessibleName(localization.text("timeline.next_frame"));self.previous_key.setAccessibleName(localization.text("timeline.previous_key"));self.next_key.setAccessibleName(localization.text("timeline.next_key"));self.fit_timeline_button.setAccessibleName(localization.text("timeline.fit_timeline"));self.fit_keys_button.setAccessibleName(localization.text("timeline.fit_visible_keys"));self.fit_selected_button.setAccessibleName(localization.text("timeline.fit_selected_keys"));self.reveal_combo.setAccessibleName(localization.text("timeline.reveal"));self.lock_layer.setAccessibleName(localization.text("layer.lock"));self.solo_layer.setAccessibleName(localization.text("layer.solo"));self.move_up.setAccessibleName(localization.text("hierarchy.front"));self.move_down.setAccessibleName(localization.text("hierarchy.back"));self._update_tooltips();[widget.setAccessibleDescription(widget.toolTip()) for widget in (self.previous,self.play,self.next,self.add_layer,self.duplicate_layer,self.remove_layer,self.group_layer,self.ungroup_layer,self.lock_layer,self.solo_layer,self.move_up,self.move_down,self.previous_key,self.next_key,self.fit_timeline_button,self.fit_keys_button,self.fit_selected_button,self.reveal_combo,self.snap_toggle)]
