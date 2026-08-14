from PySide6.QtCore import QEvent, QMimeData, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QDrag
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHBoxLayout, QMenu, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from app.ui.timeline_scrub_controller import TimelineScrubController
from app.ui.tooltip_helper import apply_tooltip
from app.models.layer_group import LayerGroup
from app.models.layer_parenting import would_create_parent_cycle


class LayerOrderTable(QTableWidget):
    """Timeline table that commits a layer move only when a drop completes."""
    layer_drop_requested=Signal(object,int)
    duplicate_requested=Signal()
    delete_requested=Signal();select_all_layers_requested=Signal()
    MIME="application/x-pixel-effect-resource-layer"

    def __init__(self,parent=None):
        super().__init__(parent);self.layer_rows=[];self.locked_ids=set();self.selected_layer_ids=set();self.setDragEnabled(True);self.setAcceptDrops(True);self.viewport().setAcceptDrops(True);self.setDropIndicatorShown(True);self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop);self.setDefaultDropAction(Qt.DropAction.MoveAction)

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
        if event.mimeData().hasFormat(self.MIME):super().dragMoveEvent(event);event.acceptProposedAction();self.viewport().update()
        else:super().dragMoveEvent(event)

    def dropEvent(self,event):
        if not event.mimeData().hasFormat(self.MIME):super().dropEvent(event);return
        identifiers=[value for value in bytes(event.mimeData().data(self.MIME)).decode().split(",") if value];positions=[row for row,_identifier in self.layer_rows];y=event.position().y();target=len(positions)
        for index,row in enumerate(positions):
            rect=self.visualRect(self.model().index(row,0))
            if y<rect.center().y():target=index;break
        selected_positions=[index for index,(_row,value) in enumerate(self.layer_rows) if value in identifiers]
        target-=sum(1 for value in selected_positions if value<target)
        self.layer_drop_requested.emit(identifiers,max(0,min(target,max(0,len(positions)-len(identifiers)))));event.setDropAction(Qt.DropAction.MoveAction);event.accept()

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
    add_layer_requested = Signal(str,str)
    remove_layer_requested = Signal(str)
    move_layer_requested = Signal(str,int)
    reorder_layer_requested = Signal(object,int)
    duplicate_layer_requested = Signal(str)
    lock_requested = Signal(str,bool)
    solo_requested = Signal(str,bool)
    selection_requested=Signal(str,object);select_all_requested=Signal();batch_command_requested=Signal(str)
    group_expanded_requested=Signal(str,bool)
    parent_requested=Signal(str,object)
    scrub_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent); self.rows=[]; self.localization=None; self._playing=False; self._shortcuts=([],[],[]); layout=QVBoxLayout(self); controls=QHBoxLayout()
        self.previous=QPushButton("◀"); self.play=QPushButton("▶"); self.play.setObjectName("resourceV2PlayButton"); self.next=QPushButton("▶|"); self.delete_keyframe=QPushButton()
        self.add_layer=QPushButton();self.add_layer.setObjectName("resourceV2AddLayerButton");self.add_layer_menu=QMenu(self.add_layer);self.add_layer.setMenu(self.add_layer_menu)
        self.remove_layer=QPushButton();self.remove_layer.setObjectName("resourceV2RemoveLayerButton");self.duplicate_layer=QPushButton();self.duplicate_layer.setObjectName("resourceV2DuplicateLayerButton");self.group_layer=QPushButton("Group");self.group_layer.setObjectName("resourceV2GroupButton");self.ungroup_layer=QPushButton("Ungroup");self.ungroup_layer.setObjectName("resourceV2UngroupButton");self.lock_layer=QPushButton("L");self.lock_layer.setCheckable(True);self.solo_layer=QPushButton("S");self.solo_layer.setCheckable(True);self.move_up=QPushButton("↑");self.move_up.setObjectName("resourceV2MoveLayerUpButton");self.move_down=QPushButton("↓");self.move_down.setObjectName("resourceV2MoveLayerDownButton")
        for widget in (self.previous,self.play,self.next,self.delete_keyframe): controls.addWidget(widget)
        controls.addStretch(); layout.addLayout(controls)
        layer_controls=QHBoxLayout();layer_controls.addWidget(self.add_layer);layer_controls.addWidget(self.duplicate_layer);layer_controls.addWidget(self.remove_layer);layer_controls.addWidget(self.group_layer);layer_controls.addWidget(self.ungroup_layer);layer_controls.addWidget(self.lock_layer);layer_controls.addWidget(self.solo_layer);layer_controls.addWidget(self.move_up);layer_controls.addWidget(self.move_down);layer_controls.addStretch();layout.addLayout(layer_controls)
        self.selection_status=QPushButton();self.selection_status.setObjectName("resourceLayerSelectionStatus");self.selection_status.setFlat(True);self.selection_status.setEnabled(False);layer_controls.addWidget(self.selection_status)
        self.frame_cell_width=36; self.table=LayerOrderTable(); self.table.setObjectName("resourceV2CompositionTimeline"); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width); layout.addWidget(self.table)
        self.table.cellClicked.connect(self._clicked); self.table.verticalHeader().sectionClicked.connect(self._header_clicked)
        self.scrub_controller=TimelineScrubController(self.table,self._scrub_to,self.scrub_started.emit,self);self._key_drag=None;self.table.viewport().installEventFilter(self)
        self.previous.clicked.connect(self.previous_requested); self.next.clicked.connect(self.next_requested); self.play.clicked.connect(self.play_requested); self.delete_keyframe.clicked.connect(self._delete)
        self.remove_layer.clicked.connect(self._remove_selected_layer);self.duplicate_layer.clicked.connect(self._duplicate_selected_layer);self.group_layer.clicked.connect(lambda:self.batch_command_requested.emit("group"));self.ungroup_layer.clicked.connect(lambda:self.batch_command_requested.emit("ungroup"));self.lock_layer.clicked.connect(self._toggle_lock);self.solo_layer.clicked.connect(self._toggle_solo);self.move_up.clicked.connect(lambda:self._move_selected_layer(1));self.move_down.clicked.connect(lambda:self._move_selected_layer(-1));self.table.layer_drop_requested.connect(self.reorder_layer_requested);self.table.duplicate_requested.connect(self._duplicate_selected_layer);self.table.delete_requested.connect(lambda:self.batch_command_requested.emit("delete"));self.table.select_all_layers_requested.connect(self.select_all_requested);self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.table.customContextMenuRequested.connect(self._context_menu)

    def set_available_sources(self,project):
        self.add_layer_menu.clear()
        for kind,items in (("source_asset",project.source_assets),("animation_clip",project.animation_clips)):
            for asset in items:
                action=QAction(asset.name,self.add_layer_menu);action.setData((kind,asset.id));action.triggered.connect(lambda checked=False,k=kind,i=asset.id:self.add_layer_requested.emit(k,i));self.add_layer_menu.addAction(action)
        self.add_layer.setEnabled(bool(self.add_layer_menu.actions()))

    def _scrub_to(self,row,column):
        self.table.setCurrentCell(row,column);self._clicked(row,column)

    def eventFilter(self,watched,event):
        if watched is self.table.viewport():
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                index=self.table.indexAt(event.position().toPoint());row=index.row();column=index.column()
                if index.isValid() and 0<=row<len(self.rows) and not self.rows[row][0].locked and self.rows[row][1] is not None and self.table.item(row,column).text()=="◆":
                    self._key_drag=(row,column,event.position().toPoint(),False);self.table.setCurrentCell(row,column);self._clicked(row,column);event.accept();return True
            elif event.type()==QEvent.Type.MouseMove and self._key_drag and event.buttons()&Qt.MouseButton.LeftButton:
                row,column,start,_=self._key_drag;dragged=(event.position().toPoint()-start).manhattanLength()>=QApplication.startDragDistance();self._key_drag=(row,column,start,dragged);event.accept();return True
            elif event.type()==QEvent.Type.MouseButtonRelease and self._key_drag:
                row,source,_,dragged=self._key_drag;self._key_drag=None
                if dragged:
                    target=self.table.columnAt(int(event.position().x()))
                    if target<0:target=0 if event.position().x()<0 else self.table.columnCount()-1
                    target=max(0,min(self.table.columnCount()-1,target))
                    if target>=0 and target!=source:
                        property_id=self.rows[row][1];self.move_keyframe_requested.emit(property_id,source,target)
                event.accept();return True
        return super().eventFilter(watched,event)

    def refresh(self, composition, selected_layer, frame, selected_ids=None, primary_id=None, expanded_ids=None):
        composition.repair_hierarchy();self._composition=composition;primary_id=primary_id or (selected_layer.id if selected_layer else None);self.rows=[];self._child_rows=set()
        # The renderer composites later model entries over earlier ones. Reverse
        # the UI rows so list top means Canvas Front / Top.
        expanded_ids=set(expanded_ids or ());self._expanded_ids=expanded_ids;layer_by_id={layer.id:layer for layer in composition.layers};group_by_id={group.id:group for group in composition.groups}
        for node in reversed(composition.root_order):
            if node["type"]=="layer":nodes=[(layer_by_id[node["id"]],False)]
            else:
                group=group_by_id[node["id"]];nodes=[(group,False)]+([(layer_by_id[value],True) for value in reversed(group.children)] if group.id in expanded_ids else [])
            for value,child in nodes:
                row=len(self.rows);self.rows.append((value,None))
                if child:self._child_rows.add(row)
                if not isinstance(value,LayerGroup):
                    for property_id in value.tracks:
                        row=len(self.rows);self.rows.append((value,property_id))
                        if child:self._child_rows.add(row)
        self.table.blockSignals(True); self.table.clear(); self.table.setRowCount(len(self.rows)); self.table.setColumnCount(composition.frame_count); self.table.setHorizontalHeaderLabels([str(index+1) for index in range(composition.frame_count)])
        self.table.layer_rows=[(row,layer.id) for row,(layer,property_id) in enumerate(self.rows) if property_id is None]
        self.table.locked_ids={layer.id for layer in composition.layers if composition.effective_locked(layer)}|{group.id for group in composition.groups if group.locked or any(composition.effective_locked(layer_by_id[value]) for value in group.children)}
        selected_ids=set(selected_ids or ({selected_layer.id} if selected_layer else set()));self.table.selected_layer_ids=selected_ids
        headers=[]
        for row,(layer,property_id) in enumerate(self.rows):
            child=row in self._child_rows
            property_name=self.localization.text("property."+property_id) if self.localization and property_id else property_id
            if isinstance(layer,LayerGroup):headers.append(("▼ " if layer.id in expanded_ids else "▶ ")+("☑ " if layer.visible else "☐ ")+("🔒 " if layer.locked else "")+("S " if layer.solo else "")+f"📁 {layer.name}  {len(layer.children)}")
            else:
                parent=layer_by_id.get(layer.parent_id);relation=f"  ↳ {parent.name}" if parent else ""
                headers.append((("    " if child else "")+("☑ " if layer.visible else "☐ ")+("🔒 " if layer.locked else "")+("S " if layer.solo else "")+layer.name+relation) if property_id is None else ("      ↳ " if child else "  ↳ ")+property_name)
            for column in range(composition.frame_count):
                marker="" if isinstance(layer,LayerGroup) else "◆" if property_id and any(key.frame==column for key in layer.tracks[property_id].keyframes) else "■" if property_id is None and layer.start_frame<=column<=layer.end_frame else "·"
                item=QTableWidgetItem(marker); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(row,column,item)
                if layer.id in selected_ids:item.setBackground(QBrush(QColor("#315a78" if layer.id==primary_id else "#29465b")))
        self.table.setVerticalHeaderLabels(headers)
        if self.localization:
            for row,(layer,property_id) in enumerate(self.rows):
                header=self.table.verticalHeaderItem(row)
                if header and property_id is None:header.setToolTip(self.localization.text("tooltip.visibility.hide" if layer.visible else "tooltip.visibility.show"))
        target=next((index for index,value in enumerate(self.rows) if value[0].id==primary_id),0) if self.rows else -1
        if target>=0: self.table.setCurrentCell(target,frame); self.table.scrollToItem(self.table.item(target,frame))
        self.table.blockSignals(False)
        count=len(selected_ids);self.selection_status.setText((self.localization.text("layer.selection_count").format(count=count) if self.localization else f"{count} layers selected") if count>1 else "")
        self._sync_layer_controls()

    def set_frame_cell_width(self,width):
        self.frame_cell_width=max(20,min(96,int(width)));self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        for column in range(self.table.columnCount()):self.table.setColumnWidth(column,self.frame_cell_width)

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
        if index.isValid():
            clicked=next((value for row,value in self.table.layer_rows if row==index.row()),None)
            if clicked and clicked not in self.table.selected_layer_ids:
                self.selection_requested.emit(clicked,Qt.KeyboardModifier.NoModifier)
        layer=self._selected_layer()
        if not layer:return
        keys=("duplicate","lock","unlock","solo","unsolo","show","hide","front","back","delete");menu=QMenu(self);actions={key:menu.addAction(self.localization.text("layer.batch."+key)) for key in keys};actions["group"]=menu.addAction(self.localization.text("group.group_selected"));actions["ungroup"]=menu.addAction(self.localization.text("group.ungroup"))
        parent_actions={}
        if not isinstance(layer,LayerGroup):
            parent_menu=menu.addMenu(self.localization.text("parent.set"));clear=menu.addAction(self.localization.text("parent.clear"));clear.setEnabled(layer.parent_id is not None);parent_actions[clear]=None
            composition=getattr(self,"_composition",None)
            for candidate in composition.layers if composition else ():
                if candidate.id!=layer.id and not would_create_parent_cycle(composition.layers,layer.id,candidate.id):
                    action=parent_menu.addAction(candidate.name);parent_actions[action]=candidate.id
        chosen=menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen in parent_actions:self.parent_requested.emit(layer.id,parent_actions[chosen]);return
        command=next((key for key,value in actions.items() if value is chosen),None)
        if command:self.batch_command_requested.emit(command)

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

    def retranslate(self,localization):
        self.localization=localization;self.delete_keyframe.setText(localization.text("composition.delete_keyframe"));self.add_layer.setText(localization.text("composition.add_layer"));self.duplicate_layer.setText(localization.text("composition.duplicate_layer"));self.remove_layer.setText(localization.text("composition.remove_layer"));self.group_layer.setText(localization.text("group.group_selected"));self.ungroup_layer.setText(localization.text("group.ungroup"));self.move_up.setToolTip(localization.text("tooltip.resource.layer_up"));self.move_down.setToolTip(localization.text("tooltip.resource.layer_down"));self.add_layer.setToolTip(localization.text("tooltip.resource.add_layer"));self.duplicate_layer.setToolTip(localization.text("tooltip.resource.duplicate_layer"));self.remove_layer.setToolTip(localization.text("tooltip.resource.remove_layer"));self.group_layer.setToolTip(localization.text("tooltip.group.create"));self.ungroup_layer.setToolTip(localization.text("tooltip.group.ungroup"));self.lock_layer.setToolTip(localization.text("tooltip.layer.lock"));self.solo_layer.setToolTip(localization.text("tooltip.layer.solo"));self.selection_status.setToolTip(localization.text("layer.multiselect_help"));self._update_tooltips()
