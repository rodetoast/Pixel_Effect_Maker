"""Source Asset and generator library panel."""

from __future__ import annotations

import numpy as np
from dataclasses import replace
from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QAction, QColor, QDrag, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QApplication,
    QLabel,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.project import Project
from app.models.layer_group import LayerGroup
from app.models.layer_parenting import would_create_parent_cycle
from app.models.source_asset import SourceAsset
from app.ui.tooltip_helper import apply_tooltip
from app.ui.hierarchy_display import (
    DROP_AFTER, DROP_BEFORE, DROP_INTO, build_hierarchy_rows, classify_drop_zone,
    context_action_states, drop_is_allowed, elide_text, layer_display_labels, resolve_drop_target,
)
from app.ui.layout_metrics import EFFECT_LIBRARY_MIN_WIDTH


class EffectLayerList(QListWidget):
    """Effect list whose internal drag is committed by the project owner."""
    layer_drop_requested=Signal(object,int)
    hierarchy_drop_requested=Signal(object,object,int)
    duplicate_requested=Signal()
    delete_requested=Signal();select_all_layers_requested=Signal()
    disclosure_requested=Signal(str)
    MIME="application/x-pixel-effect-effect-layer"

    def __init__(self,parent=None):
        super().__init__(parent);self.locked_ids=set();self.selected_layer_ids=set();self.node_kind={};self.node_parent={};self.sibling_order={};self._drop_feedback=None;self.setDragEnabled(True);self.setAcceptDrops(True);self.viewport().setAcceptDrops(True);self.setDropIndicatorShown(False);self.setDragDropMode(QListWidget.DragDropMode.DragDrop);self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def startDrag(self,supported_actions):
        item=self.currentItem()
        if item is None:return
        identifier=str(item.data(Qt.ItemDataRole.UserRole));identifiers=[str(self.item(index).data(Qt.ItemDataRole.UserRole)) for index in range(self.count()) if str(self.item(index).data(Qt.ItemDataRole.UserRole)) in self.selected_layer_ids] if identifier in self.selected_layer_ids else [identifier]
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

    def dragLeaveEvent(self,event):self._clear_drop_feedback();super().dragLeaveEvent(event)

    def _drag_identifiers(self,event):return [value for value in bytes(event.mimeData().data(self.MIME)).decode().split(",") if value]

    def _update_drop_feedback(self,event):
        identifiers=self._drag_identifiers(event);point=event.position().toPoint();item=self.itemAt(point);target_id=str(item.data(Qt.ItemDataRole.UserRole)) if item else None
        if target_id:
            rect=self.visualItemRect(item);zone=classify_drop_zone(self.node_kind.get(target_id,"leaf"),point.y()-rect.top(),rect.height());allowed=drop_is_allowed(identifiers,target_id,zone,self.node_kind,self.node_parent,self.locked_ids);resolved=resolve_drop_target(target_id,zone,self.node_kind,self.node_parent,self.sibling_order,identifiers) if allowed else None;self._drop_feedback=(target_id,zone,resolved,allowed)
        else:self._drop_feedback=None

    def _clear_drop_feedback(self):self._drop_feedback=None;self.viewport().unsetCursor();self.viewport().update()

    def paintEvent(self,event):
        super().paintEvent(event)
        if not self._drop_feedback:return
        target_id,zone,_resolved,allowed=self._drop_feedback;item=next((self.item(index) for index in range(self.count()) if str(self.item(index).data(Qt.ItemDataRole.UserRole))==target_id),None)
        if item is None:return
        rect=self.visualItemRect(item);painter=QPainter(self.viewport());color=QColor("#74c0fc") if allowed else QColor("#fa5252");painter.setPen(QPen(color,2))
        if zone==DROP_INTO:painter.drawRect(1,rect.top()+1,self.viewport().width()-3,max(1,rect.height()-3))
        else:
            y=rect.top() if zone==DROP_BEFORE else rect.bottom();painter.drawLine(1,y,self.viewport().width()-2,y)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_D and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.duplicate_requested.emit();event.accept();return
        if event.key()==Qt.Key.Key_A and event.modifiers()&Qt.KeyboardModifier.ControlModifier:self.select_all_layers_requested.emit();event.accept();return
        if event.key()==Qt.Key.Key_Delete:self.delete_requested.emit();event.accept();return
        super().keyPressEvent(event)

    def mousePressEvent(self,event):
        item=self.itemAt(event.position().toPoint())
        if event.button()==Qt.MouseButton.LeftButton and event.position().x()<=36 and item is not None:
            identifier=str(item.data(Qt.ItemDataRole.UserRole))
            if self.node_kind.get(identifier)=="group":self.disclosure_requested.emit(identifier);event.accept();return
        super().mousePressEvent(event)


class EffectLibraryPanel(QWidget):
    import_requested = Signal()
    add_emitter_requested = Signal()
    asset_selected = Signal(str)
    generator_selected = Signal(str)
    delete_asset_requested = Signal(str)
    delete_generator_requested = Signal(str)
    create_clip_requested = Signal(str)
    clip_selected = Signal(str)
    particle_selected = Signal(str)
    add_particle_requested = Signal(str)
    add_particle_from_resource_requested = Signal(str, str)
    add_composition_requested = Signal(str)
    composition_selected = Signal(str)
    resource_open_requested = Signal(str, str)
    remove_resource_layer_requested = Signal(str)
    move_resource_layer_requested = Signal(str, int)
    reorder_resource_layer_requested = Signal(object, int)
    duplicate_resource_layer_requested = Signal(str)
    lock_resource_layer_requested = Signal(str,bool)
    solo_resource_layer_requested = Signal(str,bool)
    resource_layer_selection_requested=Signal(str,object)
    select_all_resource_layers_requested=Signal()
    batch_resource_layer_requested=Signal(str)
    group_expanded_requested=Signal(str)
    expand_all_requested=Signal();collapse_all_requested=Signal();hierarchy_drop_requested=Signal(object,object,int)
    parent_requested=Signal(str,object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(EFFECT_LIBRARY_MIN_WIDTH)
        self.setMaximumWidth(360)
        outer_layout=QVBoxLayout(self);outer_layout.setContentsMargins(0,0,0,0)
        self.scroll_area=QScrollArea();self.scroll_area.setObjectName("effectLibraryScrollArea");self.scroll_area.setWidgetResizable(True);self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_body=QWidget();scroll_body.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);layout=QVBoxLayout(scroll_body);layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint);self.scroll_area.setWidget(scroll_body);outer_layout.addWidget(self.scroll_area)
        self.title_label = QLabel("Effect Library")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(self.title_label)

        self.source_group = QGroupBox("Source Assets")
        source_layout = QVBoxLayout(self.source_group)
        self.import_button = QPushButton("Import Source Asset…")
        self.asset_list = QListWidget()
        self.asset_list.setObjectName("sourceAssetList")
        self.source_preview = QLabel("No source selected")
        self.source_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.source_preview.setMinimumHeight(112)
        self.source_preview.setStyleSheet("background: #252a31; color: #adb5bd;")
        self.source_info = QLabel("")
        self.delete_asset_button = QPushButton("Delete Source")
        source_layout.addWidget(self.import_button)
        source_layout.addWidget(self.asset_list)
        source_layout.addWidget(self.source_preview)
        source_layout.addWidget(self.source_info)
        source_layout.addWidget(self.delete_asset_button)
        layout.addWidget(self.source_group, 1)

        self.generator_group = QGroupBox("Legacy Clip Generators")
        generator_layout = QVBoxLayout(self.generator_group)
        self.add_emitter_button = QPushButton("Add Transform Emitter")
        self.generator_list = QListWidget()
        self.generator_list.setObjectName("generatorList")
        self.delete_generator_button = QPushButton("Delete Generator")
        generator_layout.addWidget(self.add_emitter_button)
        generator_layout.addWidget(self.generator_list)
        generator_layout.addWidget(self.delete_generator_button)
        layout.addWidget(self.generator_group, 1)

        self.clip_group = QGroupBox("Animated Resources")
        clip_layout = QVBoxLayout(self.clip_group)
        self.create_clip_button = QPushButton("Create Animated Resource")
        self.clip_list = QListWidget(); self.clip_list.setObjectName("animationClipList")
        clip_layout.addWidget(self.create_clip_button); clip_layout.addWidget(self.clip_list)
        layout.addWidget(self.clip_group, 1)

        self.composition_group = QGroupBox("Resource Layers")
        composition_layout = QVBoxLayout(self.composition_group)
        self.add_composition_button = QPushButton("Add Resource Layer")
        self.composition_list = EffectLayerList(); self.composition_list.setObjectName("compositionLayerList");self.composition_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.composition_add_menu=QMenu(self.add_composition_button);self.add_composition_button.setMenu(self.composition_add_menu)
        self.group_composition_button=QPushButton("Group Selected");self.ungroup_composition_button=QPushButton("Ungroup")
        self.duplicate_composition_button=QPushButton("Duplicate Layer");self.duplicate_composition_button.setObjectName("duplicateEffectLayerButton");self.remove_composition_button=QPushButton("Remove Layer");self.lock_composition_button=QPushButton("L");self.lock_composition_button.setCheckable(True);self.solo_composition_button=QPushButton("S");self.solo_composition_button.setCheckable(True);self.move_composition_up=QPushButton("↑ Front");self.move_composition_down=QPushButton("↓ Back")
        self.composition_selection_label=QLabel();composition_layout.addWidget(self.add_composition_button); composition_layout.addWidget(self.composition_list);composition_layout.addWidget(self.composition_selection_label);composition_layout.addWidget(self.group_composition_button);composition_layout.addWidget(self.ungroup_composition_button);composition_layout.addWidget(self.duplicate_composition_button);composition_layout.addWidget(self.remove_composition_button);composition_layout.addWidget(self.lock_composition_button);composition_layout.addWidget(self.solo_composition_button);composition_layout.addWidget(self.move_composition_up);composition_layout.addWidget(self.move_composition_down)
        layout.addWidget(self.composition_group, 1)

        self.particle_group = QGroupBox("Particle Systems")
        particle_layout = QVBoxLayout(self.particle_group)
        self.add_particle_button = QPushButton("Add Particle System")
        self.particle_list = QListWidget(); self.particle_list.setObjectName("particleEmitterList")
        particle_layout.addWidget(self.add_particle_button); particle_layout.addWidget(self.particle_list)
        layout.addWidget(self.particle_group, 1)
        self.particle_group.hide()

        self.import_button.clicked.connect(self.import_requested)
        self.add_emitter_button.clicked.connect(self.add_emitter_requested)
        self.asset_list.currentItemChanged.connect(self._asset_changed)
        self.generator_list.currentItemChanged.connect(self._generator_changed)
        self.delete_asset_button.clicked.connect(self._request_delete_asset)
        self.delete_generator_button.clicked.connect(self._request_delete_generator)
        self.create_clip_button.clicked.connect(self._request_create_clip)
        self.add_particle_button.clicked.connect(self._request_add_particle)
        self.duplicate_composition_button.clicked.connect(self._request_duplicate_composition);self.remove_composition_button.clicked.connect(self._request_remove_composition);self.lock_composition_button.clicked.connect(self._request_lock_composition);self.solo_composition_button.clicked.connect(self._request_solo_composition);self.move_composition_up.clicked.connect(lambda:self._request_move_composition(1));self.move_composition_down.clicked.connect(lambda:self._request_move_composition(-1));self.composition_list.layer_drop_requested.connect(self.reorder_resource_layer_requested);self.composition_list.hierarchy_drop_requested.connect(self.hierarchy_drop_requested);self.composition_list.duplicate_requested.connect(self._request_duplicate_composition);self.composition_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.composition_list.customContextMenuRequested.connect(self._composition_context_menu)
        self.group_composition_button.clicked.connect(lambda:self.batch_resource_layer_requested.emit("group"));self.ungroup_composition_button.clicked.connect(lambda:self.batch_resource_layer_requested.emit("ungroup"));self.composition_list.disclosure_requested.connect(self.group_expanded_requested)
        self.clip_list.currentItemChanged.connect(lambda item, previous: self._typed_changed(item, "clip"))
        self.particle_list.currentItemChanged.connect(lambda item, previous: self._typed_changed(item, "particle"))
        self.composition_list.currentItemChanged.connect(lambda item, previous:self._sync_composition_controls())
        self.composition_list.itemClicked.connect(lambda item:self.resource_layer_selection_requested.emit(str(item.data(Qt.ItemDataRole.UserRole)),QApplication.keyboardModifiers()))
        self.composition_list.itemDoubleClicked.connect(self._composition_double_clicked)
        self.asset_list.itemDoubleClicked.connect(lambda item:self.resource_open_requested.emit("source_asset",str(item.data(Qt.ItemDataRole.UserRole))))
        self.clip_list.itemDoubleClicked.connect(lambda item:self.resource_open_requested.emit("animation_clip",str(item.data(Qt.ItemDataRole.UserRole))))
        self._configure_help()
        self._selected_resource_ids=set();self._primary_resource_id=None;self.composition_list.select_all_layers_requested.connect(self.select_all_resource_layers_requested);self.composition_list.delete_requested.connect(lambda:self.batch_resource_layer_requested.emit("delete"))

    def _configure_help(self) -> None:
        help_text = {
            self.import_button: "Import a PNG as a non-destructive project Source Asset.",
            self.asset_list: "Select an embedded source image and inspect its thumbnail.",
            self.add_emitter_button: "Create a Transform Emitter using the selected Source Asset.",
            self.generator_list: "Select a generator to edit its draft settings and preview.",
            self.delete_asset_button: "Delete an unused Source Asset after confirmation.",
            self.delete_generator_button: "Delete the generator and its dedicated Generated Layer.",
        }
        for widget, text in help_text.items():
            widget.setToolTip(text)
            widget.setStatusTip(text)

    def retranslate_ui(self, localization) -> None:
        self._localization = localization
        t = localization.text
        self.title_label.setText(t("effects.library.title"))
        self.source_group.setTitle(t("effects.sources"))
        self.generator_group.setTitle(t("effects.legacy_clip_generators"))
        self.clip_group.setTitle(t("effects.animated_resources"))
        self.composition_group.setTitle(t("resource_layer.plural"))
        self.create_clip_button.setText(t("effects.create_clip"))
        self.add_composition_button.setText(t("resource_layer.add"))
        self.duplicate_composition_button.setText(t("resource_layer.duplicate"));self.remove_composition_button.setText(t("resource_layer.remove"));self.move_composition_up.setText(t("resource_layer.move_front"));self.move_composition_down.setText(t("resource_layer.move_back"))
        self.group_composition_button.setText(t("group.group_selected"));self.ungroup_composition_button.setText(t("group.ungroup"))
        self.group_composition_button.setToolTip(t("tooltip.group.create"));self.ungroup_composition_button.setToolTip(t("tooltip.group.ungroup"))
        self.import_button.setText(t("effects.import"))
        self.add_emitter_button.setText(t("effects.add_emitter"))
        self.delete_asset_button.setText(t("effects.delete_source"))
        self.delete_generator_button.setText(t("effects.delete_generator"))
        help_keys = {
            self.import_button: "tooltip.effect.import", self.asset_list: "tooltip.effect.source_list",
            self.add_emitter_button: "tooltip.effect.add_transform", self.delete_asset_button: "tooltip.effect.delete_source",
            self.delete_generator_button: "tooltip.effect.delete_generator", self.create_clip_button: "tooltip.effect.create_clip",
            self.add_particle_button: "tooltip.resource_layer.add",
            self.add_composition_button: "tooltip.resource_layer.add",
            self.duplicate_composition_button: "tooltip.resource_layer.duplicate",
            self.remove_composition_button: "tooltip.resource_layer.remove",
            self.move_composition_up: "tooltip.resource_layer.move_front",
            self.move_composition_down: "tooltip.resource_layer.move_back",
            self.lock_composition_button: "tooltip.layer.lock", self.solo_composition_button: "tooltip.layer.solo",
        }
        for widget,key in help_keys.items():apply_tooltip(widget,localization,key)
        self.lock_composition_button.setAccessibleName(t("layer.lock"));self.solo_composition_button.setAccessibleName(t("layer.solo"));self.move_composition_up.setAccessibleName(t("hierarchy.front"));self.move_composition_down.setAccessibleName(t("hierarchy.back"));self.composition_list.setAccessibleName(t("hierarchy.effect_layers"))
        if self.current_asset_id() is None:
            self.source_preview.setText(t("effects.no_source"))

    @staticmethod
    def _item(identifier: str, name: str) -> QListWidgetItem:
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, identifier)
        return item

    def refresh(self, project: Project, expanded_group_ids=None) -> None:
        self._project=project
        selected_asset = self.current_asset_id()
        selected_generator = self.current_generator_id()
        selected_clip = self.current_clip_id(); selected_particle = self.current_particle_id(); selected_composition = self.current_composition_id()
        self.asset_list.blockSignals(True)
        self.generator_list.blockSignals(True)
        self.asset_list.clear()
        self.generator_list.clear()
        self.clip_list.blockSignals(True); self.particle_list.blockSignals(True); self.composition_list.blockSignals(True)
        self.clip_list.clear(); self.particle_list.clear(); self.composition_list.clear()
        for asset in project.source_assets:
            self.asset_list.addItem(self._item(asset.id, asset.name))
        for generator in project.generators:
            self.generator_list.addItem(self._item(generator.id, generator.name))
        for clip in project.animation_clips: self.clip_list.addItem(self._item(clip.id, clip.name))
        resource_names={item.id:item.name for item in project.resource_compositions}
        generated_by_id={item.id:item for item in project.layers}
        expanded=set(expanded_group_ids or ());layers={item.id:item for item in project.effect_resource_layers};groups={item.id:item for item in project.effect_layer_groups}
        self._resource_layers={**layers,**groups};self.composition_list.locked_ids={node_id for node_id in layers if project.effect_effective_locked(layers[node_id])}|{group.id for group in groups.values() if group.locked}
        display_rows=build_hierarchy_rows(project.effect_resource_layers,project.effect_layer_groups,project.effect_root_order,expanded,self._selected_resource_ids,self._primary_resource_id,visibility=lambda layer:generated_by_id.get(layer.generated_layer_id).visible if layer.generated_layer_id in generated_by_id else layer.visible,effective_locked=project.effect_effective_locked)
        self._display_rows={display.identifier:display for display in display_rows};self._resource_names=resource_names
        for display in display_rows:
            item=self._item(display.identifier,self._format_resource_row(display));item.setData(Qt.ItemDataRole.UserRole+1,display);item.setToolTip(self._resource_row_tooltip(display));font=item.font();font.setBold(display.kind=="group" or display.primary);item.setFont(font);self.composition_list.addItem(item)
        self.composition_list.node_kind={display.identifier:display.kind for display in display_rows};self.composition_list.node_parent={display.identifier:display.group_id for display in display_rows};self.composition_list.sibling_order={None:[node["id"] for node in reversed(project.effect_root_order)]}|{group.id:list(reversed(group.children)) for group in project.effect_layer_groups}
        self._restore_selection(self.asset_list, selected_asset)
        self._restore_selection(self.generator_list, selected_generator)
        self._restore_selection(self.clip_list, selected_clip); self._restore_selection(self.particle_list, selected_particle); self._restore_selection(self.composition_list, selected_composition)
        self.set_resource_selection(self._selected_resource_ids,self._primary_resource_id)
        self.asset_list.blockSignals(False)
        self.generator_list.blockSignals(False)
        self.clip_list.blockSignals(False); self.particle_list.blockSignals(False); self.composition_list.blockSignals(False)
        self.add_emitter_button.setEnabled(bool(project.source_assets))
        self.add_emitter_button.setVisible(False)
        self.generator_group.setVisible(bool(project.generators))
        self.delete_asset_button.setEnabled(self.current_asset_id() is not None)
        self.delete_generator_button.setEnabled(
            self.current_generator_id() is not None
        )
        self.create_clip_button.setEnabled(self.current_generator_id() is not None)
        self.add_particle_button.setEnabled(False)
        self._resource_composition_ids = [item.id for item in project.resource_compositions]
        self.composition_add_menu.clear()
        for composition in project.resource_compositions:
            action=QAction(composition.name,self.composition_add_menu);action.triggered.connect(lambda checked=False,i=composition.id:self.add_composition_requested.emit(i));self.composition_add_menu.addAction(action)
        self.add_composition_button.setEnabled(bool(project.resource_compositions))
        self.particle_group.setVisible(False)
        self._resource_composition_ids = [item.id for item in project.resource_compositions]
        asset = next(
            (item for item in project.source_assets if item.id == self.current_asset_id()),
            None,
        )
        self.show_asset(asset)
        self._sync_composition_controls()

    @staticmethod
    def _restore_selection(widget: QListWidget, identifier: str | None) -> None:
        if identifier is None:
            return
        for row in range(widget.count()):
            if widget.item(row).data(Qt.ItemDataRole.UserRole) == identifier:
                widget.setCurrentRow(row)
                return

    def select_asset(self, identifier: str) -> None:
        self._restore_selection(self.asset_list, identifier)

    def select_generator(self, identifier: str) -> None:
        self._restore_selection(self.generator_list, identifier)

    def select_composition(self, identifier: str) -> None:
        self.set_resource_selection({identifier},identifier)
        self._sync_composition_controls()

    def set_resource_selection(self,identifiers,primary):
        self._selected_resource_ids=set(identifiers);self._primary_resource_id=primary;self.composition_list.selected_layer_ids=set(identifiers);blocked=self.composition_list.blockSignals(True)
        for row in range(self.composition_list.count()):
            item=self.composition_list.item(row);identifier=str(item.data(Qt.ItemDataRole.UserRole));selected=identifier in self._selected_resource_ids;item.setSelected(selected);display=item.data(Qt.ItemDataRole.UserRole+1)
            if display is not None:display=replace(display,selected=selected,primary=identifier==primary);item.setData(Qt.ItemDataRole.UserRole+1,display);item.setText(self._format_resource_row(display))
            font=item.font();font.setBold(getattr(display,"kind","")=="group" or identifier==primary);item.setFont(font)
            if identifier==primary:self.composition_list.setCurrentRow(row)
        self.composition_list.blockSignals(blocked);count=len(self._selected_resource_ids);self.composition_selection_label.setText((self._localization.text("layer.selection_count").format(count=count) if hasattr(self,"_localization") else f"{count} layers selected") if count>1 else "")

    def _format_resource_row(self,display):
        marker="▌" if display.primary else "•" if display.selected else " ";visible="●" if display.visible else "○";lock="L" if display.own_locked else "L*" if display.inherited_locked else " ";solo="S" if display.solo else " ";metrics=self.composition_list.fontMetrics()
        if display.kind=="group":
            empty=(self._localization.text("hierarchy.empty") if hasattr(self,"_localization") else "Empty") if not display.child_count else str(display.child_count);name=elide_text(metrics,display.name,max(60,self.composition_list.viewport().width()-125));return f"{'▼' if display.expanded else '▶'} {visible} {lock:2} {solo} {marker} [G] {name} ({empty})"
        layer=getattr(self,"_resource_layers",{}).get(display.identifier);mode=(self._localization.text("resource_layer.mode_particle") if hasattr(self,"_localization") else "Particle") if getattr(layer,"placement_mode","")=="particle" else (self._localization.text("resource_layer.mode_single") if hasattr(self,"_localization") else "Single");parent=f" [P: {elide_text(metrics,display.parent_label,70)}]" if display.parent_label else "";suffix=parent+f" · {mode}";name=elide_text(metrics,display.name,max(45,self.composition_list.viewport().width()-metrics.horizontalAdvance(suffix)-105));return f"{'    ' if display.depth else ''}{visible} {lock:2} {solo} {marker} {name}{suffix}"

    def _resource_row_tooltip(self,display):
        parts=[display.name]
        if not hasattr(self,"_localization"):return display.name
        if display.kind=="group":parts.append(self._localization.text("hierarchy.group_tooltip"))
        if display.parent_label:parts.append(self._localization.text("hierarchy.parent_tooltip").format(name=display.parent_label))
        if display.own_locked:parts.append(self._localization.text("hierarchy.own_lock"))
        elif display.inherited_locked:parts.append(self._localization.text("hierarchy.inherited_lock"))
        return "\n".join(parts)

    def current_asset_id(self) -> str | None:
        item = self.asset_list.currentItem()
        return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def current_generator_id(self) -> str | None:
        item = self.generator_list.currentItem()
        return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def current_clip_id(self) -> str | None:
        item = self.clip_list.currentItem(); return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def current_particle_id(self) -> str | None:
        item = self.particle_list.currentItem(); return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def current_composition_id(self) -> str | None:
        item = self.composition_list.currentItem(); return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def _typed_changed(self, current, kind: str) -> None:
        if current is None: return
        identifier = str(current.data(Qt.ItemDataRole.UserRole))
        for widget in (self.asset_list, self.generator_list, self.clip_list, self.particle_list, self.composition_list):
            if (kind == "clip" and widget is self.clip_list) or (kind == "particle" and widget is self.particle_list) or (kind == "composition" and widget is self.composition_list): continue
            widget.clearSelection()
        (self.clip_selected if kind == "clip" else self.particle_selected if kind == "particle" else self.composition_selected).emit(identifier)
        if kind=="composition":self._sync_composition_controls()

    def _request_add_composition(self) -> None:
        identifiers = getattr(self, "_resource_composition_ids", [])
        if identifiers: self.add_composition_requested.emit(identifiers[0])

    def _request_remove_composition(self):
        identifier=self.current_composition_id()
        if len(self._selected_resource_ids)>1 or isinstance(getattr(self,"_resource_layers",{}).get(identifier),LayerGroup):self.batch_resource_layer_requested.emit("delete")
        elif identifier:self.remove_resource_layer_requested.emit(identifier)

    def _request_duplicate_composition(self):
        identifier=self.current_composition_id()
        if len(self._selected_resource_ids)>1 or isinstance(getattr(self,"_resource_layers",{}).get(identifier),LayerGroup):self.batch_resource_layer_requested.emit("duplicate")
        elif identifier:self.duplicate_resource_layer_requested.emit(identifier)

    def _request_move_composition(self,direction):
        identifier=self.current_composition_id()
        if len(self._selected_resource_ids)>1 or isinstance(getattr(self,"_resource_layers",{}).get(identifier),LayerGroup):self.batch_resource_layer_requested.emit("front" if direction>0 else "back")
        elif identifier:self.move_resource_layer_requested.emit(identifier,int(direction))

    def _request_lock_composition(self):
        layer=getattr(self,"_resource_layers",{}).get(self.current_composition_id())
        if len(self._selected_resource_ids)>1 or isinstance(layer,LayerGroup):self.batch_resource_layer_requested.emit("toggle_lock")
        elif layer:self.lock_resource_layer_requested.emit(layer.id,not layer.locked)

    def _request_solo_composition(self):
        layer=getattr(self,"_resource_layers",{}).get(self.current_composition_id())
        if len(self._selected_resource_ids)>1 or isinstance(layer,LayerGroup):self.batch_resource_layer_requested.emit("toggle_solo")
        elif layer:self.solo_resource_layer_requested.emit(layer.id,not layer.solo)

    def _composition_context_menu(self,pos):
        item=self.composition_list.itemAt(pos)
        if item is None:return
        identifier=str(item.data(Qt.ItemDataRole.UserRole))
        if identifier not in self._selected_resource_ids:self.resource_layer_selection_requested.emit(identifier,Qt.KeyboardModifier.NoModifier)
        layer=getattr(self,"_resource_layers",{}).get(identifier)
        if not layer:return
        selected_count=len(self._selected_resource_ids);locked=any(value in self.composition_list.locked_ids for value in self._selected_resource_ids);states=context_action_states("group" if isinstance(layer,LayerGroup) else "leaf",selected_count,locked,bool(getattr(layer,"parent_id",None)));menu=QMenu(self);actions={};actions["duplicate"]=menu.addAction(self._localization.text("layer.batch.duplicate"));actions["delete"]=menu.addAction(self._localization.text("layer.batch.delete"));actions["delete"].setEnabled(states["delete"]);menu.addSeparator();actions["group"]=menu.addAction(self._localization.text("group.group_selected"));actions["ungroup"]=menu.addAction(self._localization.text("group.ungroup"));actions["group"].setEnabled(states["group"]);actions["ungroup"].setEnabled(states["ungroup"]);menu.addSeparator();parent_actions={}
        if isinstance(layer,LayerGroup):actions["toggle_expand"]=menu.addAction(self._localization.text("hierarchy.toggle_group"))
        else:
            parent_menu=menu.addMenu(self._localization.text("parent.set"));clear=menu.addAction(self._localization.text("parent.clear"));clear.setEnabled(layer.parent_id is not None and states["clear_parent"]);parent_actions[clear]=None;leaves=[value for value in self._resource_layers.values() if not isinstance(value,LayerGroup)];groups=[value for value in self._resource_layers.values() if isinstance(value,LayerGroup)];labels=layer_display_labels(leaves,groups)
            for candidate in leaves:
                if candidate.id!=layer.id and not would_create_parent_cycle(leaves,layer.id,candidate.id):action=parent_menu.addAction(labels.get(candidate.id,candidate.name));action.setEnabled(states["set_parent"]);parent_actions[action]=candidate.id
        menu.addSeparator();state_key="show" if not layer.visible else "hide";lock_key="unlock" if layer.locked else "lock";solo_key="unsolo" if layer.solo else "solo"
        for key in (state_key,lock_key,solo_key):actions[key]=menu.addAction(self._localization.text("layer.batch."+key))
        menu.addSeparator();actions["front"]=menu.addAction(self._localization.text("layer.batch.front"));actions["back"]=menu.addAction(self._localization.text("layer.batch.back"));actions["front"].setEnabled(states["reorder"]);actions["back"].setEnabled(states["reorder"]);menu.addSeparator();actions["expand_all"]=menu.addAction(self._localization.text("hierarchy.expand_all"));actions["collapse_all"]=menu.addAction(self._localization.text("hierarchy.collapse_all"))
        chosen=menu.exec(self.composition_list.viewport().mapToGlobal(pos));command=next((key for key,value in actions.items() if value is chosen),None)
        if chosen in parent_actions:self.parent_requested.emit(identifier,parent_actions[chosen]);return
        if command=="toggle_expand":self.group_expanded_requested.emit(identifier)
        elif command=="expand_all":self.expand_all_requested.emit()
        elif command=="collapse_all":self.collapse_all_requested.emit()
        elif command:self.batch_resource_layer_requested.emit(command)

    def _composition_double_clicked(self,item):
        identifier=str(item.data(Qt.ItemDataRole.UserRole))
        if isinstance(getattr(self,"_resource_layers",{}).get(identifier),LayerGroup):self.group_expanded_requested.emit(identifier)

    def _sync_composition_controls(self):
        selected=[getattr(self,"_resource_layers",{}).get(value) for value in self._selected_resource_ids];selected=[value for value in selected if value];enabled=bool(selected);any_locked=any(value.locked for value in selected);all_locked=enabled and all(value.locked for value in selected);all_solo=enabled and all(value.solo for value in selected);self.duplicate_composition_button.setEnabled(enabled);self.remove_composition_button.setEnabled(enabled and not any_locked);self.lock_composition_button.setEnabled(enabled);self.solo_composition_button.setEnabled(enabled);self.lock_composition_button.setChecked(all_locked);self.solo_composition_button.setChecked(all_solo);self.move_composition_up.setEnabled(enabled and not any_locked);self.move_composition_down.setEnabled(enabled and not any_locked);self.group_composition_button.setEnabled(len(selected)>=2 and all(not isinstance(value,LayerGroup) for value in selected));self.ungroup_composition_button.setEnabled(len(selected)==1 and isinstance(selected[0],LayerGroup))

    def _request_create_clip(self) -> None:
        identifier = self.current_generator_id()
        if identifier: self.create_clip_requested.emit(identifier)

    def _request_add_particle(self) -> None:
        identifier = self.current_clip_id()
        if identifier is None and self.clip_list.count(): identifier = str(self.clip_list.item(0).data(Qt.ItemDataRole.UserRole))
        if identifier:self.add_particle_requested.emit(identifier)
        elif getattr(self,"_resource_composition_ids",[]):self.add_particle_from_resource_requested.emit("resource_composition",self._resource_composition_ids[0])

    def _asset_changed(self, current: QListWidgetItem | None, previous) -> None:
        self.delete_asset_button.setEnabled(current is not None)
        if current is not None:
            self.generator_list.clearSelection()
            self.asset_selected.emit(str(current.data(Qt.ItemDataRole.UserRole)))

    def _generator_changed(self, current: QListWidgetItem | None, previous) -> None:
        self.delete_generator_button.setEnabled(current is not None)
        if current is not None:
            self.asset_list.clearSelection()
            self.generator_selected.emit(str(current.data(Qt.ItemDataRole.UserRole)))

    def _request_delete_asset(self) -> None:
        identifier = self.current_asset_id()
        if identifier:
            self.delete_asset_requested.emit(identifier)

    def _request_delete_generator(self) -> None:
        identifier = self.current_generator_id()
        if identifier:
            self.delete_generator_requested.emit(identifier)

    def show_asset(self, asset: SourceAsset | None) -> None:
        if asset is None:
            self.source_preview.setPixmap(QPixmap())
            self.source_preview.setText("No source selected")
            self.source_info.setText("")
            return
        pixels = np.ascontiguousarray(asset.pixels)
        image = QImage(
            pixels.data,
            asset.width,
            asset.height,
            pixels.strides[0],
            QImage.Format.Format_RGBA8888,
        ).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            104,
            104,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.source_preview.setText("")
        self.source_preview.setPixmap(pixmap)
        self.source_info.setText(
            f"{asset.width} × {asset.height} · Pivot "
            f"({asset.pivot_x:g}, {asset.pivot_y:g})"
        )
