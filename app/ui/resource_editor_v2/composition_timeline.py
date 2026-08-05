from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
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
    scrub_started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent); self.rows=[]; self.localization=None; self._playing=False; self._shortcuts=([],[],[]); layout=QVBoxLayout(self); controls=QHBoxLayout()
        self.previous=QPushButton("◀"); self.play=QPushButton("▶"); self.play.setObjectName("resourceV2PlayButton"); self.next=QPushButton("▶|"); self.delete_keyframe=QPushButton()
        for widget in (self.previous,self.play,self.next,self.delete_keyframe): controls.addWidget(widget)
        controls.addStretch(); layout.addLayout(controls)
        self.frame_cell_width=36; self.table=QTableWidget(); self.table.setObjectName("resourceV2CompositionTimeline"); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width); layout.addWidget(self.table)
        self.table.cellClicked.connect(self._clicked); self.table.verticalHeader().sectionClicked.connect(self._header_clicked)
        self.scrub_controller=TimelineScrubController(self.table,self._scrub_to,self.scrub_started.emit,self)
        self.previous.clicked.connect(self.previous_requested); self.next.clicked.connect(self.next_requested); self.play.clicked.connect(self.play_requested); self.delete_keyframe.clicked.connect(self._delete)

    def _scrub_to(self,row,column):
        self.table.setCurrentCell(row,column);self._clicked(row,column)

    def refresh(self, composition, selected_layer, frame):
        self.rows=[]
        for layer in composition.layers:
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

    def set_frame_cell_width(self,width):
        self.frame_cell_width=max(20,min(96,int(width)));self.table.horizontalHeader().setDefaultSectionSize(self.frame_cell_width)
        for column in range(self.table.columnCount()):self.table.setColumnWidth(column,self.frame_cell_width)

    def _clicked(self,row,column):
        self.frame_selected.emit(column)
        if 0<=row<len(self.rows): self.layer_selected.emit(self.rows[row][0].id)

    def _header_clicked(self,row):
        if 0<=row<len(self.rows):
            layer,property_id=self.rows[row]
            if property_id is None: self.visibility_requested.emit(layer.id)

    def _delete(self):
        row=self.table.currentRow(); self.delete_keyframe_requested.emit(self.rows[row][1] if 0<=row<len(self.rows) else None)

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
        self.localization=localization;self.delete_keyframe.setText(localization.text("composition.delete_keyframe"));self._update_tooltips()
