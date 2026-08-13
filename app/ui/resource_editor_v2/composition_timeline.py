from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHBoxLayout, QMenu, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from app.ui.timeline_scrub_controller import TimelineScrubController
from app.ui.tooltip_helper import apply_tooltip


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
    scrub_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent); self.rows=[]; self.localization=None; self._playing=False; self._shortcuts=([],[],[]); layout=QVBoxLayout(self); controls=QHBoxLayout()
        self.previous=QPushButton("◀"); self.play=QPushButton("▶"); self.play.setObjectName("resourceV2PlayButton"); self.next=QPushButton("▶|"); self.delete_keyframe=QPushButton()
        self.add_layer=QPushButton();self.add_layer.setObjectName("resourceV2AddLayerButton");self.add_layer_menu=QMenu(self.add_layer);self.add_layer.setMenu(self.add_layer_menu)
        self.remove_layer=QPushButton();self.remove_layer.setObjectName("resourceV2RemoveLayerButton");self.move_up=QPushButton("↑");self.move_up.setObjectName("resourceV2MoveLayerUpButton");self.move_down=QPushButton("↓");self.move_down.setObjectName("resourceV2MoveLayerDownButton")
        for widget in (self.previous,self.play,self.next,self.delete_keyframe): controls.addWidget(widget)
        controls.addStretch(); layout.addLayout(controls)
        layer_controls=QHBoxLayout();layer_controls.addWidget(self.add_layer);layer_controls.addWidget(self.remove_layer);layer_controls.addWidget(self.move_up);layer_controls.addWidget(self.move_down);layer_controls.addStretch();layout.addLayout(layer_controls)
        self.frame_cell_width=36; self.table=QTableWidget(); self.table.setObjectName("resourceV2CompositionTimeline"); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width); layout.addWidget(self.table)
        self.table.cellClicked.connect(self._clicked); self.table.verticalHeader().sectionClicked.connect(self._header_clicked)
        self.scrub_controller=TimelineScrubController(self.table,self._scrub_to,self.scrub_started.emit,self);self._key_drag=None;self.table.viewport().installEventFilter(self)
        self.previous.clicked.connect(self.previous_requested); self.next.clicked.connect(self.next_requested); self.play.clicked.connect(self.play_requested); self.delete_keyframe.clicked.connect(self._delete)
        self.remove_layer.clicked.connect(self._remove_selected_layer);self.move_up.clicked.connect(lambda:self._move_selected_layer(1));self.move_down.clicked.connect(lambda:self._move_selected_layer(-1))

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
                if index.isValid() and 0<=row<len(self.rows) and self.rows[row][1] is not None and self.table.item(row,column).text()=="◆":
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

    def refresh(self, composition, selected_layer, frame):
        self.rows=[]
        # The renderer composites later model entries over earlier ones. Reverse
        # the UI rows so list top means Canvas Front / Top.
        for layer in reversed(composition.layers):
            self.rows.append((layer,None))
            for property_id in layer.tracks: self.rows.append((layer,property_id))
        self.table.blockSignals(True); self.table.clear(); self.table.setRowCount(len(self.rows)); self.table.setColumnCount(composition.frame_count); self.table.setHorizontalHeaderLabels([str(index+1) for index in range(composition.frame_count)])
        headers=[]
        for row,(layer,property_id) in enumerate(self.rows):
            property_name=self.localization.text("property."+property_id) if self.localization and property_id else property_id
            headers.append(("☑ " if layer.visible else "☐ ")+layer.name if property_id is None else "  ↳ "+property_name)
            for column in range(composition.frame_count):
                marker="◆" if property_id and any(key.frame==column for key in layer.tracks[property_id].keyframes) else "■" if property_id is None and layer.start_frame<=column<=layer.end_frame else "·"
                item=QTableWidgetItem(marker); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(row,column,item)
        self.table.setVerticalHeaderLabels(headers)
        if self.localization:
            for row,(layer,property_id) in enumerate(self.rows):
                header=self.table.verticalHeaderItem(row)
                if header and property_id is None:header.setToolTip(self.localization.text("tooltip.visibility.hide" if layer.visible else "tooltip.visibility.show"))
        target=next((index for index,value in enumerate(self.rows) if value[0] is selected_layer),0) if self.rows else -1
        if target>=0: self.table.setCurrentCell(target,frame); self.table.scrollToItem(self.table.item(target,frame))
        self.table.blockSignals(False)
        self._sync_layer_controls()

    def set_frame_cell_width(self,width):
        self.frame_cell_width=max(20,min(96,int(width)));self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        for column in range(self.table.columnCount()):self.table.setColumnWidth(column,self.frame_cell_width)

    def _clicked(self,row,column):
        self.frame_selected.emit(column)
        if 0<=row<len(self.rows): self.layer_selected.emit(self.rows[row][0].id)
        self._sync_layer_controls()

    def _header_clicked(self,row):
        if 0<=row<len(self.rows):
            layer,property_id=self.rows[row]
            if property_id is None: self.visibility_requested.emit(layer.id)

    def _delete(self):
        row=self.table.currentRow(); self.delete_keyframe_requested.emit(self.rows[row][1] if 0<=row<len(self.rows) else None)

    def _selected_layer(self):
        row=self.table.currentRow()
        return self.rows[row][0] if 0<=row<len(self.rows) else None

    def _remove_selected_layer(self):
        layer=self._selected_layer()
        if layer is not None:self.remove_layer_requested.emit(layer.id)

    def _move_selected_layer(self,direction):
        layer=self._selected_layer()
        if layer is not None:self.move_layer_requested.emit(layer.id,int(direction))

    def _sync_layer_controls(self):
        layer=self._selected_layer();enabled=layer is not None;self.remove_layer.setEnabled(enabled)
        layer_rows=[value[0] for value in self.rows if value[1] is None]
        index=layer_rows.index(layer) if layer in layer_rows else -1
        self.move_up.setEnabled(index>0);self.move_down.setEnabled(index>=0 and index<len(layer_rows)-1)

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
        self.localization=localization;self.delete_keyframe.setText(localization.text("composition.delete_keyframe"));self.add_layer.setText(localization.text("composition.add_layer"));self.remove_layer.setText(localization.text("composition.remove_layer"));self.move_up.setToolTip(localization.text("tooltip.resource.layer_up"));self.move_down.setToolTip(localization.text("tooltip.resource.layer_down"));self.add_layer.setToolTip(localization.text("tooltip.resource.add_layer"));self.remove_layer.setToolTip(localization.text("tooltip.resource.remove_layer"));self._update_tooltips()
