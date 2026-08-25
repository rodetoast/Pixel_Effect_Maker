from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from uuid import uuid4

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton, QSizePolicy, QStackedWidget, QSplitter, QTableWidget, QVBoxLayout, QWidget

from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.layer_group import LayerGroup,group_node,layer_node
from app.models.layer_parenting import surviving_parent_dependencies, would_create_parent_cycle
from app.services.layer_parenting_service import resource_local_affine, set_parent_keep_world
from app.services.multi_transform_service import apply_resource_multi_transform,build_resource_multi_transform_context,set_resource_local_component,validate_multi_transform_selection
from app.services.resource_composition_render_service import invalidate_composition_cache
from app.ui.interface_settings_dialog import timeline_frame_width

from .asset_browser_panel import AssetBrowserPanel
from .asset_inspector_widget import AssetFrameStrip, AssetInspectorWidget, AssetPreviewCanvas, asset_durations, asset_frames
from app.project_defaults import DEFAULT_RESOURCE_HEIGHT, DEFAULT_RESOURCE_WIDTH
from .composition_canvas import CompositionCanvas
from .composition_inspector import CompositionInspector, LayerInspector, PropertySearchDialog
from .composition_timeline import CompositionTimeline
from .new_resource_dialog import NewResourceDialog
from .resource_editor_controller import ResourceEditorController
from .resource_editor_state import ResourceEditorMode
from app.ui.undo_commands import EditorValueCommand
from app.ui.tooltip_helper import apply_tooltip
from app.ui.layer_selection_state import LayerSelectionState
from app.ui.group_inspector import GroupInspector
from app.ui.layout_metrics import (
    RESOURCE_BROWSER_DEFAULT_WIDTH, RESOURCE_BROWSER_MIN_WIDTH,
    RESOURCE_INSPECTOR_DEFAULT_WIDTH, RESOURCE_INSPECTOR_MIN_WIDTH,
    RESOURCE_TIMELINE_DEFAULT_HEIGHT, RESOURCE_TIMELINE_MIN_HEIGHT,
)


class ResourceStartPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent);layout=QVBoxLayout(self);layout.addStretch();self.label=QLabel();self.label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.import_button=QPushButton();self.blank_button=QPushButton();layout.addWidget(self.label);layout.addWidget(self.import_button);layout.addWidget(self.blank_button);layout.addStretch()
    def setText(self,text):self.label.setText(text)


class ResourceEditorWidget(QWidget):
    SUPPORTED_DROP_SUFFIXES = {".png", ".gif", ".ase", ".aseprite"}
    import_requested=Signal(object);pivot_changed=Signal(str,str,float,float);create_emitter_requested=Signal(str,str);add_to_effect_requested=Signal(str,str,str);reimport_requested=Signal(str,str);delete_requested=Signal(str,str);resource_selected=Signal(str,str);composition_changed=Signal(str)

    def __init__(self,settings,parent=None):
        super().__init__(parent);self.setAcceptDrops(True);self.settings=settings;self.localization=None;self.undo_stack=None;self._applying_command=False;self.controller=ResourceEditorController(self);self.layer_selection=LayerSelectionState();self.expanded_group_ids=set();self._collapsed_group_ids=set();self.project=None;self._playing=False;self._last_asset=None;self._gizmo_before={};self._multi_gizmo_context=None;self._multi_gizmo_before=None;root=QVBoxLayout(self);self.vertical_splitter=QSplitter(Qt.Orientation.Vertical);self.splitter=QSplitter(Qt.Orientation.Horizontal);self.splitter.setChildrenCollapsible(False);self.splitter.setStretchFactor(0,0);self.splitter.setStretchFactor(1,1);self.splitter.setStretchFactor(2,0)
        self.browser=AssetBrowserPanel();self.center_stack=QStackedWidget();self.empty=ResourceStartPanel();self.asset_canvas=AssetPreviewCanvas();self.asset_strip=AssetFrameStrip();asset_center=QWidget();asset_layout=QVBoxLayout(asset_center);asset_layout.addWidget(self.asset_canvas,1);asset_tools=QHBoxLayout();self.asset_fit=QPushButton();self.asset_actual=QPushButton();asset_tools.addStretch();asset_tools.addWidget(self.asset_fit);asset_tools.addWidget(self.asset_actual);asset_layout.addLayout(asset_tools);asset_layout.addWidget(self.asset_strip);self.composition_canvas=CompositionCanvas();self.center_stack.addWidget(self.empty);self.center_stack.addWidget(asset_center);self.center_stack.addWidget(self.composition_canvas)
        self.browser.setMinimumWidth(RESOURCE_BROWSER_MIN_WIDTH);self.browser.setMaximumWidth(340);self.browser.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Expanding);self.center_stack.setMinimumWidth(260);self.inspector_stack=QStackedWidget();self.empty_inspector=QWidget();self.asset_inspector=AssetInspectorWidget();self.composition_inspector=CompositionInspector();self.layer_inspector=LayerInspector();self.group_inspector=GroupInspector();[self.inspector_stack.addWidget(widget) for widget in (self.empty_inspector,self.asset_inspector,self.composition_inspector,self.layer_inspector,self.group_inspector)];self.inspector_stack.setMinimumWidth(RESOURCE_INSPECTOR_MIN_WIDTH);self.inspector_stack.setMaximumWidth(520);self.inspector_stack.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Expanding);[self.splitter.addWidget(widget) for widget in (self.browser,self.center_stack,self.inspector_stack)];self.vertical_splitter.setChildrenCollapsible(False);self.vertical_splitter.setStretchFactor(0,1);self.vertical_splitter.setStretchFactor(1,0);self.vertical_splitter.addWidget(self.splitter)
        self.composition_timeline=CompositionTimeline();self.composition_timeline.set_frame_cell_width(timeline_frame_width(settings));self.composition_timeline.setMinimumHeight(RESOURCE_TIMELINE_MIN_HEIGHT);self.vertical_splitter.addWidget(self.composition_timeline);root.addWidget(self.vertical_splitter,1);self.timeline=QTableWidget(self);self.timeline.hide();self.splitter.splitterMoved.connect(self._save_horizontal_splitter);self.vertical_splitter.splitterMoved.connect(self._save_vertical_splitter);QTimer.singleShot(0,self._restore_splitters)
        self.timer=QTimer(self);self.timer.timeout.connect(self._advance)
        self.list=self.browser.asset_list;self.comp_list=self.browser.resource_list;self.pivot_x=self.asset_inspector.pivot_x;self.pivot_y=self.asset_inspector.pivot_y;self.canvas=self.composition_canvas
        self.browser.import_requested.connect(lambda:self.import_requested.emit(None));self.browser.asset_selected.connect(self._select_asset);self.browser.composition_selected.connect(lambda identifier:self.controller.select_composition(identifier));self.browser.asset_delete_requested.connect(self.delete_requested);self.browser.composition_delete_requested.connect(self._delete_composition);self.asset_strip.frame_selected.connect(self.set_frame);self.asset_inspector.create_requested.connect(self._create_dialog);self.asset_inspector.reimport_requested.connect(self._reimport);self.asset_inspector.pivot_changed.connect(self._asset_pivot)
        self.asset_fit.clicked.connect(self.asset_canvas.fit_to_view);self.asset_actual.clicked.connect(self.asset_canvas.actual_pixels)
        self.empty.import_button.clicked.connect(lambda:self.import_requested.emit(None));self.empty.blank_button.clicked.connect(self._create_blank_dialog)
        self.composition_inspector.changed.connect(self._composition_meta);self.composition_inspector.use_requested.connect(self._use_in_effect);self.layer_inspector.changed.connect(self._layer_meta);self.layer_inspector.parent_changed.connect(lambda parent_id:self.set_layer_parent(self.selected_layer.id,parent_id) if self.selected_layer else None);self.layer_inspector.mode_changed.connect(self.set_gizmo);self.layer_inspector.add_property_requested.connect(self._property_dialog);self.layer_inspector.full_rotation_requested.connect(self._full_rotation_click);self.layer_inspector.center_pivot_requested.connect(self._center_layer_pivot);self.layer_inspector.use_requested.connect(self._use_in_effect);self.layer_inspector.keyframe_requested.connect(self.set_keyframe);self.layer_inspector.keyframe_delete_requested.connect(self._delete_keyframe);self.layer_inspector.property_value_requested.connect(self._property_value);self.layer_inspector.batch_property_value_requested.connect(self._batch_property_value);self.layer_inspector.remove_property_requested.connect(self._remove_property)
        self.composition_timeline.frame_selected.connect(self.set_frame);self.composition_timeline.selection_requested.connect(self.select_layer_with_modifiers);self.composition_timeline.select_all_requested.connect(self.select_all_layers);self.composition_timeline.batch_command_requested.connect(self.batch_command);self.composition_timeline.visibility_requested.connect(self._toggle_visibility);self.composition_timeline.play_requested.connect(self.toggle_play);self.composition_timeline.previous_requested.connect(self.previous_frame);self.composition_timeline.next_requested.connect(self.next_frame);self.composition_timeline.delete_keyframe_requested.connect(self._delete_keyframe);self.composition_timeline.move_keyframe_requested.connect(self._move_keyframe)
        self.composition_timeline.add_layer_requested.connect(self.add_asset_layer);self.composition_timeline.duplicate_layer_requested.connect(self.duplicate_layer);self.composition_timeline.remove_layer_requested.connect(self.remove_layer);self.composition_timeline.move_layer_requested.connect(self.move_layer);self.composition_timeline.reorder_layer_requested.connect(self.reorder_layers)
        self.composition_timeline.lock_requested.connect(self.set_layer_locked);self.composition_timeline.solo_requested.connect(self.set_layer_solo)
        self.composition_timeline.group_expanded_requested.connect(self.toggle_group_expanded);self.composition_timeline.expand_all_requested.connect(lambda:self.set_all_groups_expanded(True));self.composition_timeline.collapse_all_requested.connect(lambda:self.set_all_groups_expanded(False));self.composition_timeline.hierarchy_drop_requested.connect(self.move_hierarchy_nodes)
        self.composition_timeline.parent_requested.connect(self.set_layer_parent)
        self.group_inspector.rename_requested.connect(self.rename_group);self.group_inspector.state_requested.connect(self.set_group_state)
        self.composition_timeline.scrub_started.connect(self.stop)
        self.composition_canvas.layer_selected.connect(lambda identifier:self.select_layer_with_modifiers(identifier,Qt.KeyboardModifier.NoModifier) if identifier else self.clear_layer_selection());self.composition_canvas.transform_changed.connect(self._gizmo_change);self.composition_canvas.transform_cancelled.connect(self._gizmo_cancel);self.composition_canvas.drag_started.connect(self.stop)
        self.controller.state_changed.connect(self._apply_state);self.controller.frame_changed.connect(lambda frame:self._apply_state(self.controller.state));self.controller.composition_changed.connect(self.composition_changed);self.controller.clear()
        for drop_target in (self.browser,self.browser.asset_list,self.browser.asset_list.viewport(),self.browser.resource_list,self.browser.resource_list.viewport(),self.empty,self.center_stack,self.asset_canvas,self.composition_canvas):
            drop_target.setAcceptDrops(True);drop_target.installEventFilter(self)

    @classmethod
    def _drop_paths(cls,event):
        mime=event.mimeData()
        if not mime or not mime.hasUrls():return []
        return [url.toLocalFile() for url in mime.urls() if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in cls.SUPPORTED_DROP_SUFFIXES]

    def _accept_drag(self,event):
        if self._drop_paths(event):event.setDropAction(Qt.DropAction.CopyAction);event.accept()
        else:event.ignore()

    def dragEnterEvent(self,event):self._accept_drag(event)
    def dragMoveEvent(self,event):self._accept_drag(event)
    def dropEvent(self,event):
        paths=self._drop_paths(event)
        if not paths:event.ignore();return
        self.import_requested.emit(paths);event.setDropAction(Qt.DropAction.CopyAction);event.accept()

    def eventFilter(self,watched,event):
        if event.type() in (QEvent.Type.DragEnter,QEvent.Type.DragMove):self._accept_drag(event);return True
        if event.type()==QEvent.Type.Drop:self.dropEvent(event);return True
        return super().eventFilter(watched,event)

    @property
    def resource(self):return self.controller.asset
    @resource.setter
    def resource(self,value):
        if value is None:self.controller.state.asset_id=None
    @property
    def resource_type(self):return self.controller.state.asset_type
    @property
    def composition(self):return self.controller.composition
    @composition.setter
    def composition(self,value):self.controller.state.composition_id=None if value is None else value.id
    @property
    def selected_layer(self):return self.controller.layer
    @selected_layer.setter
    def selected_layer(self,value):self.controller.state.layer_id=None if value is None else value.id
    @property
    def frame_index(self):return self.controller.state.frame
    @frame_index.setter
    def frame_index(self,value):self.controller.state.frame=int(value)

    def refresh(self,project,select=None):
        self.project=project;self.controller.set_project(project)
        self.composition_timeline.set_available_sources(project)
        if select:self._last_asset=select;self.controller.select_asset(*select)
        asset_selection=(self.controller.state.asset_type,self.controller.state.asset_id) if self.controller.asset else None;self.browser.refresh(project,asset_selection,self.controller.state.composition_id);self._legacy_timeline();self._apply_state(self.controller.state)

    def select_resource(self,kind,identifier):self.controller.select_asset(kind,identifier);self.browser.refresh(self.project,(kind,identifier),None)

    def _select_asset(self,kind,identifier):
        self._last_asset=(kind,identifier);self.controller.select_asset(kind,identifier);self.resource_selected.emit(kind,identifier)

    def _apply_state(self,state):
        mode=state.mode;asset=self.controller.asset;composition=self.controller.composition;layer=self.controller.layer
        timeline_was_visible=self.composition_timeline.isVisible();timeline_visible=mode in {ResourceEditorMode.COMPOSITION,ResourceEditorMode.LAYER_EDIT};self.center_stack.setCurrentIndex(0 if mode==ResourceEditorMode.EMPTY else 1 if mode==ResourceEditorMode.ASSET_INSPECT else 2);self.inspector_stack.setCurrentIndex({ResourceEditorMode.EMPTY:0,ResourceEditorMode.ASSET_INSPECT:1,ResourceEditorMode.COMPOSITION:2,ResourceEditorMode.LAYER_EDIT:3}[mode]);self.composition_timeline.setVisible(timeline_visible)
        if timeline_visible and not timeline_was_visible:QTimer.singleShot(0,self._restore_vertical_splitter)
        if mode==ResourceEditorMode.EMPTY:self.empty.setText(self.localization.text("resource.start_text") if self.localization else "Import an asset or create an empty resource to begin")
        elif mode==ResourceEditorMode.ASSET_INSPECT:
            self.asset_canvas.set_asset(asset,state.frame);self.asset_strip.set_asset(asset,state.frame);self.asset_inspector.set_asset(asset)
        else:
            composition.repair_hierarchy();self.expanded_group_ids&={group.id for group in composition.groups};self.expanded_group_ids|={group.id for group in composition.groups if group.id not in self.expanded_group_ids and group.id not in getattr(self,"_collapsed_group_ids",set())};ui_ids=self._ui_node_ids()
            if state.layer_id is None and self.layer_selection.primary_id and composition.group_by_id(self.layer_selection.primary_id) is None:self.layer_selection.clear()
            if state.layer_id in ui_ids and state.layer_id!=self.layer_selection.primary_id:self.layer_selection.restore({"selected_ids":[state.layer_id],"primary_id":state.layer_id,"anchor_id":state.layer_id},ui_ids)
            preferred=self.layer_selection.primary_id or state.layer_id;primary=self.layer_selection.repair(ui_ids,preferred,allow_empty=state.layer_id is None and not self.layer_selection.selected_ids);state.layer_id=primary if any(item.id==primary for item in composition.layers) else None;layer=self.controller.layer
            self.composition_timeline.set_available_sources(self.project)
            group=composition.group_by_id(primary);self.inspector_stack.setCurrentWidget(self.group_inspector if group else self.layer_inspector if layer else self.composition_inspector);self.group_inspector.set_group(group);source=self._layer_source(layer);selected_leaves,reason=validate_multi_transform_selection(composition.layers,self.layer_selection.selected_ids,group_ids=[item.id for item in composition.groups],effectively_locked=composition.effective_locked);multi_context=None
            if selected_leaves and reason is None:
                try:multi_context=build_resource_multi_transform_context(composition,self.layer_selection.selected_ids,state.frame)
                except ValueError:multi_context=None
            blocked=len(self.layer_selection.selected_ids)>1 and reason in {"group","locked"};display_leaves=[item for item in composition.layers if item.id in self.layer_selection.selected_ids];self.composition_canvas.set_context(self.project,composition,layer,state.frame,selected_leaves if multi_context else (display_leaves or ([layer] if layer else [])),multi_context.pivot if multi_context else None,multi_context is not None,blocked);self.composition_inspector.set_composition(composition);self.layer_inspector.set_layer(layer,source,state.frame);self.layer_inspector.set_multi_layers(selected_leaves if multi_context else [],state.frame);self.layer_inspector.set_parent_candidates(composition.layers,composition.groups);self.layer_inspector.set_mode(state.gizmo_mode);self.composition_canvas.set_mode(state.gizmo_mode,self.localization.text({"move":"gizmo.move","rotate_x":"gizmo.rotate_x","rotate_y":"gizmo.rotate_y","rotate":"gizmo.rotate_z","scale":"gizmo.scale","pivot":"composition.pivot"}[state.gizmo_mode]) if self.localization else state.gizmo_mode);self.composition_timeline.refresh(composition,layer,state.frame,self.layer_selection.selected_ids,self.layer_selection.primary_id,self.expanded_group_ids)
            count=len(self.layer_selection.selected_ids);help_text=self.localization.text("layer.multiselect_primary_help") if self.localization and count>1 else "";self.layer_inspector.title.setToolTip(help_text)
            if self.localization and layer and count>1:self.layer_inspector.title.setText(self.localization.text("layer.primary_summary").format(name=layer.name,count=count))
        self._legacy_timeline()

    def _ui_root_ids(self):return [] if not self.composition else [node["id"] for node in reversed(self.composition.root_order)]
    def _ui_node_ids(self,visible_only=True):
        if not self.composition:return []
        group_by_id={group.id:group for group in self.composition.groups};result=[]
        for node in reversed(self.composition.root_order):
            identifier=node["id"];result.append(identifier)
            if node["type"]=="group" and (not visible_only or identifier in self.expanded_group_ids):result.extend(reversed(group_by_id[identifier].children))
        return result
    def _ui_layer_ids(self):return self._ui_node_ids()
    def _parent_id(self,identifier):
        group=self.composition.parent_group(identifier) if self.composition else None;return group.id if group else None
    def _ui_siblings(self,identifier):
        if not self.composition:return []
        group=self.composition.parent_group(identifier)
        return list(reversed(group.children)) if group else self._ui_root_ids()
    @property
    def selected_layer_ids(self):return set(self.layer_selection.selected_ids)
    @property
    def primary_layer_id(self):return self.layer_selection.primary_id
    @property
    def selection_anchor_id(self):return self.layer_selection.anchor_id

    def select_layer_with_modifiers(self,identifier,modifiers=Qt.KeyboardModifier.NoModifier):
        if identifier is None:return
        identifier=str(identifier);shift=bool(modifiers&Qt.KeyboardModifier.ShiftModifier)
        if shift and self.layer_selection.anchor_id and self._parent_id(identifier)!=self._parent_id(self.layer_selection.anchor_id):modifiers=Qt.KeyboardModifier.NoModifier
        ids=self._ui_siblings(identifier) if modifiers&Qt.KeyboardModifier.ShiftModifier else self._ui_node_ids(False);primary=self.layer_selection.click(identifier,ids,modifiers);self._repair_selection_overlap(identifier);self.controller.select_layer(primary if any(item.id==primary for item in self.composition.layers) else None)

    def select_all_layers(self):
        primary=self.layer_selection.select_all(self._ui_root_ids());self.controller.select_layer(primary if any(item.id==primary for item in self.composition.layers) else None)

    def _repair_selection_overlap(self,clicked=None):
        if not self.composition:return
        for group in self.composition.groups:
            if group.id in self.layer_selection.selected_ids:
                if clicked in group.children:self.layer_selection.selected_ids.discard(group.id)
                else:self.layer_selection.selected_ids.difference_update(group.children)
        self.layer_selection.repair(self._ui_node_ids(False),self.layer_selection.primary_id)

    def clear_layer_selection(self):
        self.layer_selection.clear();self.controller.select_layer(None)

    def _selection_value(self,layers=None,selected_ids=None,primary=None,anchor=None,render=True,groups=None,root_order=None):
        return {"layers":deepcopy(self.composition.layers if layers is None else layers),"groups":deepcopy(self.composition.groups if groups is None else groups),"root_order":deepcopy(self.composition.root_order if root_order is None else root_order),"selection":{"selected_ids":list(self.layer_selection.selected_ids if selected_ids is None else selected_ids),"primary_id":self.layer_selection.primary_id if primary is None else primary,"anchor_id":self.layer_selection.anchor_id if anchor is None else anchor},"expanded":list(self.expanded_group_ids),"render":bool(render)}

    def _selected_ids_in_model_order(self):
        selected=self.layer_selection.selected_ids;return [item.id for item in self.composition.layers if item.id in selected] if self.composition else []

    def _layer_effectively_locked(self,layer):return bool(layer and self.composition and self.composition.effective_locked(layer))

    @staticmethod
    def _settings_sizes(value,count):
        try:return [int(item) for item in value] if isinstance(value,(list,tuple)) and len(value)==count else []
        except (TypeError,ValueError):return []

    def _restore_splitters(self):
        available=max(820,self.width(),self.window().width());left=min(220,max(RESOURCE_BROWSER_DEFAULT_WIDTH,round(available*.16)));right=RESOURCE_INSPECTOR_DEFAULT_WIDTH;defaults=[left,max(260,available-left-right),right];saved=self._settings_sizes(self.settings.value("ui/resource_editor_v2_horizontal_splitter",[]),3)
        valid=bool(saved and saved[0]>=RESOURCE_BROWSER_MIN_WIDTH and saved[1]>=260 and saved[2]>=RESOURCE_INSPECTOR_MIN_WIDTH and saved[2]<=min(520,available*.42) and sum(saved)<=available*1.25);self.splitter.setSizes(saved if valid else defaults);self._restore_vertical_splitter()

    def _restore_vertical_splitter(self):
        available=max(420,self.height());saved=self._settings_sizes(self.settings.value("ui/resource_editor_v2_vertical_splitter",[]),2);defaults=[max(260,available-RESOURCE_TIMELINE_DEFAULT_HEIGHT),RESOURCE_TIMELINE_DEFAULT_HEIGHT];valid=bool(saved and saved[0]>=240 and saved[1]>=RESOURCE_TIMELINE_MIN_HEIGHT and sum(saved)<=available*1.25);self.vertical_splitter.setSizes(saved if valid else defaults)

    def _save_horizontal_splitter(self,*args):self.settings.setValue("ui/resource_editor_v2_horizontal_splitter",self.splitter.sizes())
    def _save_vertical_splitter(self,*args):
        if self.composition_timeline.isVisible():self.settings.setValue("ui/resource_editor_v2_vertical_splitter",self.vertical_splitter.sizes())

    def _layer_source(self,layer):
        if layer is None:return None
        items=self.project.source_assets if layer.source_type=="source_asset" else self.project.animation_clips;return next((item for item in items if item.id==layer.source_id),None)

    def _legacy_timeline(self):
        count=len(asset_frames(self.resource)) if self.resource else 0;self.timeline.setColumnCount(count);self.timeline.setRowCount(1 if count else 0)

    def _create_dialog(self):
        if self.resource is None:return
        dialog=NewResourceDialog(self.resource,self.localization,self,defaults=(DEFAULT_RESOURCE_WIDTH,DEFAULT_RESOURCE_HEIGHT,self.project.fps,self.project.loop))
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.controller.create_resource(*dialog.values());self.browser.refresh(self.project,None,self.composition.id)

    def _create_blank_dialog(self):
        if self.project is None:return
        dialog=NewResourceDialog(None,self.localization,self,defaults=(DEFAULT_RESOURCE_WIDTH,DEFAULT_RESOURCE_HEIGHT,self.project.fps,self.project.loop))
        if dialog.exec()==QDialog.DialogCode.Accepted:
            composition=self.controller.create_blank_resource(*dialog.values());self.browser.refresh(self.project,None,composition.id)

    def _reimport(self):
        if self.resource:self.reimport_requested.emit(self.resource_type,self.resource.id)

    def _asset_pivot(self,x,y):
        if self.resource:self._push_value(self.resource.id,"asset_pivot",[self.resource.pivot_x,self.resource.pivot_y],[x,y],"Asset Pivot",512)

    def _composition_meta(self,before,after):
        names={item.name for item in self.project.resource_compositions if item is not self.composition};base=self.composition.name;number=2
        while self.composition.name in names:self.composition.name=f"{base} ({number})";number+=1
        after=dict(after);after["name"]=self.composition.name
        for key,value in before.items():setattr(self.composition,key,value)
        self._push_value(self.composition.id,"composition_meta",before,after,"Composition Properties",510);self.browser.refresh(self.project,None,self.composition.id)

    def _layer_meta(self,before,after):
        if self._layer_effectively_locked(self.selected_layer):
            for key,value in before.items():setattr(self.selected_layer,key,value)
            self._apply_state(self.controller.state);return
        for key,value in before.items():setattr(self.selected_layer,key,value)
        self._push_value(self.selected_layer.id,"layer_meta",before,after,"Layer Properties",511)
    def _use_in_effect(self):
        if not self.composition:return
        self.request_add_to_effect("resource_layer")

    def request_add_to_effect(self, mode: str) -> None:
        """Add the current Resource Composition as a single Resource Layer."""
        if not self.composition or mode not in {"resource_layer","composition_layer","particle_system"}:return
        self.add_to_effect_requested.emit("resource_layer","resource_composition",self.composition.id)

    def _delete_composition(self,identifier):
        composition=next((item for item in self.project.resource_compositions if item.id==identifier),None)
        if composition is None:return
        if any(layer.resource_composition_id==identifier for layer in self.project.effect_resource_layers) or any(emitter.settings.resource_type=="resource_composition" and emitter.settings.resource_id==identifier for emitter in self.project.particle_emitters) or any(layer.resource_composition_id==identifier for layer in self.project.effect_composition_layers):QMessageBox.warning(self,self.localization.text("v2.resources"),self.localization.text("composition.in_use"));return
        if not self._confirm(self.localization.text("v2.resources"),self.localization.text("composition.delete_confirm"),"v2.delete"):return
        self.project.resource_compositions.remove(composition);invalidate_composition_cache(identifier);self.controller.clear();self.composition_changed.emit("");self.browser.refresh(self.project)

    def _property_dialog(self):
        if not self.selected_layer:return
        dialog=PropertySearchDialog(self.selected_layer.tracks,self.localization,self)
        if dialog.exec()==QDialog.DialogCode.Accepted and dialog.selected_id:self.add_property_to_layer(dialog.selected_id)

    def _full_rotation_click(self):
        track=self.selected_layer.tracks.get("rotation") if self.selected_layer else None
        if track and track.keyframes and not self._confirm(self.localization.text("v2.full_rotation"),self.localization.text("v2.replace_rotation_confirm"),"v2.replace"):return
        self.add_full_rotation()

    def _center_layer_pivot(self):
        if not self.selected_layer or self._layer_effectively_locked(self.selected_layer):return
        source=self._layer_source(self.selected_layer)
        if source:self._push_value(self.selected_layer.id,"pivot",[self.selected_layer.pivot_x,self.selected_layer.pivot_y],[source.width/2,source.height/2],"Center Layer Pivot")

    def _toggle_visibility(self,layer_id):
        layer=next((item for item in self.composition.layers if item.id==layer_id),None)
        if layer:self._push_value(layer.id,"visible",layer.visible,not layer.visible,"Layer Visibility")

    def _delete_keyframe(self,property_id):
        if self.selected_layer is None or self._layer_effectively_locked(self.selected_layer):return
        properties=[property_id] if property_id in self.selected_layer.tracks else list(self.selected_layer.tracks)
        for prop in properties:
            before=deepcopy(self.selected_layer.tracks.get(prop));after=deepcopy(before)
            if after is not None and after.delete_keyframe(self.frame_index):self._push_value(self.selected_layer.id,"track:"+prop,before,after,"Delete Keyframe")

    def _move_keyframe(self,property_id,source_frame,target_frame):
        if self.selected_layer is None or self._layer_effectively_locked(self.selected_layer) or property_id not in self.selected_layer.tracks:return
        before=deepcopy(self.selected_layer.tracks[property_id]);after=deepcopy(before)
        if after.move_keyframe(source_frame,target_frame,self.composition.frame_count):
            self._push_value(self.selected_layer.id,"track:"+property_id,before,after,"Move Keyframe")
            self.set_frame(max(0,min(int(target_frame),self.composition.frame_count-1)))

    def _remove_property(self,property_id):
        if not self.selected_layer or self._layer_effectively_locked(self.selected_layer):return
        if self._confirm(self.localization.text("composition.properties"),self.localization.text("composition.remove_property_confirm"),"v2.delete"):self.selected_layer.remove_property(property_id);self.controller.changed()

    def _property_value(self,property_id,value):
        if self.selected_layer is None or self._layer_effectively_locked(self.selected_layer) or property_id not in self.selected_layer.tracks:return
        track=self.selected_layer.tracks[property_id];before=deepcopy(track);after=deepcopy(track);existing=next((item for item in after.keyframes if item.frame==self.frame_index),None)
        current=after.evaluate(self.frame_index)
        if current==value:return
        if existing:existing.value=value
        elif after.keyframes:after.set_keyframe(self.frame_index,value,"Linear")
        else:after.default_value=value
        merge_ids={"position":100,"rotation":101,"scale":102,"opacity":103,"rotation_x":104,"rotation_y":105,"perspective_strength":106}
        self._push_value(self.selected_layer.id,"track:"+property_id,before,after,"Change "+property_id.title(),merge_ids.get(property_id,-1))

    def _batch_property_value(self,property_id,component,value):
        if not self.composition:return False
        layers,reason=validate_multi_transform_selection(self.composition.layers,self.layer_selection.selected_ids,group_ids=[item.id for item in self.composition.groups],effectively_locked=self.composition.effective_locked)
        if reason:
            self._report_multi_transform_block(reason);return False
        before={layer.id:deepcopy(layer.tracks) for layer in layers};changed=False
        for layer in layers:changed=set_resource_local_component(layer,property_id,component,self.frame_index,value) or changed
        if not changed:return False
        after={layer.id:deepcopy(layer.tracks) for layer in layers};self._apply_multi_tracks(before,touch=False,refresh=False);self._push_value(self.composition.id,"multi_tracks",before,after,"Edit Selected Local Transform");return True

    def _confirm(self,title,message,accept_key):
        box=QMessageBox(QMessageBox.Icon.Question,title,message,parent=self);accept=box.addButton(self.localization.text(accept_key),QMessageBox.ButtonRole.AcceptRole);box.addButton(self.localization.text("v2.cancel"),QMessageBox.ButtonRole.RejectRole);box.exec();return box.clickedButton() is accept

    def set_gizmo(self,mode):
        self.controller.set_gizmo(mode);self.layer_inspector.set_mode(mode);self.composition_canvas.set_mode(mode,self.localization.text({"move":"gizmo.move","rotate_x":"gizmo.rotate_x","rotate_y":"gizmo.rotate_y","rotate":"gizmo.rotate_z","scale":"gizmo.scale","pivot":"composition.pivot"}[mode]) if self.localization else mode)

    def _gizmo_change(self,property_id,value,final):
        if self.composition_canvas.multi_transform_enabled and property_id in {"position","rotation","scale"}:
            return self._multi_gizmo_change(property_id,value,final)
        layer=self.selected_layer
        if layer is None or self._layer_effectively_locked(layer):return
        had_change=property_id in self._gizmo_before
        if not had_change:self._gizmo_before[property_id]=deepcopy([layer.pivot_x,layer.pivot_y] if property_id=="pivot" else layer.tracks.get(property_id))
        if property_id=="pivot":
            if [layer.pivot_x,layer.pivot_y]==list(value):
                if not final or not had_change:
                    if final:self._gizmo_before.pop(property_id,None)
                    return
            layer.pivot_x,layer.pivot_y=value
        else:
            track=layer.add_property(property_id);current=track.evaluate(self.frame_index)
            if current==value:
                if not final or not had_change:
                    if final:self._gizmo_before.pop(property_id,None)
                    return
            key=track.keyframe_at(self.frame_index)
            if key is not None:key.value=value
            elif track.keyframes:track.set_keyframe(self.frame_index,value,"Linear")
            else:track.default_value=value
        self.composition.touch();invalidate_composition_cache(self.composition.id);self._apply_state(self.controller.state)
        if final:
            before=self._gizmo_before.pop(property_id,None);after=deepcopy([layer.pivot_x,layer.pivot_y] if property_id=="pivot" else layer.tracks.get(property_id))
            if before!=after:self.apply_undo_value(layer.id,"pivot" if property_id=="pivot" else "track:"+property_id,before);self._push_value(layer.id,"pivot" if property_id=="pivot" else "track:"+property_id,before,after,"Gizmo "+property_id.title())
            self.composition_changed.emit(self.composition.id)

    def _gizmo_cancel(self,property_id,value):
        if self._multi_gizmo_before is not None:
            self._apply_multi_tracks(self._multi_gizmo_before);self._multi_gizmo_before=None;self._multi_gizmo_context=None;self._apply_state(self.controller.state);return
        before=self._gizmo_before.pop(property_id,None);layer=self.selected_layer
        if layer is None or self._layer_effectively_locked(layer):return
        if property_id=="pivot":layer.pivot_x,layer.pivot_y=before or value
        elif before is None:layer.tracks.pop(property_id,None)
        else:layer.tracks[property_id]=before
        self.composition.touch();invalidate_composition_cache(self.composition.id);self._apply_state(self.controller.state)

    def _multi_gizmo_change(self,property_id,value,final):
        layers,reason=validate_multi_transform_selection(self.composition.layers,self.layer_selection.selected_ids,group_ids=[item.id for item in self.composition.groups],effectively_locked=self.composition.effective_locked)
        if reason:
            self._report_multi_transform_block(reason);return False
        if self._multi_gizmo_context is None:
            try:self._multi_gizmo_context=build_resource_multi_transform_context(self.composition,self.layer_selection.selected_ids,self.frame_index)
            except ValueError:return False
            roots=set(self._multi_gizmo_context.transform_root_ids);self._multi_gizmo_before={layer.id:deepcopy(layer.tracks) for layer in self.composition.layers if layer.id in roots}
        self._apply_multi_tracks(self._multi_gizmo_before,touch=False,refresh=False)
        operation={"position":"move","rotation":"rotate","scale":"scale"}[property_id]
        try:changed=apply_resource_multi_transform(self.composition,self._multi_gizmo_context,operation,value,self.frame_index)
        except ValueError:
            self._apply_multi_tracks(self._multi_gizmo_before);return False
        if changed:self.composition.touch();invalidate_composition_cache(self.composition.id);self._apply_state(self.controller.state)
        if final:
            before=self._multi_gizmo_before;after={identifier:deepcopy(next(layer for layer in self.composition.layers if layer.id==identifier).tracks) for identifier in before};self._apply_multi_tracks(before,touch=False,refresh=False);self._multi_gizmo_before=None;self._multi_gizmo_context=None
            if before!=after:self._push_value(self.composition.id,"multi_tracks",before,after,"Transform Selected Resource Layers");self.composition_changed.emit(self.composition.id)
            else:self._apply_state(self.controller.state)
        return changed

    def _apply_multi_tracks(self,value,touch=True,refresh=True):
        by_id={layer.id:layer for layer in self.composition.layers}
        for identifier,tracks in value.items():
            if identifier in by_id:by_id[identifier].tracks=deepcopy(tracks)
        if touch:self.composition.touch();invalidate_composition_cache(self.composition.id)
        if refresh:self._apply_state(self.controller.state)

    def _report_multi_transform_block(self,reason):
        key="multi_transform.group_block" if reason=="group" else "multi_transform.locked_block" if reason=="locked" else "multi_transform.selection_block"
        message=self.localization.text(key) if self.localization else ("Groups cannot be transformed." if reason=="group" else "Unlock selected layers before transforming." if reason=="locked" else "Select at least two leaf layers.")
        self.composition_timeline.selection_status.setToolTip(message);status=getattr(self.window(),"statusBar",None)
        if callable(status):status().showMessage(message,4000)

    def set_frame(self,index):self.stop();self.controller.set_frame(index)
    def previous_frame(self):self.set_frame(self.frame_index-1)
    def next_frame(self):self.set_frame(self.frame_index+1)
    def toggle_play(self):
        if self._playing:self.stop();return
        count=self.composition.frame_count if self.composition else len(asset_frames(self.resource)) if self.resource else 0
        if count<2:return
        interval=max(1,round(1000/self.composition.fps)) if self.composition else asset_durations(self.resource)[self.frame_index];self._playing=True;self.composition_timeline.set_playing(True);self.timer.start(interval)
    def stop(self):self._playing=False;self.timer.stop();self.composition_timeline.set_playing(False)
    def _advance(self):
        if not self._playing:return
        if self.composition:
            if self.frame_index>=self.composition.frame_count-1:
                if not self.composition.loop:self.stop();return
                self.controller.set_frame(0)
            else:self.controller.set_frame(self.frame_index+1)
        else:
            frames=asset_frames(self.resource);self.controller.set_frame((self.frame_index+1)%len(frames));self.timer.setInterval(asset_durations(self.resource)[self.frame_index])

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):self.toggle_play();event.accept();return
        if event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Comma):self.previous_frame();event.accept();return
        if event.key() in (Qt.Key.Key_Right,Qt.Key.Key_Period):self.next_frame();event.accept();return
        super().keyPressEvent(event)

    def retranslate_ui(self,localization):
        self.localization=localization;self.browser.retranslate(localization);self.asset_inspector.retranslate(localization);self.composition_inspector.retranslate(localization);self.layer_inspector.retranslate(localization);self.group_inspector.retranslate(localization);self.composition_timeline.retranslate(localization);self.empty.setText(localization.text("resource.start_text"));self.empty.import_button.setText(localization.text("resource.start_import"));self.empty.blank_button.setText(localization.text("resource.start_blank"));self.asset_fit.setText(localization.text("v2.fit_view"));self.asset_actual.setText(localization.text("v2.actual_pixels"));apply_tooltip(self.empty.import_button,localization,"tooltip.resource.import");apply_tooltip(self.empty.blank_button,localization,"tooltip.resource.create_empty");apply_tooltip(self.asset_fit,localization,"tooltip.resource.fit_view");apply_tooltip(self.asset_actual,localization,"tooltip.resource.actual_pixels");self.set_gizmo(self.composition_canvas.mode)
    def set_undo_stack(self,stack):self.undo_stack=stack
    def set_shortcuts(self,play,previous,next_):self.composition_timeline.set_shortcuts(play,previous,next_)
    def set_timeline_frame_width(self,width):self.composition_timeline.set_frame_cell_width(width)
    def _push_value(self,target_id,field,before,after,text,merge_id=-1):
        if before==after:return
        if self.undo_stack is None:self.apply_undo_value(target_id,field,after)
        else:self.undo_stack.push(EditorValueCommand(self,target_id,field,before,after,text,merge_id))
    def apply_undo_value(self,target_id,field,value):
        if self.project is None:return
        self._applying_command=True
        try:self._apply_undo_value(target_id,field,value)
        finally:self._applying_command=False
    def _apply_undo_value(self,target_id,field,value):
        if field=="asset_pivot":
            asset=next((item for item in self.project.source_assets+self.project.animation_clips if item.id==target_id),None)
            if asset:asset.pivot_x,asset.pivot_y=value;self._apply_state(self.controller.state);self.pivot_changed.emit(self.resource_type,target_id,*value)
            return
        if field=="composition_meta":
            composition=next((item for item in self.project.resource_compositions if item.id==target_id),None)
            if composition:
                for key,part in value.items():setattr(composition,key,part)
                composition.touch();invalidate_composition_cache(composition.id);self.controller.changed();self.browser.refresh(self.project,None,composition.id)
            return
        if field=="layers":
            composition=next((item for item in self.project.resource_compositions if item.id==target_id),None)
            if composition:
                composition.layers=deepcopy(value)
                if self.controller.state.composition_id==composition.id and self.controller.layer is None:self.controller.state.layer_id=composition.layers[-1].id if composition.layers else None
                self.controller.changed()
            return
        if field=="multi_tracks":
            composition=next((item for item in self.project.resource_compositions if item.id==target_id),None)
            if composition:
                by_id={layer.id:layer for layer in composition.layers}
                for identifier,tracks in value.items():
                    if identifier in by_id:by_id[identifier].tracks=deepcopy(tracks)
                composition.touch();invalidate_composition_cache(composition.id);self.controller.changed()
            return
        if field=="layer_workflow":
            composition=next((item for item in self.project.resource_compositions if item.id==target_id),None)
            if composition:
                composition.layers=deepcopy(value["layers"])
                composition.groups=deepcopy(value.get("groups",[]));composition.root_order=deepcopy(value.get("root_order",[]));composition.repair_hierarchy();self.expanded_group_ids=set(value.get("expanded",[group.id for group in composition.groups]))
                if "selection" in value:self.layer_selection.restore(value["selection"],self._ui_node_ids(False));self.controller.state.layer_id=self.layer_selection.primary_id if any(item.id==self.layer_selection.primary_id for item in composition.layers) else None
                else:self.controller.state.layer_id=value.get("selected_id");self.layer_selection.restore({"selected_ids":[self.controller.state.layer_id],"primary_id":self.controller.state.layer_id,"anchor_id":self.controller.state.layer_id},[item.id for item in reversed(composition.layers)])
                if value.get("render",True):self.controller.changed()
                else:self._apply_state(self.controller.state)
            return
        layer=next((layer for composition in self.project.resource_compositions for layer in composition.layers if layer.id==target_id),None)
        if layer is None:return
        if field.startswith("track:"):
            prop=field.split(":",1)[1]
            if value is None:layer.tracks.pop(prop,None)
            else:layer.tracks[prop]=value
        elif field=="pivot":layer.pivot_x,layer.pivot_y=value
        elif field=="layer_meta":
            for key,part in value.items():setattr(layer,key,part)
        else:setattr(layer,field,value)
        composition=next((item for item in self.project.resource_compositions if layer in item.layers),None)
        if composition:
            if field in {"locked","solo"}:self._apply_state(self.controller.state)
            else:composition.touch();invalidate_composition_cache(composition.id);self.controller.changed()
    def _center(self):self.asset_inspector._center()
    def create_composition(self,name="Composition",width=64,height=64,fps=12,frame_count=12,loop=True):
        existing={item.name for item in self.project.resource_compositions};base=name;number=2
        while name in existing:name=f"{base} ({number})";number+=1
        composition=ResourceComposition(name,width,height,fps,frame_count,loop);self.project.resource_compositions.append(composition);self.controller.select_composition(composition.id);self.composition_changed.emit(composition.id);self.browser.refresh(self.project,None,composition.id);return composition
    def add_selected_asset(self):
        return None if not self._last_asset else self.add_asset_layer(*self._last_asset)
    def add_asset_layer(self,kind,identifier):
        if not self.composition:return None
        items=self.project.source_assets if kind=="source_asset" else self.project.animation_clips;asset=next((item for item in items if item.id==identifier),None)
        if asset is None:return None
        existing={item.name for item in self.composition.layers};base=asset.name;name=base;number=2
        while name in existing:name=f"{base} ({number})";number+=1
        layer=CompositionLayer(name,kind,asset.id,0,self.composition.frame_count-1,pivot_x=asset.pivot_x,pivot_y=asset.pivot_y);before=deepcopy(self.composition.layers);after=before+[deepcopy(layer)];self._push_value(self.composition.id,"layers",before,after,"Add Resource Layer");self.controller.select_layer(layer.id);return self.selected_layer
    def remove_layer(self,identifier):
        if not self.composition:return False
        if identifier not in self.layer_selection.selected_ids:self.select_layer_with_modifiers(identifier)
        return self.delete_selected_layers()
    def duplicate_layer(self,identifier):
        if identifier not in self.layer_selection.selected_ids:self.select_layer_with_modifiers(identifier)
        values=self.duplicate_selected_layers();return values[0] if values else None
    def move_layer(self,identifier,direction):
        if not self.composition:return False
        before=deepcopy(self.composition.layers);index=next((i for i,item in enumerate(before) if item.id==identifier),-1);target=index+int(direction)
        if index<0 or self._layer_effectively_locked(self.composition.layers[index]) or target<0 or target>=len(before):return False
        after=deepcopy(before);layer=after.pop(index);after.insert(target,layer);self._push_value(self.composition.id,"layers",before,after,"Reorder Resource Layer");self.controller.select_layer(identifier);return True
    def reorder_layer(self,identifier,target_ui_index):
        if identifier not in self.layer_selection.selected_ids:self.select_layer_with_modifiers(identifier)
        return self.reorder_layers([identifier],target_ui_index)
    def add_property_to_layer(self,property_id):
        if not self.selected_layer or self._layer_effectively_locked(self.selected_layer):return None
        track=self.selected_layer.add_property(property_id);self.controller.changed();return track
    def set_keyframe(self,property_id,value,easing="Linear"):
        if not self.selected_layer or self._layer_effectively_locked(self.selected_layer):return
        before=deepcopy(self.selected_layer.tracks.get(property_id));after=deepcopy(before) if before else self.selected_layer.add_property(property_id);after=deepcopy(after);after.set_keyframe(self.frame_index,value,easing)
        if before is None:self.selected_layer.tracks.pop(property_id,None)
        self._push_value(self.selected_layer.id,"track:"+property_id,before,after,"Add Keyframe")
    def add_full_rotation(self,clockwise=True,turns=1):
        if not self.selected_layer or self._layer_effectively_locked(self.selected_layer):return
        before=deepcopy(self.selected_layer.tracks.get("rotation"));track=deepcopy(before) if before else self.selected_layer.add_property("rotation");track=deepcopy(track);track.keyframes.clear();track.set_keyframe(0,0,"Linear");count=self.composition.frame_count
        if count>1:track.set_keyframe(count-1,(360 if clockwise else -360)*turns*((count-1)/count if self.composition.loop else 1),"Linear")
        if before is None:self.selected_layer.tracks.pop("rotation",None)
        self._push_value(self.selected_layer.id,"track:rotation",before,track,"Full Rotation")

    def set_layer_locked(self,identifier,locked):
        layer=next((item for item in self.composition.layers if item.id==identifier),None) if self.composition else None
        locked=bool(locked)
        if layer is None or layer.locked==locked:return False
        self._push_value(identifier,"locked",layer.locked,locked,"Lock Resource Layer");return True

    def set_layer_solo(self,identifier,solo):
        layer=next((item for item in self.composition.layers if item.id==identifier),None) if self.composition else None
        solo=bool(solo)
        if layer is None or layer.solo==solo:return False
        self._push_value(identifier,"solo",layer.solo,solo,"Solo Resource Layer");return True

    def set_layer_parent(self,identifier,parent_id):
        if not self.composition:return False
        layer=next((item for item in self.composition.layers if item.id==identifier),None)
        parent_id=None if not parent_id else str(parent_id)
        if layer is None or self._layer_effectively_locked(layer) or would_create_parent_cycle(self.composition.layers,identifier,parent_id):return False
        before=self._selection_value()
        changed=set_parent_keep_world(self.composition.layers,identifier,parent_id,self.controller.state.frame,lambda item,frame:resource_local_affine(item,frame,self.composition))
        return self._commit_hierarchy(before,"Set Resource Layer Parent") if changed else False

    def duplicate_selected_layers(self):
        if not self.composition:return []
        selected={value for value in self.layer_selection.selected_ids if self.composition.group_by_id(value) is None};before=self._selection_value();existing={item.name for item in self.composition.layers};after=[];duplicates=[];primary_duplicate=None;duplicate_by_original={}
        for layer in self.composition.layers:
            after.append(deepcopy(layer))
            if layer.id not in selected:continue
            duplicate=deepcopy(layer);duplicate.id=uuid4().hex;base=re.sub(r" \(\d+\)$","",duplicate.name);number=2;name=f"{base} ({number})"
            while name in existing:number+=1;name=f"{base} ({number})"
            duplicate.name=name;existing.add(name);after.append(duplicate);duplicates.append(duplicate);duplicate_by_original[layer.id]=duplicate.id
            if layer.id==self.layer_selection.primary_id:primary_duplicate=duplicate.id
        if not duplicates:return []
        for original_id,duplicate_id in duplicate_by_original.items():
            original=next(item for item in self.composition.layers if item.id==original_id);duplicate=next(item for item in after if item.id==duplicate_id)
            if original.parent_id in duplicate_by_original:duplicate.parent_id=duplicate_by_original[original.parent_id]
        groups=deepcopy(self.composition.groups);root=deepcopy(self.composition.root_order)
        for group in groups:
            values=[]
            for value in group.children:values.extend([value,duplicate_by_original[value]] if value in duplicate_by_original else [value])
            group.children=values
        values=[]
        for node in root:
            values.append(node)
            if node["type"]=="layer" and node["id"] in duplicate_by_original:values.append(layer_node(duplicate_by_original[node["id"]]))
        root=values;duplicate_ids={item.id for item in duplicates};primary_duplicate=primary_duplicate or duplicates[-1].id;after_value=self._selection_value(after,duplicate_ids,primary_duplicate,primary_duplicate,groups=groups,root_order=root)
        self._push_value(self.composition.id,"layer_workflow",before,after_value,"Duplicate Selected Resource Layers");return [next(item for item in self.composition.layers if item.id==value.id) for value in duplicates]

    def delete_selected_layers(self):
        if not self.composition:return False
        selected=set(self.layer_selection.selected_ids);targets=[item for item in self.composition.layers if item.id in selected]
        if not targets:return False
        if any(self._layer_effectively_locked(item) for item in targets):self._report_locked_batch();return False
        if surviving_parent_dependencies(self.composition.layers,selected):return False
        before=self._selection_value();after=[deepcopy(item) for item in self.composition.layers if item.id not in selected];groups=deepcopy(self.composition.groups);root=deepcopy(self.composition.root_order)
        for group in groups:group.children=[value for value in group.children if value not in selected]
        root=[node for node in root if not (node["type"]=="layer" and node["id"] in selected)]
        remaining_ui=[item.id for item in reversed(after)];primary=remaining_ui[0] if remaining_ui else None;after_value=self._selection_value(after,{primary} if primary else set(),primary,primary)
        after_value["groups"]=groups;after_value["root_order"]=root
        self._push_value(self.composition.id,"layer_workflow",before,after_value,"Delete Selected Resource Layers");return True

    def set_selected_layer_state(self,field,value):
        if field not in {"locked","solo","visible"} or not self.composition:return False
        selected=set(self.layer_selection.selected_ids);before=self._selection_value(render=field=="visible");after=deepcopy(self.composition.layers);changed=False
        for layer in after:
            if layer.id in selected and getattr(layer,field)!=bool(value):setattr(layer,field,bool(value));changed=True
        if not changed:return False
        after_value=self._selection_value(after,render=field=="visible");self._push_value(self.composition.id,"layer_workflow",before,after_value,f"Set Selected Layers {field.title()}");return True

    def reorder_layers(self,identifiers,target_ui_index):
        if not self.composition:return False
        parents={self._parent_id(value) for value in identifiers}
        if self.composition.groups:
            if len(parents)!=1:return False
            return self.move_hierarchy_nodes(identifiers,next(iter(parents)),target_ui_index)
        selected=set(identifiers or self.layer_selection.selected_ids);ui=list(reversed(self.composition.layers));moving=[item for item in ui if item.id in selected]
        if not moving:return False
        if any(item.locked for item in moving):self._report_locked_batch();return False
        remaining=[item for item in ui if item.id not in selected];target=max(0,min(int(target_ui_index),len(remaining)));after_ui=remaining[:target]+moving+remaining[target:]
        if [item.id for item in after_ui]==[item.id for item in ui]:return False
        before=self._selection_value();after_value=self._selection_value(list(reversed(after_ui)));self._push_value(self.composition.id,"layer_workflow",before,after_value,"Reorder Selected Resource Layers");return True

    def move_selected_to_edge(self,front):return self.reorder_layers(self.layer_selection.selected_ids,0 if front else len(self.composition.layers)) if self.composition else False

    def _commit_hierarchy(self,before,text,render=True):
        after=self._selection_value(render=render);self._apply_undo_value(self.composition.id,"layer_workflow",before);self._push_value(self.composition.id,"layer_workflow",before,after,text);return True

    def _node_structurally_locked(self,identifier):
        group=self.composition.group_by_id(identifier) if self.composition else None
        if group:return group.locked or any(self._layer_effectively_locked(next((item for item in self.composition.layers if item.id==child),None)) for child in group.children)
        layer=next((item for item in self.composition.layers if item.id==identifier),None) if self.composition else None
        return self._layer_effectively_locked(layer)

    def create_group_selected(self):
        if not self.composition:return None
        selected=set(self.layer_selection.selected_ids);root=self.composition.root_order;indices=[i for i,node in enumerate(root) if node["type"]=="layer" and node["id"] in selected]
        if len(indices)<2 or len(indices)!=len(selected) or indices!=list(range(min(indices),max(indices)+1)):return None
        children=[root[index]["id"] for index in indices]
        if any(self._node_structurally_locked(value) for value in children):return None
        before=self._selection_value();existing={group.name for group in self.composition.groups};name="Group";number=2
        while name in existing:name=f"Group ({number})";number+=1
        group=LayerGroup(name=name,children=children);start=indices[0];self.composition.groups.append(group);self.composition.root_order=root[:start]+[group_node(group.id)]+root[indices[-1]+1:];self.composition.sync_flat_order();self.expanded_group_ids.add(group.id);self.layer_selection.restore({"selected_ids":[group.id],"primary_id":group.id,"anchor_id":group.id},self._ui_node_ids(False));self.controller.state.layer_id=None;self._commit_hierarchy(before,"Group Selected Resource Layers");return self.composition.group_by_id(group.id)

    def toggle_group_expanded(self,identifier,expanded=None):
        group=self.composition.group_by_id(identifier) if self.composition else None
        if group is None:return False
        expanded=(identifier not in self.expanded_group_ids) if expanded is None else bool(expanded)
        if expanded:self.expanded_group_ids.add(identifier);getattr(self,"_collapsed_group_ids",set()).discard(identifier)
        else:
            if not hasattr(self,"_collapsed_group_ids"):self._collapsed_group_ids=set()
            self._collapsed_group_ids.add(identifier);self.expanded_group_ids.discard(identifier)
            if any(child in self.layer_selection.selected_ids for child in group.children):self.layer_selection.restore({"selected_ids":[identifier],"primary_id":identifier,"anchor_id":identifier},self._ui_node_ids(False));self.controller.state.layer_id=None
        self._apply_state(self.controller.state);return True

    def set_all_groups_expanded(self,expanded):
        if not self.composition:return False
        group_ids={group.id for group in self.composition.groups};expanded=bool(expanded)
        if expanded:
            self.expanded_group_ids|=group_ids;self._collapsed_group_ids-=group_ids
        else:
            self.expanded_group_ids-=group_ids;self._collapsed_group_ids|=group_ids
            primary=self.layer_selection.primary_id;target=next((group for group in self.composition.groups if primary in group.children),None)
            if target is None:target=next((group for group in self.composition.groups if any(child in self.layer_selection.selected_ids for child in group.children)),None)
            if target is not None:self.layer_selection.restore({"selected_ids":[target.id],"primary_id":target.id,"anchor_id":target.id},self._ui_node_ids(False));self.controller.state.layer_id=None
        self._apply_state(self.controller.state);return True

    def ungroup(self,identifier=None):
        identifier=identifier or self.layer_selection.primary_id;group=self.composition.group_by_id(identifier) if self.composition else None
        if group is None or self._node_structurally_locked(group.id):return False
        before=self._selection_value();index=next(i for i,node in enumerate(self.composition.root_order) if node["type"]=="group" and node["id"]==group.id);self.composition.root_order[index:index+1]=[layer_node(value) for value in group.children];self.composition.groups.remove(group);self.expanded_group_ids.discard(group.id);selected=list(reversed(group.children));primary=selected[0] if selected else next((node["id"] for node in reversed(self.composition.root_order)),None);self.layer_selection.restore({"selected_ids":selected or ([primary] if primary else []),"primary_id":primary,"anchor_id":primary},self._ui_node_ids(False));self.controller.state.layer_id=primary;return self._commit_hierarchy(before,"Ungroup Resource Layers")

    def rename_group(self,identifier,name):
        group=self.composition.group_by_id(identifier) if self.composition else None;base=str(name).strip()
        if group is None or group.locked or not base or base==group.name:return False
        existing={item.name for item in self.composition.groups if item.id!=identifier};safe=base;number=2
        while safe in existing:safe=f"{base} ({number})";number+=1
        before=self._selection_value(render=False);group.name=safe;return self._commit_hierarchy(before,"Rename Resource Group",render=False)

    def set_group_state(self,identifier,field,value):
        group=self.composition.group_by_id(identifier) if self.composition else None
        if group is None or field not in {"visible","locked","solo"} or getattr(group,field)==bool(value):return False
        before=self._selection_value(render=field in {"visible","solo"});setattr(group,field,bool(value));return self._commit_hierarchy(before,f"Set Resource Group {field.title()}",render=field in {"visible","solo"})

    def duplicate_group(self,identifier=None):
        identifier=identifier or self.layer_selection.primary_id;group=self.composition.group_by_id(identifier) if self.composition else None
        if group is None:return None
        before=self._selection_value();existing_group_names={item.name for item in self.composition.groups};base=re.sub(r" \(\d+\)$","",group.name);number=2;name=f"{base} ({number})"
        while name in existing_group_names:number+=1;name=f"{base} ({number})"
        existing_layer_names={item.name for item in self.composition.layers};by_id={item.id:item for item in self.composition.layers};children=[];duplicates=[]
        for child in group.children:
            duplicate=deepcopy(by_id[child]);duplicate.id=uuid4().hex;base_name=re.sub(r" \(\d+\)$","",duplicate.name);number=2;leaf_name=f"{base_name} ({number})"
            while leaf_name in existing_layer_names:number+=1;leaf_name=f"{base_name} ({number})"
            duplicate.name=leaf_name;existing_layer_names.add(leaf_name);children.append(duplicate.id);duplicates.append(duplicate)
        remap={old:new for old,new in zip(group.children,children)}
        for duplicate in duplicates:
            if duplicate.parent_id in remap:duplicate.parent_id=remap[duplicate.parent_id]
        copy_group=deepcopy(group);copy_group.id=uuid4().hex;copy_group.name=name;copy_group.children=children;self.composition.layers.extend(duplicates);self.composition.groups.append(copy_group);index=next(i for i,node in enumerate(self.composition.root_order) if node["id"]==group.id);self.composition.root_order.insert(index+1,group_node(copy_group.id));self.composition.sync_flat_order();self.expanded_group_ids.add(copy_group.id);self.layer_selection.restore({"selected_ids":[copy_group.id],"primary_id":copy_group.id,"anchor_id":copy_group.id},self._ui_node_ids(False));self.controller.state.layer_id=None;self._commit_hierarchy(before,"Duplicate Resource Group");return self.composition.group_by_id(copy_group.id)

    def delete_group(self,identifier=None):
        identifier=identifier or self.layer_selection.primary_id;group=self.composition.group_by_id(identifier) if self.composition else None
        if group is None or self._node_structurally_locked(group.id):return False
        if surviving_parent_dependencies(self.composition.layers,set(group.children)):return False
        before=self._selection_value();children=set(group.children);self.composition.layers=[item for item in self.composition.layers if item.id not in children];self.composition.groups.remove(group);self.composition.root_order=[node for node in self.composition.root_order if node["id"]!=group.id];self.expanded_group_ids.discard(group.id);ui=self._ui_node_ids(False);primary=ui[0] if ui else None;self.layer_selection.restore({"selected_ids":[primary] if primary else [],"primary_id":primary,"anchor_id":primary},ui);self.controller.state.layer_id=primary if any(item.id==primary for item in self.composition.layers) else None;return self._commit_hierarchy(before,"Delete Resource Group")

    def move_hierarchy_nodes(self,identifiers,target_parent_id=None,target_ui_index=0):
        if not self.composition:return False
        selected=set(identifiers);parents={self._parent_id(value) for value in selected}
        if len(parents)!=1 or any(self._node_structurally_locked(value) for value in selected):return False
        source_parent=next(iter(parents));source_group=self.composition.group_by_id(source_parent) if source_parent else None;target_group=self.composition.group_by_id(target_parent_id) if target_parent_id else None
        if target_group and (target_group.locked or any(self.composition.group_by_id(value) for value in selected)):return False
        source_ui=list(reversed(source_group.children)) if source_group else self._ui_root_ids();moving=[value for value in source_ui if value in selected]
        if not moving:return False
        remaining=[value for value in source_ui if value not in selected]
        target_ui=(list(reversed(target_group.children)) if target_group else self._ui_root_ids()) if source_parent!=target_parent_id else remaining
        target=max(0,min(int(target_ui_index),len(target_ui)));after_ui=target_ui[:target]+moving+target_ui[target:]
        if source_parent==target_parent_id and after_ui==source_ui:return False
        before=self._selection_value()
        if source_group:source_group.children=list(reversed(remaining))
        else:self.composition.root_order=[node for node in self.composition.root_order if node["id"] not in selected]
        if target_group:target_group.children=list(reversed(after_ui))
        else:
            kind={group.id:"group" for group in self.composition.groups};self.composition.root_order=[{"type":kind.get(value,"layer"),"id":value} for value in reversed(after_ui)]
        self.composition.sync_flat_order();return self._commit_hierarchy(before,"Move Resource Hierarchy Nodes")

    def move_selected_hierarchy_to_edge(self,front):
        selected=set(self.layer_selection.selected_ids);parent=next(iter({self._parent_id(value) for value in selected}),None);siblings=self._ui_siblings(next(iter(selected))) if selected else []
        return self.move_hierarchy_nodes(selected,parent,0 if front else len(siblings))

    def _report_locked_batch(self):
        message=self.localization.text("layer.batch.locked_block") if self.localization else "The selection contains a locked layer."
        self.composition_timeline.selection_status.setToolTip(message)
        status=getattr(self.window(),"statusBar",None)
        if callable(status):status().showMessage(message,4000)

    def batch_command(self,command):
        primary_group=self.composition.group_by_id(self.layer_selection.primary_id) if self.composition else None
        if command=="group":return self.create_group_selected()
        if command=="ungroup":return self.ungroup()
        if primary_group and command=="duplicate":return self.duplicate_group()
        if primary_group and command=="delete":return self.delete_group()
        if primary_group and command in {"lock","unlock","solo","unsolo","show","hide","toggle_lock","toggle_solo"}:
            field={"lock":"locked","unlock":"locked","toggle_lock":"locked","solo":"solo","unsolo":"solo","toggle_solo":"solo","show":"visible","hide":"visible"}[command];value=(not getattr(primary_group,field)) if command.startswith("toggle") else command in {"lock","solo","show"};return self.set_group_state(primary_group.id,field,value)
        if command in {"front","back"} and any(self.composition.group_by_id(value) for value in self.layer_selection.selected_ids):return self.move_selected_hierarchy_to_edge(command=="front")
        selected=[item for item in self.composition.layers if item.id in self.layer_selection.selected_ids] if self.composition else []
        if command=="duplicate":return self.duplicate_selected_layers()
        if command=="delete":return self.delete_selected_layers()
        if command in {"lock","unlock","solo","unsolo","show","hide"}:
            field={"lock":"locked","unlock":"locked","solo":"solo","unsolo":"solo","show":"visible","hide":"visible"}[command];return self.set_selected_layer_state(field,command in {"lock","solo","show"})
        if command=="toggle_lock":return self.set_selected_layer_state("locked",not all(item.locked for item in selected))
        if command=="toggle_solo":return self.set_selected_layer_state("solo",not all(item.solo for item in selected))
        if command=="front":return self.move_selected_to_edge(True)
        if command=="back":return self.move_selected_to_edge(False)
        return False
