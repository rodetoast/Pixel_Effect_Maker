"""Main application window and UI orchestration."""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from time import perf_counter

from PySide6.QtCore import QElapsedTimer, QSignalBlocker, QTimer, Qt, Slot
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QVBoxLayout,
    QWidget,
    QSplitter,
    QStackedWidget,
    QPushButton,
    QSizePolicy,
)

from app.models.effect_generator import TransformEmitter, TransformEmitterSettings
from app.models.frame import empty_pixels
from app.models.layer import Layer
from app.models.project import Project, ProjectError
from app.models.source_asset import SourceAsset
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings
from app.models.effect_composition_layer import EffectCompositionLayer
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE, PLACEMENT_SINGLE
from app.services.clip_service import create_clip_from_generator, update_clip_from_generator
from app.services.particle_render_service import apply_particle_frames, render_particle_frames, invalidate_particle_render_caches
from app.services.particle_preview_service import ParticlePreviewManager
from app.services.preview_export_service import export_preview_sequence
from app.services.export_service import ExportError, export_png_frames
from app.services.effect_render_service import (
    EffectRenderError,
    apply_rendered_frames,
    generate_emitter,
)
from app.services.preview_service import (
    PreviewManager,
    PreviewRenderSnapshot,
    render_preview_snapshot,
)
from app.services.localization_service import LocalizationService
from app.services.project_io import ProjectIOError, load_project, save_project
from app.services.canvas_resize_service import (
    CanvasResizeError,
    CanvasResizeMode,
    resize_canvas,
    scale_project,
)
from app.services.sample_project_service import create_playback_test_project
from app.services.source_import_service import SourceImportError, import_source_asset
from app.services.resource_import_service import ResourceImportError, import_resource
from app.services.aseprite_import_service import import_aseprite
from app.services.aseprite_locator_service import locate_aseprite, validate_aseprite
from app.services.resource_composition_render_service import invalidate_composition_cache
from app.services.effect_composition_layer_render_service import render_effect_composition_layer, apply_effect_composition_layer
from app.services.effect_resource_layer_render_service import render_effect_resource_layer, apply_effect_resource_layer, apply_effect_resource_layer_current_frame, invalidate_effect_resource_layer_base, render_effect_resource_layer_base_frame, render_effect_resource_layer_current_base_frame, effect_resource_layer_base_frame_key
from app.services.settings_service import SettingsError, ShortcutSettingsService
from app.services.runtime_diagnostics import build_diagnostic_text, log_exception, runtime_logger, safe_path_label
from app.services.effect_playback_service import EffectPlaybackManager,PLAYBACK_STOPPED,PLAYBACK_PREPARING,PLAYBACK_PLAYING
from app.services.interactive_gizmo_service import InteractiveGizmoRenderManager
from app.shortcuts import DEFAULT_SHORTCUTS
from app.version import get_display_name

from .canvas_widget import CanvasWidget
from .effect_library_panel import EffectLibraryPanel
from .effect_properties_panel import EffectPropertiesPanel
from .particle_properties_panel import ParticlePropertiesPanel
from .composition_layer_properties_panel import CompositionLayerPropertiesPanel
from .frame_shortcut_controller import FrameShortcutController
from .keyboard_shortcuts_dialog import KeyboardShortcutsDialog
from .new_project_dialog import NewProjectDialog
from .playback_shortcut_controller import PlaybackShortcutController
from .project_settings_dialog import ProjectSettingsDialog, ProjectSettingsValues
from .timeline_widget import TimelineWidget
from .resource_editor_v2 import ResourceEditorWidget
from .external_tools_dialog import ExternalToolsDialog
from .interface_settings_dialog import InterfaceSettingsDialog, timeline_frame_width
from .undo_commands import EditorOperationCommand, EditorValueCommand
from .tooltip_helper import apply_tooltip
from .interactive_proxy_prewarm import InteractiveProxyPrewarmManager
from .preview_build_notice_dialog import PreviewBuildNoticeDialog


class MainWindow(QMainWindow):
    """Coordinate project state, services, and editor widgets."""

    def __init__(
        self, settings_service: ShortcutSettingsService | None = None, initial_project: Project | None = None
    ) -> None:
        super().__init__()
        self.setWindowTitle(get_display_name())
        self.resize(1280, 800)
        # The invisible pre-startup placeholder stays deliberately small; every
        # user-facing New Project path uses the central 600x600/12-frame defaults.
        self.project = initial_project or Project.create_default(width=64,height=64,frame_count=1)
        self.project_path: Path | None = None
        self.frame_index = 0
        self.layer_index = 0
        self.dirty = False
        self._non_undo_dirty=False
        self._project_edit_revision=0
        self._save_in_progress=False
        self.settings_service = settings_service or ShortcutSettingsService()
        self.localization = LocalizationService(self.settings_service.settings)
        self.application_undo_stack = QUndoStack(self)
        self.preview_manager = PreviewManager(
            self.settings_service.settings, parent=self
        )
        self.particle_preview_manager = ParticlePreviewManager(self)
        self.active_preview_generator_id: str | None = None
        self._effect_guide_before = None
        try:
            self.shortcuts = self.settings_service.load()
        except SettingsError:
            self.shortcuts = dict(DEFAULT_SHORTCUTS)
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(lambda:self._advance_playback(False))
        self._playback_clock=QElapsedTimer();self._playback_start_frame=0;self._playback_last_step=0
        self._playback_state=PLAYBACK_STOPPED;self._playback_plan=None
        self._pending_resource_transforms={}
        self._dirty_resource_transform_layers=set()
        self.resource_transform_render_timer=QTimer(self);self.resource_transform_render_timer.setSingleShot(True);self.resource_transform_render_timer.timeout.connect(self._flush_resource_transform_current)
        self.resource_transform_finalize_timer=QTimer(self);self.resource_transform_finalize_timer.setSingleShot(True);self.resource_transform_finalize_timer.timeout.connect(self._flush_resource_transform_final)
        self._pending_particle_motion={}
        self._pending_particle_motion_layers={}
        self._dirty_particle_motion_layers=set()
        self.particle_motion_render_timer=QTimer(self);self.particle_motion_render_timer.setSingleShot(True);self.particle_motion_render_timer.timeout.connect(self._flush_particle_motion_current)
        self.particle_motion_finalize_timer=QTimer(self);self.particle_motion_finalize_timer.setSingleShot(True);self.particle_motion_finalize_timer.timeout.connect(self._flush_particle_motion_final)
        self._pending_transform_inspector=None;self.transform_inspector_timer=QTimer(self);self.transform_inspector_timer.setSingleShot(True);self.transform_inspector_timer.timeout.connect(self._flush_transform_inspector_sync)
        self._pending_guide_inspector=None;self.guide_inspector_timer=QTimer(self);self.guide_inspector_timer.setSingleShot(True);self.guide_inspector_timer.timeout.connect(self._flush_guide_inspector_sync)
        self._timeline_scrubbing=False

        self._build_ui()
        self.effect_playback=EffectPlaybackManager(self)
        self.effect_playback.frame_ready.connect(self._playback_frame_ready)
        self.effect_playback.preparation_failed.connect(self._playback_preparation_failed)
        self.interactive_gizmo_renderer=InteractiveGizmoRenderManager(self)
        self._pending_interactive_gizmo_results={}
        self.interactive_gizmo_renderer.ready.connect(self._interactive_gizmo_frame_ready)
        self.interactive_gizmo_renderer.failed.connect(lambda message:runtime_logger().error("interactive_gizmo failed message=%s",message))
        self.interactive_proxy_prewarm=InteractiveProxyPrewarmManager(self._build_resource_transform_prewarm_payload,self)
        self.interactive_proxy_prewarm.ready.connect(self._install_resource_transform_prewarm)
        self._build_menus()
        self.resource_editor.set_undo_stack(self.application_undo_stack)
        self.application_undo_stack.indexChanged.connect(self._undo_index_changed)
        self._connect_signals()
        self.playback_shortcut_controller = PlaybackShortcutController(
            self, self.toggle_workspace_playback
        )
        self.playback_shortcut_controller.set_sequences(
            self.shortcuts.get("play_stop_animation", [])
        )
        self.frame_shortcut_controller = FrameShortcutController(
            self,
            self.previous_workspace_frame,
            self.next_workspace_frame,
            [self.timeline.table,self.resource_editor.composition_timeline.table,self.resource_editor.asset_strip],
        )
        self.frame_shortcut_controller.set_sequences(self.shortcuts)
        self.localization.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._refresh_all()

    def _build_ui(self) -> None:
        outer = QWidget(); outer_layout = QVBoxLayout(outer); outer_layout.setContentsMargins(4,4,4,4)
        workspace_row=QHBoxLayout();self.effect_workspace_button=QPushButton("Effect Editor");self.resource_workspace_button=QPushButton("Resource Editor")
        for button in (self.effect_workspace_button,self.resource_workspace_button):button.setCheckable(True);workspace_row.addWidget(button)
        workspace_row.addStretch();outer_layout.addLayout(workspace_row);self.workspace_stack=QStackedWidget();outer_layout.addWidget(self.workspace_stack,1)
        container = QWidget()
        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(4, 4, 4, 4)
        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_splitter.setObjectName("editorSplitter")
        self.editor_splitter.setChildrenCollapsible(False)
        self.effect_library = EffectLibraryPanel()
        self.editor_splitter.addWidget(self.effect_library)
        self.canvas = CanvasWidget()
        self.editor_splitter.addWidget(self.canvas)
        self.effect_properties = EffectPropertiesPanel()
        self.effect_properties.auto_preview_check.setChecked(
            self.preview_manager.auto_preview
        )
        self.particle_properties = ParticlePropertiesPanel()
        self.composition_layer_properties = CompositionLayerPropertiesPanel()
        self.properties_stack = QStackedWidget(); self.properties_stack.setMinimumWidth(280);self.properties_stack.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Expanding)
        self.properties_stack.addWidget(self.effect_properties); self.properties_stack.addWidget(self.particle_properties); self.properties_stack.addWidget(self.composition_layer_properties)
        self.editor_splitter.addWidget(self.properties_stack)
        self.editor_splitter.setStretchFactor(0, 0)
        self.editor_splitter.setStretchFactor(1, 1)
        self.editor_splitter.setStretchFactor(2, 0)
        self._restore_splitter_sizes()
        self.editor_splitter.splitterMoved.connect(self._save_splitter_sizes)
        root_layout.addWidget(self.editor_splitter, 1)
        self.timeline = TimelineWidget()
        self.timeline.set_frame_cell_width(timeline_frame_width(self.settings_service.settings))
        root_layout.addWidget(self.timeline)
        self.resource_editor=ResourceEditorWidget(self.settings_service.settings)
        self.workspace_stack.addWidget(container);self.workspace_stack.addWidget(self.resource_editor);self.workspace_stack.setCurrentIndex(0);self.effect_workspace_button.setChecked(True)
        self.effect_workspace_button.clicked.connect(lambda:self.set_workspace("effect"));self.resource_workspace_button.clicked.connect(lambda:self.set_workspace("resource"))
        self.setCentralWidget(outer)

    def set_workspace(self, workspace: str) -> None:
        resource=workspace=="resource"
        if resource:self._flush_resource_transform_final()
        if resource:self.resource_editor.refresh(self.project)
        self.workspace_stack.setCurrentIndex(1 if resource else 0);self.effect_workspace_button.setChecked(not resource);self.resource_workspace_button.setChecked(resource);self.settings_service.settings.setValue("ui/workspace",workspace)

    def toggle_workspace_playback(self) -> None:
        if self.workspace_stack.currentIndex()==1:self.resource_editor.toggle_play()
        else:self.play_action.trigger()

    def previous_workspace_frame(self) -> None:
        if self.workspace_stack.currentIndex()==1:self.resource_editor.previous_frame()
        else:self.previous_frame()

    def next_workspace_frame(self) -> None:
        if self.workspace_stack.currentIndex()==1:self.resource_editor.next_frame()
        else:self.next_frame()

    def _restore_splitter_sizes(self) -> None:
        value = self.settings_service.settings.value("ui/editor_splitter_sizes")
        try:
            sizes = [int(item) for item in value] if isinstance(value, (list, tuple)) else []
        except (TypeError, ValueError):
            sizes = []
        if len(sizes) != 3 or min(sizes) < 100 or sizes[2] < 280:
            sizes = [230, 700, 300]
        self.editor_splitter.setSizes(sizes)

    def _save_splitter_sizes(self, *args) -> None:
        sizes = self.editor_splitter.sizes()
        if len(sizes) == 3 and sizes[2] >= 280:
            self.settings_service.settings.setValue("ui/editor_splitter_sizes", sizes)

    def _build_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu("File")
        self.new_action = QAction("New Project…", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.open_action = QAction("Open…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.save_action = QAction("Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_as_action = QAction("Save As…", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.project_settings_action = QAction("Project Settings…", self)
        self.exit_action=QAction("Exit",self)
        self.import_source_action = QAction("Import Source Asset…", self)
        self.import_resources_action = QAction("Import Resources…", self)
        self.external_tools_action = QAction("External Tools…", self)
        self.playback_test_action = QAction("Create Playback Test Project", self)
        self.playback_test_action.setStatusTip(
            "Create an 8-frame sample project for checking animation playback."
        )
        self.export_action = QAction("Export PNG Frames…", self)
        self.file_menu.addActions(
            [self.new_action, self.open_action, self.save_action, self.save_as_action]
        )
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.import_source_action)
        self.file_menu.addAction(self.import_resources_action)
        self.file_menu.addSeparator();self.file_menu.addAction(self.exit_action)

        self.edit_menu = self.menuBar().addMenu("Edit")
        self.undo_action=self.application_undo_stack.createUndoAction(self)
        self.redo_action=self.application_undo_stack.createRedoAction(self)
        self.undo_action.setShortcuts([QKeySequence("Ctrl+Z")]);self.redo_action.setShortcuts([QKeySequence("Ctrl+Shift+Z"),QKeySequence("Ctrl+Y")])
        self.keyboard_shortcuts_action = QAction("Keyboard Shortcuts…", self)
        self.edit_menu.addActions([self.undo_action,self.redo_action]);self.edit_menu.addSeparator();self.edit_menu.addAction(self.project_settings_action);self.edit_menu.addAction(self.keyboard_shortcuts_action)

        self.layer_menu = self.menuBar().addMenu("Layer")
        self.new_layer_action = QAction("New Layer", self)
        self.delete_layer_action = QAction("Delete Layer", self)
        self.layer_menu.addActions([self.new_layer_action, self.delete_layer_action])
        self.layer_menu.addSeparator()
        self.add_composition_layer_action = QAction("Add Resource Layer", self)
        self.add_resource_layer_action = self.add_composition_layer_action
        self.add_particle_system_action = QAction("Add Particle System", self)
        self.layer_menu.addAction(self.add_resource_layer_action)

        self.frame_menu = self.menuBar().addMenu("Frame")
        self.new_frame_action = QAction("New Frame (Duplicate Current)", self)
        self.new_empty_frame_action = QAction("New Empty Frame", self)
        self.delete_frame_action = QAction("Delete Frame", self)
        self.frame_menu.addActions(
            [
                self.new_frame_action,
                self.new_empty_frame_action,
                self.delete_frame_action,
            ]
        )

        self.animation_menu = self.menuBar().addMenu("Animation")
        self.play_action = QAction("Play / Stop Animation", self, checkable=True)

        self.view_menu = self.menuBar().addMenu("View")
        self.status_bar_action = QAction("Status Bar", self, checkable=True)
        self.status_bar_action.setChecked(True)
        self.view_menu.addAction(self.status_bar_action)
        self.editing_guides_action = QAction("Show Editing Guides", self, checkable=True)
        self.editing_guides_action.setChecked(str(self.settings_service.settings.value("ui/show_effect_editing_guides", "true")).lower() not in {"false", "0"})
        self.canvas.set_effect_guides_visible(self.editing_guides_action.isChecked())
        self.view_menu.addAction(self.editing_guides_action)

        self.export_menu = self.menuBar().addMenu("Export")
        self.export_menu.addAction(self.export_action)

        self.settings_menu = self.menuBar().addMenu("Settings")
        self.interface_settings_action=QAction("Interface Settings…",self)
        self.language_menu = self.settings_menu.addMenu("Language")
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        self.korean_action = QAction("한국어", self, checkable=True)
        self.english_action = QAction("English", self, checkable=True)
        self.language_group.addAction(self.korean_action)
        self.language_group.addAction(self.english_action)
        self.language_menu.addActions([self.korean_action, self.english_action])
        self.settings_menu.addSeparator();self.settings_menu.addAction(self.interface_settings_action);self.settings_menu.addAction(self.external_tools_action)
        self.korean_action.triggered.connect(
            lambda: self.localization.set_language("ko")
        )
        self.english_action.triggered.connect(
            lambda: self.localization.set_language("en")
        )

        self.help_menu = self.menuBar().addMenu("Help")
        self.project_overview_action = QAction("Project Overview and Development Status…", self)
        self.copy_diagnostics_action = QAction("Copy Diagnostic Information", self)
        self.help_menu.addActions([self.project_overview_action, self.copy_diagnostics_action])

        # Compatibility aliases for the existing action-oriented tests and code.
        self.add_layer_action = self.new_layer_action
        self.duplicate_frame_action = self.new_frame_action
        self.add_frame_action = self.new_empty_frame_action
        self.shortcut_actions = {
            "undo": self.undo_action,
            "redo": self.redo_action,
            "new_layer": self.new_layer_action,
            "new_frame": self.new_frame_action,
            "new_empty_frame": self.new_empty_frame_action,
        }
        self._update_action_shortcuts(self.shortcuts)

    def retranslate_ui(self, *args) -> None:
        t = self.localization.text
        self.file_menu.setTitle(t("menu.file"))
        self.edit_menu.setTitle(t("menu.edit"))
        self.layer_menu.setTitle(t("menu.layer"))
        self.frame_menu.setTitle(t("menu.frame"))
        self.animation_menu.setTitle(t("menu.animation"))
        self.view_menu.setTitle(t("menu.view"))
        self.export_menu.setTitle(t("menu.export"))
        self.settings_menu.setTitle(t("menu.settings"))
        self.help_menu.setTitle(t("menu.help"))
        self.language_menu.setTitle(t("menu.language"))
        mapping = {
            self.new_action: "action.new_project",
            self.open_action: "action.open",
            self.save_action: "action.save",
            self.save_as_action: "action.save_as",
            self.project_settings_action: "action.project_settings",
            self.exit_action: "action.exit",
            self.import_source_action: "action.import_source",
            self.import_resources_action: "resource.import",
            self.external_tools_action: "external.title",
            self.playback_test_action: "action.playback_test",
            self.export_action: "action.export_frames",
            self.keyboard_shortcuts_action: "action.keyboard_shortcuts",
            self.new_layer_action: "action.new_layer",
            self.delete_layer_action: "action.delete_layer",
            self.new_frame_action: "action.new_frame",
            self.new_empty_frame_action: "action.new_empty_frame",
            self.delete_frame_action: "action.delete_frame",
            self.play_action: "action.play_stop",
            self.status_bar_action: "action.status_bar",
            self.interface_settings_action: "interface.title",
            self.add_resource_layer_action: "resource_layer.add",
            self.editing_guides_action: "effect.editing_guides",
            self.project_overview_action: "action.project_overview",
            self.copy_diagnostics_action: "action.copy_diagnostics",
        }
        for action, key in mapping.items():
            action.setText(t(key))
        self.korean_action.setText(t("language.ko"))
        self.english_action.setText(t("language.en"))
        self.korean_action.setChecked(self.localization.language == "ko")
        self.english_action.setChecked(self.localization.language == "en")
        self.effect_library.retranslate_ui(self.localization)
        self.effect_properties.retranslate_ui(self.localization)
        self.particle_properties.retranslate_ui(self.localization)
        self.composition_layer_properties.retranslate_ui(self.localization)
        self.resource_editor.retranslate_ui(self.localization)
        self.effect_workspace_button.setText(t("workspace.effect"));self.resource_workspace_button.setText(t("workspace.resource"))
        self.timeline.retranslate_ui(self.localization)
        if hasattr(self,"project"):
            self._update_resource_layer_display_names()
        self._refresh_undo_action_texts()
        self._refresh_tooltips()
        self.canvas.preview_badge_text = t("effects.preview_badge")
        self.canvas.set_resource_transform_tooltips({name:t("tooltip.resource_layer.move_"+name) for name in ("x","y","z")}|{"center":t("tooltip.resource_layer.move_center")})
        self.canvas.update()
        self._refresh_playback_status()

    def _refresh_tooltips(self) -> None:
        action_keys = {
            self.new_action: "tooltip.main.new", self.open_action: "tooltip.main.open",
            self.save_action: "tooltip.main.save", self.save_as_action: "tooltip.main.save_as",
            self.project_settings_action: "tooltip.main.project_settings", self.exit_action: "tooltip.main.exit",
            self.import_source_action: "tooltip.main.import_source", self.import_resources_action: "tooltip.main.import_resources",
            self.external_tools_action: "tooltip.main.external_tools", self.playback_test_action: "tooltip.main.playback_test",
            self.export_action: "tooltip.main.export", self.keyboard_shortcuts_action: "tooltip.main.shortcuts",
            self.new_layer_action: "tooltip.main.new_layer", self.delete_layer_action: "tooltip.main.delete_layer",
            self.new_frame_action: "tooltip.main.duplicate_frame", self.new_empty_frame_action: "tooltip.main.empty_frame",
            self.delete_frame_action: "tooltip.main.delete_frame", self.status_bar_action: "tooltip.main.status_bar",
            self.interface_settings_action: "tooltip.main.interface", self.undo_action: "tooltip.undo",
            self.redo_action: "tooltip.redo",
            self.add_resource_layer_action: "tooltip.resource_layer.add",
            self.editing_guides_action: "tooltip.effect.show_guides",
            self.project_overview_action: "tooltip.main.project_overview",
            self.copy_diagnostics_action: "tooltip.main.copy_diagnostics",
        }
        for action, key in action_keys.items():
            apply_tooltip(action, self.localization, key, action)
        play_key = "tooltip.timeline.pause" if self.play_timer.isActive() else "tooltip.timeline.play"
        play_shortcuts = self.shortcuts.get("play_stop_animation", [])
        apply_tooltip(self.play_action, self.localization, play_key, play_shortcuts)
        apply_tooltip(self.effect_workspace_button, self.localization, "tooltip.workspace.effect")
        apply_tooltip(self.resource_workspace_button, self.localization, "tooltip.workspace.resource")
        apply_tooltip(self.canvas, self.localization, "tooltip.effect.canvas_guides", status=False)
        apply_tooltip(self.korean_action, self.localization, "tooltip.main.language_ko")
        apply_tooltip(self.english_action, self.localization, "tooltip.main.language_en")
        self.timeline.set_shortcuts(
            play_shortcuts,
            self.shortcuts.get("previous_frame", []),
            self.shortcuts.get("next_frame", []),
            self.shortcuts,
        )
        self.resource_editor.set_shortcuts(
            play_shortcuts,
            self.shortcuts.get("previous_frame", []),
            self.shortcuts.get("next_frame", []),
        )

    def _connect_signals(self) -> None:
        self.new_action.triggered.connect(self.new_project)
        self.open_action.triggered.connect(self.open_project)
        self.save_action.triggered.connect(self.save)
        self.save_as_action.triggered.connect(self.save_as)
        self.project_settings_action.triggered.connect(self.show_project_settings)
        self.exit_action.triggered.connect(self.close)
        self.import_source_action.triggered.connect(self.import_source_asset)
        self.import_resources_action.triggered.connect(self.import_resources)
        self.external_tools_action.triggered.connect(self.show_external_tools)
        self.interface_settings_action.triggered.connect(self.show_interface_settings)
        self.playback_test_action.triggered.connect(self.create_playback_test)
        self.export_action.triggered.connect(self.export_frames)
        self.keyboard_shortcuts_action.triggered.connect(
            self.show_keyboard_shortcuts
        )
        self.new_frame_action.triggered.connect(self.duplicate_frame)
        self.new_empty_frame_action.triggered.connect(self.add_frame)
        self.delete_frame_action.triggered.connect(self.delete_frame)
        self.new_layer_action.triggered.connect(self.add_layer)
        self.delete_layer_action.triggered.connect(self.delete_layer)
        self.play_action.toggled.connect(self.set_playing)
        self.status_bar_action.toggled.connect(self.statusBar().setVisible)
        self.editing_guides_action.toggled.connect(self._set_effect_guides_visible)
        self.add_resource_layer_action.triggered.connect(self.add_default_resource_layer)
        self.project_overview_action.triggered.connect(self.show_project_overview)
        self.copy_diagnostics_action.triggered.connect(self.copy_diagnostic_information)
        self.timeline.add_requested.connect(self.add_frame)
        self.timeline.duplicate_requested.connect(self.duplicate_frame)
        self.timeline.delete_requested.connect(self.delete_frame)
        self.timeline.add_layer_requested.connect(self.add_layer)
        self.timeline.delete_layer_requested.connect(self.delete_layer)
        self.timeline.delete_layer_context_requested.connect(self._delete_layer_at)
        self.timeline.cell_selected.connect(self.select_cell)
        self.timeline.scrub_started.connect(self._resource_timeline_scrub_started)
        self.timeline.scrub_finished.connect(self._resource_timeline_scrub_finished)
        self.timeline.play_requested.connect(self.play_action.trigger)
        self.timeline.fps_changed.connect(self.set_fps)
        self.timeline.layer_visibility_requested.connect(self.set_layer_visibility)
        self.effect_library.import_requested.connect(self.import_source_asset)
        self.effect_library.add_emitter_requested.connect(self.add_transform_emitter)
        self.effect_library.asset_selected.connect(self.select_source_asset)
        self.effect_library.generator_selected.connect(self.select_generator)
        self.effect_library.delete_asset_requested.connect(self.delete_source_asset)
        self.effect_library.delete_generator_requested.connect(self.delete_generator)
        self.effect_library.create_clip_requested.connect(self.create_animation_clip)
        self.effect_library.add_particle_requested.connect(self.add_particle_emitter)
        self.effect_library.add_particle_from_resource_requested.connect(self.create_particle_from_resource)
        self.effect_library.clip_selected.connect(self.select_animation_clip)
        self.effect_library.particle_selected.connect(self.select_resource_layer)
        self.effect_library.composition_selected.connect(self.select_resource_layer)
        self.effect_library.add_composition_requested.connect(self.create_resource_layer_from_resource)
        self.effect_library.resource_open_requested.connect(self.open_resource_editor)
        self.effect_properties.generate_requested.connect(self.generate_effect)
        self.effect_properties.reset_requested.connect(self.reset_generator_settings)
        self.effect_properties.draft_changed.connect(self.update_generator_draft)
        self.effect_properties.refresh_preview_requested.connect(
            self.refresh_generator_preview
        )
        self.effect_properties.revert_requested.connect(self.revert_generator_draft)
        self.effect_properties.auto_preview_changed.connect(
            self.preview_manager.set_auto_preview
        )
        self.effect_properties.gizmo_mode_changed.connect(self._set_gizmo_mode)
        self.canvas.gizmo_changed.connect(self._gizmo_changed)
        self.canvas.effect_guide_changed.connect(self._effect_guide_changed)
        self.canvas.effect_guide_started.connect(self._effect_guide_started)
        self.canvas.effect_guide_cancelled.connect(self._effect_guide_cancelled)
        self.canvas.resource_transform_changed.connect(self._resource_transform_gizmo_changed)
        self.canvas.resource_transform_cancelled.connect(self._resource_transform_gizmo_cancelled)
        self.canvas.resource_transform_started.connect(self._prepare_resource_transform_interaction)
        self.canvas.layer_selected.connect(lambda index:self.select_cell(index,self.frame_index))
        self.preview_manager.state_changed.connect(self._preview_state_changed)
        self.preview_manager.preview_ready.connect(self._preview_ready)
        self.preview_manager.preview_failed.connect(self._preview_failed)
        self.particle_properties.draft_changed.connect(self.update_particle_draft)
        self.particle_properties.refresh_requested.connect(self.refresh_particle_preview)
        self.particle_properties.bake_requested.connect(self.bake_particle_emitter)
        self.particle_properties.revert_requested.connect(self.revert_particle_draft)
        self.particle_properties.export_requested.connect(self.export_particle_preview)
        self.composition_layer_properties.changed.connect(self.update_composition_layer)
        self.composition_layer_properties.mode_changed.connect(self.set_resource_layer_mode)
        self.composition_layer_properties.resource_changed.connect(self.set_resource_layer_resource)
        self.particle_properties.mode_changed.connect(self.set_resource_layer_mode)
        self.particle_properties.motion_keyframe_requested.connect(self.add_particle_motion_keyframe)
        for panel in (self.composition_layer_properties,self.particle_properties):
            panel.transform_changed.connect(self.update_resource_layer_transform)
            panel.transform_panel.interactive_transform_changed.connect(self.update_resource_layer_transform_property)
            panel.transform_panel.transform_edit_finished.connect(self.finalize_resource_layer_transform)
            panel.transform_keyframe_requested.connect(self.add_resource_layer_transform_keyframe)
            panel.transform_gizmo_changed.connect(self._set_resource_transform_gizmo)
            panel.transform_panel.surface_transform_changed.connect(self.update_resource_surface_transform)
        self.particle_preview_manager.preview_ready.connect(self._particle_preview_ready)
        self.particle_preview_manager.preview_failed.connect(self._particle_preview_failed)
        self.resource_editor.import_requested.connect(self.import_resources)
        self.resource_editor.pivot_changed.connect(self.update_resource_pivot)
        self.resource_editor.create_emitter_requested.connect(self.create_particle_from_resource)
        self.resource_editor.add_to_effect_requested.connect(self._resource_add_to_effect)
        self.resource_editor.reimport_requested.connect(self.reimport_resource)
        self.resource_editor.delete_requested.connect(self.delete_resource)
        self.resource_editor.composition_changed.connect(self.resource_composition_changed)

    def _refresh_all(self) -> None:
        self.frame_index = max(0, min(self.frame_index, self._display_frame_count() - 1))
        self.layer_index = max(0, min(self.layer_index, len(self.project.layers) - 1))
        self.canvas.set_project(self.project)
        self.canvas.set_frame(self.frame_index)
        self.canvas.set_layer(self.layer_index)
        self.timeline.refresh(
            self.project,
            self.layer_index,
            self.frame_index,
            display_frame_count=self._display_frame_count(),
            preview=self.active_preview_generator_id is not None,
        )
        self.timeline.set_playing(self.play_timer.isActive())
        deletable = self._selected_layer_is_deletable()
        self.timeline.set_delete_layer_enabled(deletable)
        self.delete_layer_action.setEnabled(deletable)
        apply_tooltip(
            self.delete_layer_action,
            self.localization,
            "tooltip.main.delete_layer" if deletable else "tooltip.main.select_layer_to_delete",
        )
        self._refresh_playback_status()
        self._refresh_effect_panels()
        self._update_title()
        self._refresh_selection_status()

    def _display_frame_count(self) -> int:
        if self.active_preview_generator_id and self.canvas.preview_frames is not None:
            return len(self.canvas.preview_frames)
        if self.active_preview_generator_id:
            session = self.preview_manager.current_session(
                self.active_preview_generator_id
            )
            if session is not None:
                return session.output_frame_count
        return len(self.project.frames)

    def _refresh_selection_status(self) -> None:
        self.statusBar().showMessage(
            f"{self.project.layers[self.layer_index].name} · "
            f"Frame {self.frame_index + 1}"
        )

    def _update_title(self) -> None:
        marker = "*" if self.dirty else ""
        self.setWindowTitle(f"{get_display_name()} - {self.project.name}{marker}")

    def _mark_dirty(self) -> None:
        if hasattr(self,"effect_playback"):self._invalidate_playback_cache(stop=True)
        self._project_edit_revision+=1
        self._non_undo_dirty=True
        self.dirty = True
        self._update_title()

    @Slot(int)
    def _undo_index_changed(self, index: int) -> None:
        if hasattr(self,"effect_playback"):self._invalidate_playback_cache(stop=True)
        self._project_edit_revision+=1
        self.dirty = self._non_undo_dirty or not self.application_undo_stack.isClean()
        self._update_title()
        self._refresh_undo_action_texts()
        if hasattr(self,"interactive_proxy_prewarm"):self._schedule_resource_transform_prewarm()

    def _refresh_undo_action_texts(self) -> None:
        t=self.localization.text
        self.undo_action.setText(t("action.undo") if not self.application_undo_stack.undoText() else t("action.undo_named").format(name=self.application_undo_stack.undoText()))
        self.redo_action.setText(t("action.redo") if not self.application_undo_stack.redoText() else t("action.redo_named").format(name=self.application_undo_stack.redoText()))

    def apply_undo_value(self,target_id,field,value) -> None:
        if field=="effect_visibility":
            layer=next((item for item in self.project.layers if item.id==target_id),None)
            if layer:
                layer.visible=bool(value)
                resource=next((item for item in self.project.effect_resource_layers if item.generated_layer_id==target_id),None)
                if resource:resource.visible=bool(value)
                self.canvas.update();self.timeline.refresh(self.project,self.layer_index,self.frame_index,display_frame_count=self._display_frame_count(),preview=self.active_preview_generator_id is not None)
                self._schedule_resource_transform_prewarm()
        elif field=="particle_settings":
            emitter=next((item for item in self.project.particle_emitters if item.id==target_id),None)
            if emitter:
                self.particle_preview_manager.update(self.project,emitter,value);self.particle_properties.set_settings(value)
                if self.particle_properties.emitter_id==target_id:self.canvas.set_effect_guide(target_id,"particle_system",value)
        elif field=="composition_layer_settings":
            layer=next((item for item in self.project.effect_composition_layers if item.id==target_id),None)
            if layer:
                layer.__dict__.update(deepcopy(value).__dict__)
                outputs=render_effect_composition_layer(self.project,layer);generated=apply_effect_composition_layer(self.project,layer,outputs)
                self.composition_layer_properties.set_layer(layer,self.project)
                self.canvas.set_effect_guide(layer.id,"composition_layer",layer)
                self.layer_index=self.project.layers.index(generated);self._refresh_all()
        elif field=="resource_layer_settings":
            current=next((item for item in self.project.effect_resource_layers if item.id==target_id),None)
            if current:
                motion_only=self._is_particle_motion_only_change(current,value)
                if motion_only:
                    current.__dict__.update(deepcopy(value).__dict__);invalidate_effect_resource_layer_base(current.id);self._sync_resource_layer_adapters()
                    draft=self.particle_preview_manager.ensure_draft(current.as_particle_emitter());draft.settings=deepcopy(current.particle_settings);draft.revision+=1;draft.is_dirty=False;self.particle_preview_manager.sessions.pop(current.id,None)
                    if self.particle_properties.emitter_id==current.id:self.particle_properties.set_resource_layer(current,self.project);self.canvas.set_effect_guide(current.id,"particle_system",current.particle_settings)
                    self._queue_particle_motion_render(current);return
                self.canvas.clear_interactive_transform_proxy(update=False);self.canvas.proxy_base_image_cache.clear(current.id)
                current.__dict__.update(deepcopy(value).__dict__)
                invalidate_effect_resource_layer_base(current.id)
                generated=apply_effect_resource_layer(self.project,current)
                self._dirty_particle_motion_layers.discard(current.id)
                self._dirty_resource_transform_layers.discard(current.id)
                self._sync_resource_layer_adapters()
                if current.placement_mode==PLACEMENT_PARTICLE:self.particle_preview_manager.revert(current.as_particle_emitter())
                self.layer_index=self.project.layers.index(generated)
                self._refresh_all();self.select_resource_layer(current.id)
        elif field=="resource_layer_interaction":
            current=next((item for item in self.project.effect_resource_layers if item.id==target_id),None)
            if current:
                current.__dict__.update(deepcopy(value).__dict__);invalidate_effect_resource_layer_base(current.id);self._sync_resource_layer_adapters()
                if current.placement_mode==PLACEMENT_PARTICLE:
                    draft=self.particle_preview_manager.ensure_draft(current.as_particle_emitter());draft.settings=deepcopy(current.particle_settings);draft.revision+=1;draft.is_dirty=False;self.particle_preview_manager.sessions.pop(current.id,None)
                self._queue_particle_motion_render(current,final=True)
        elif field.startswith("resource_layer_transform"):
            current=next((item for item in self.project.effect_resource_layers if item.id==target_id),None)
            if current:
                current.layer_transform=deepcopy(value);self._queue_resource_transform_render(current)
                self._sync_resource_layer_adapters()
                self.project._current_effect_frame=self.frame_index
                panel=self.particle_properties.transform_panel if current.placement_mode==PLACEMENT_PARTICLE else self.composition_layer_properties.transform_panel
                property_id=field.partition(":")[2]
                if property_id:panel.set_transform_fields(current,self.frame_index,(property_id,))
                else:panel.set_layer(current,self.frame_index)
        elif field=="resource_surface_transform":
            current=next((item for item in self.project.effect_resource_layers if item.id==target_id),None)
            if current:
                current.surface_transform=deepcopy(value);invalidate_effect_resource_layer_base(current.id);apply_effect_resource_layer_current_frame(self.project,current,self.frame_index);self._sync_resource_layer_adapters();self._refresh_all();self.select_resource_layer(current.id)

    def _queue_resource_transform_render(self,layer) -> None:
        if self.active_preview_generator_id==layer.id:self._clear_preview()
        self._pending_resource_transforms[layer.id]=int(layer.layer_transform.revision)
        self._dirty_resource_transform_layers.add(layer.id)
        if self.canvas.resource_transform_id==layer.id:
            state=self.canvas.interactive_transform_proxy
            if state is not None and not state.active:self.canvas.activate_proxy_prewarm(layer,effect_resource_layer_base_frame_key(self.project,layer,self.frame_index));state=self.canvas.interactive_transform_proxy
            if state is not None and state.resource_layer_id==layer.id and state.frame==self.frame_index:state.queue(layer.layer_transform)
            else:
                base_key=effect_resource_layer_base_frame_key(self.project,layer,self.frame_index);self.interactive_proxy_prewarm.schedule(self.canvas.proxy_prewarm_token(layer,base_key),0)
        if not self.resource_transform_render_timer.isActive():self.resource_transform_render_timer.start(33)
        self.resource_transform_finalize_timer.start(120)

    @staticmethod
    def _is_particle_motion_only_change(before,after) -> bool:
        if before.placement_mode!=PLACEMENT_PARTICLE or after.placement_mode!=PLACEMENT_PARTICLE:return False
        left=before.to_dict();right=after.to_dict();left_settings=left.pop("particle_settings");right_settings=right.pop("particle_settings")
        left_settings.pop("motion",None);right_settings.pop("motion",None)
        return left==right and left_settings==right_settings and before.particle_settings.motion!=after.particle_settings.motion

    def _queue_particle_motion_render(self,layer,final=False) -> None:
        revision=int(layer.particle_settings.motion.revision);self._pending_particle_motion[layer.id]=(revision,int(self.frame_index));self._pending_particle_motion_layers[layer.id]=deepcopy(layer)
        if any(item is layer for item in self.project.effect_resource_layers):self._dirty_particle_motion_layers.add(layer.id)
        if final:self._flush_particle_motion_final();return
        if not self.particle_motion_render_timer.isActive():self.particle_motion_render_timer.start(33)
        self.particle_motion_finalize_timer.start(120)

    def _flush_particle_motion_current(self) -> None:
        for identifier,(revision,frame) in dict(self._pending_particle_motion).items():
            layer=self._pending_particle_motion_layers.get(identifier)
            if layer is None or layer.particle_settings.motion.revision!=revision:continue
            self.interactive_gizmo_renderer.schedule(self.project,layer,frame,immediate=True,purpose="motion")

    def _flush_particle_motion_final(self) -> None:
        if self.canvas._guide_handle:
            self.particle_motion_finalize_timer.start(120);return
        self.particle_motion_render_timer.stop();self.particle_motion_finalize_timer.stop()
        pending=dict(self._pending_particle_motion);layers=dict(self._pending_particle_motion_layers);self._pending_particle_motion.clear();self._pending_particle_motion_layers.clear()
        for identifier,(revision,frame) in pending.items():
            layer=layers.get(identifier) or next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
            if layer is None or layer.particle_settings.motion.revision!=revision:continue
            self.interactive_gizmo_renderer.schedule(self.project,layer,frame,final=True,purpose="motion")
        if pending:self._schedule_resource_transform_prewarm()

    def _interactive_gizmo_frame_ready(self,result) -> None:
        request=result.request
        if request.project_identity!=id(self.project) or request.frame!=self.frame_index:return
        layer=request.layer;actual=next((item for item in self.project.effect_resource_layers if item.id==layer.id),None)
        if actual is None:return
        if request.final:
            generated=next((item for item in self.project.layers if item.id==actual.generated_layer_id),None)
            if generated is not None and 0<=request.frame<len(self.project.frames):
                self.project.frames[request.frame].layer_pixels[generated.id]=result.exact_rgba.copy();self.layer_index=self.project.layers.index(generated)
            self.interactive_gizmo_renderer.collector.final_exact_installs+=1
            if request.purpose=="layer_transform":self.canvas.finish_interactive_transform_proxy(layer.id,actual.layer_space_transform)
            else:self.canvas.finish_interactive_motion_proxy(layer.id)
            self._schedule_resource_transform_prewarm();return
        revision=layer.layer_space_transform.revision if request.purpose=="layer_transform" else layer.particle_settings.motion.revision
        installed=self.canvas.apply_interactive_motion_proxy(layer,result.exact_rgba,(*result.base_key,request.revision),revision,already_transformed=True)
        if installed:self._pending_interactive_gizmo_results.pop(layer.id,None)
        else:self._pending_interactive_gizmo_results[layer.id]=result

    def _render_dirty_particle_motion_frame(self,frame: int) -> None:
        """Install exact particle pixels for paused arbitrary frame access.

        Persisted generated buffers are only a bake/cache artifact.  Metadata-only
        saves intentionally do not materialize a sequence, so session-local dirty
        flags cannot decide whether a paused Timeline frame is authoritative.
        """
        if self.active_preview_generator_id is not None:return
        for layer in self.project.effect_resource_layers:
            if layer.placement_mode==PLACEMENT_PARTICLE:apply_effect_resource_layer_current_frame(self.project,layer,frame)

    def _flush_resource_transform_current(self) -> None:
        pending=dict(self._pending_resource_transforms)
        for identifier,revision in pending.items():
            layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
            if layer is None or layer.layer_transform.revision!=revision:continue
            if layer.placement_mode==PLACEMENT_PARTICLE:
                self.interactive_gizmo_renderer.schedule(self.project,layer,self.frame_index,immediate=True,purpose="layer_transform")
            else:self.canvas.apply_interactive_transform_proxy(layer)

    def _flush_resource_transform_final(self) -> None:
        self.resource_transform_render_timer.stop();pending=dict(self._pending_resource_transforms);self._pending_resource_transforms.clear()
        for identifier,revision in pending.items():
            layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
            if layer is None or layer.layer_transform.revision!=revision:continue
            if layer.placement_mode==PLACEMENT_PARTICLE:
                self.interactive_gizmo_renderer.schedule(self.project,layer,self.frame_index,final=True,purpose="layer_transform")
            else:
                generated=apply_effect_resource_layer_current_frame(self.project,layer,self.frame_index)
                if generated in self.project.layers:self.layer_index=self.project.layers.index(generated)
                self.canvas.finish_interactive_transform_proxy(identifier,layer.layer_transform)
        if pending:self._schedule_resource_transform_prewarm()

    def _selected_resource_layer(self):
        identifier=self.canvas.resource_transform_id
        return next((item for item in self.project.effect_resource_layers if item.id==identifier),None)

    def _schedule_resource_transform_prewarm(self) -> None:
        if not hasattr(self,"interactive_proxy_prewarm"):return
        layer=self._selected_resource_layer()
        if layer is None or self.play_timer.isActive() or self._timeline_scrubbing or self.canvas.preview_frames is not None or self.canvas._resource_transform_drag or self.canvas._guide_handle:
            self.interactive_proxy_prewarm.cancel();return
        base_key=effect_resource_layer_base_frame_key(self.project,layer,self.frame_index)
        token=self.canvas.proxy_prewarm_token(layer,base_key)
        self.interactive_proxy_prewarm.schedule(token)

    def _build_resource_transform_prewarm_payload(self,token):
        if self.play_timer.isActive() or self._timeline_scrubbing:return None
        layer=next((item for item in self.project.effect_resource_layers if item.id==token.resource_layer_id),None)
        if layer is None:return None
        base_key=effect_resource_layer_base_frame_key(self.project,layer,self.frame_index)
        if self.canvas.proxy_prewarm_token(layer,base_key,token.request_revision)!=token:return None
        payload=self.canvas.proxy_prewarm_payload(token,None)
        for name,value in self.canvas.last_prewarm_payload_timings.items():self.interactive_proxy_prewarm.collector.record(name,value)
        return payload

    def _install_resource_transform_prewarm(self,result) -> None:
        token=result.token
        if token.request_revision!=self.interactive_proxy_prewarm.request_revision:return
        if not self.canvas.install_proxy_prewarm(result):self.interactive_proxy_prewarm.collector.stale_rejections+=1
        else:
            for name,value in self.canvas.last_prewarm_install_timings.items():self.interactive_proxy_prewarm.collector.record(name,value)
            layer=next((item for item in self.project.effect_resource_layers if item.id==token.resource_layer_id),None)
            if layer is not None and (self.canvas._resource_transform_drag or token.resource_layer_id in self._pending_resource_transforms) and layer.placement_mode!=PLACEMENT_PARTICLE:
                state=self.canvas.interactive_transform_proxy
                if layer is not None and state is not None:
                    state.active=True;state.queue(self.canvas.resource_transform if self.canvas._resource_transform_drag and self.canvas.resource_transform is not None else layer.layer_transform);self.canvas.apply_interactive_transform_proxy(layer)
            pending=self._pending_interactive_gizmo_results.get(token.resource_layer_id)
            if pending is not None and pending.request.revision==self.interactive_gizmo_renderer.revision and pending.request.frame==self.frame_index:
                request=pending.request;pending_layer=request.layer
                revision=pending_layer.layer_space_transform.revision if request.purpose=="layer_transform" else pending_layer.particle_settings.motion.revision
                if self.canvas.apply_interactive_motion_proxy(pending_layer,pending.exact_rgba,(*pending.base_key,request.revision),revision,already_transformed=True):self._pending_interactive_gizmo_results.pop(token.resource_layer_id,None)

    def _resource_timeline_scrub_started(self) -> None:
        self._timeline_scrubbing=True;self.interactive_proxy_prewarm.cancel();self.set_playing(False)

    def _resource_timeline_scrub_finished(self) -> None:
        self._timeline_scrubbing=False;self._schedule_resource_transform_prewarm()

    def _materialize_resource_transform_sequences(self) -> None:
        self.resource_transform_render_timer.stop();self.resource_transform_finalize_timer.stop();self.particle_motion_render_timer.stop();self.particle_motion_finalize_timer.stop()
        identifiers=set(self._dirty_resource_transform_layers)|set(self._dirty_particle_motion_layers)|set(self._pending_resource_transforms)|set(self._pending_particle_motion)
        self._pending_resource_transforms.clear();self._pending_particle_motion.clear();self._pending_particle_motion_layers.clear();self._dirty_resource_transform_layers.clear();self._dirty_particle_motion_layers.clear()
        self.interactive_gizmo_renderer.cancel();self.canvas.clear_interactive_transform_proxy(update=False)
        for identifier in identifiers:
            layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
            if layer is not None:apply_effect_resource_layer(self.project,layer)
        if identifiers:self._sync_resource_layer_adapters()

    def apply_undo_operation(self,operation,state,forward) -> None:
        if operation in {"delete_layer","delete_effect_layer","add_resource_layer"}:
            self.interactive_proxy_prewarm.cancel();self.canvas.clear_interactive_transform_proxy(update=False)
        if operation in {"add_frame","duplicate_frame"}:
            index=state["index"]+1
            if forward:
                if "frame" not in state:state["frame"]=self.project.insert_empty_frame(state["index"]) if operation=="add_frame" else self.project.duplicate_frame(state["index"])
                else:self.project.frames.insert(index,state["frame"])
                self.frame_index=index
            else:self.project.frames.pop(index);self.frame_index=state["index"]
        elif operation=="delete_frame":
            index=state["index"]
            if forward:self.project.frames.pop(index);self.frame_index=min(index,len(self.project.frames)-1)
            else:self.project.frames.insert(index,state["frame"]);self.frame_index=index
        elif operation=="add_layer":
            if forward:
                if "layer" not in state:state["layer"]=self.project.add_layer(state["name"])
                else:
                    self.project.layers.append(state["layer"])
                    for frame in self.project.frames:frame.layer_pixels[state["layer"].id]=empty_pixels(self.project.width,self.project.height)
                self.layer_index=len(self.project.layers)-1
            else:self.project.delete_layer(len(self.project.layers)-1);self.layer_index=max(0,len(self.project.layers)-1)
        elif operation=="delete_layer":
            index=state["index"]
            if forward:self.project.delete_layer(index);self.layer_index=min(index,len(self.project.layers)-1)
            else:
                self.project.layers.insert(index,state["layer"])
                for frame,pixels in zip(self.project.frames,state["pixels"]):frame.layer_pixels[state["layer"].id]=pixels
                self.layer_index=index
        elif operation=="delete_effect_layer":
            self._apply_effect_layer_delete(state, forward)
        elif operation=="add_resource_layer":
            resource=state["resource_layer"];generated=state["generated_layer"]
            if forward:
                if state.pop("initial_redo",False):pass
                else:
                    self.project.effect_resource_layers.insert(min(state["resource_index"],len(self.project.effect_resource_layers)),resource)
                    self.project.layers.insert(min(state["layer_index"],len(self.project.layers)),generated)
                    for frame,pixels in zip(self.project.frames,state["pixels"]):frame.layer_pixels[generated.id]=pixels
                self._sync_resource_layer_adapters();self.layer_index=self.project.layers.index(generated)
            else:
                if resource in self.project.effect_resource_layers:self.project.effect_resource_layers.remove(resource)
                if generated in self.project.layers:self.project.layers.remove(generated)
                for frame in self.project.frames:frame.layer_pixels.pop(generated.id,None)
                self._sync_resource_layer_adapters();self.layer_index=max(0,min(state["layer_index"]-1,len(self.project.layers)-1))
        self._refresh_all()
        if operation == "delete_effect_layer":
            model_info = state.get("model_info")
            if forward or not model_info:
                self.composition_layer_properties.set_layer(None, self.project)
                self.particle_properties.set_emitter(None, self.project)
            elif model_info["kind"] == "resource_layer":
                self.select_resource_layer(model_info["model"].id)
            elif model_info["kind"] == "composition_layer":
                self.select_effect_composition_layer(model_info["model"].id)
            elif model_info["kind"] == "particle_system":
                self.select_particle_emitter(model_info["model"].id)
            else:
                self.select_generator(model_info["model"].id)
        elif operation=="add_resource_layer":
            if forward:self.select_resource_layer(state["resource_layer"].id)
            else:
                self.canvas.set_effect_guide(None);self.composition_layer_properties.set_resource_layer(None,self.project);self.particle_properties.set_resource_layer(None,self.project)

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self,
            self.localization.text("message.unsaved_title"),
            self.localization.text("message.discard_unsaved"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if not self._confirm_unapplied_previews() or not self._confirm_discard():
            return
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        settings = dialog.settings()
        self.apply_new_project_settings(settings)
        self.statusBar().showMessage(self.localization.text("status.new_project"), 3000)

    def apply_new_project_settings(self, settings) -> None:
        runtime_logger().info(
            "new_project start size=%sx%s frames=%s fps=%s loop=%s",
            settings.width,settings.height,settings.frame_count,settings.fps,settings.loop,
        )
        self.interactive_proxy_prewarm.cancel()
        self.interactive_gizmo_renderer.cancel()
        self._invalidate_playback_cache(stop=True)
        invalidate_composition_cache()
        invalidate_effect_resource_layer_base()
        invalidate_particle_render_caches()
        self.canvas.proxy_composite_cache.clear()
        self.canvas.proxy_base_image_cache.clear()
        self.set_playing(False)
        self.preview_manager.reset_context()
        self.particle_preview_manager.reset_context()
        self._clear_preview()
        self.project = Project.create_default(
            settings.name,
            settings.width,
            settings.height,
            settings.fps,
            settings.loop,
            settings.frame_count,
        )
        self.project_path = None
        self.application_undo_stack.clear()
        self.frame_index = self.layer_index = 0
        self.dirty = False
        self._non_undo_dirty=False
        self.set_workspace("effect")
        self._refresh_all()
        runtime_logger().info("new_project success")

    def open_project(self) -> None:
        if not self._confirm_unapplied_previews() or not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "projects", "Pixel Effect Project (*.peffect.json)"
        )
        if not path:
            return
        runtime_logger().info("open_project start source=%s", safe_path_label(path))
        self.interactive_proxy_prewarm.cancel()
        self.interactive_gizmo_renderer.cancel()
        self._invalidate_playback_cache(stop=True)
        invalidate_composition_cache()
        invalidate_effect_resource_layer_base()
        invalidate_particle_render_caches()
        self.canvas.proxy_composite_cache.clear()
        self.canvas.proxy_base_image_cache.clear()
        try:
            loaded_project = load_project(path)
        except ProjectIOError as exc:
            log_exception("open_project", exc)
            key={
                "load_payload":"error.load_payload",
                "load_future_format":"error.load_future_format",
            }.get(exc.code,"error.load_failed_body")
            QMessageBox.critical(self,self.localization.text("error.open"),self.localization.text(key).format(reason=str(exc)))
            return
        self.project = loaded_project
        self.set_playing(False)
        self.preview_manager.reset_context()
        self.particle_preview_manager.reset_context()
        self._clear_preview()
        self.project_path = Path(path)
        self.application_undo_stack.clear()
        self.frame_index = self.layer_index = 0
        self.dirty = False
        self._non_undo_dirty=False
        self.application_undo_stack.setClean()
        self._refresh_all()
        saved_workspace=str(self.settings_service.settings.value("ui/workspace","effect"))
        self.set_workspace("resource" if saved_workspace=="resource" and (self.project.source_assets or self.project.animation_clips) else "effect")
        self.statusBar().showMessage(self.localization.text("status.opened").format(path=path), 4000)
        runtime_logger().info("open_project success source=%s", safe_path_label(path))

    def save(self) -> bool:
        if self.project_path is None:
            return self.save_as()
        return self._save_to_path(self.project_path)

    def _save_to_path(self,target: Path) -> bool:
        if self._save_in_progress:
            self.statusBar().showMessage(self.localization.text("status.save_in_progress"),3000);return False
        runtime_logger().info("save_project start target=%s",safe_path_label(target))
        self._save_in_progress=True;self.save_action.setEnabled(False);self.save_as_action.setEnabled(False)
        try:
            # Project Save persists the editable Resource Layer metadata.  It
            # must not materialize dirty preview/output sequences; exact
            # materialization remains an explicit playback/export/bake concern.
            saved_revision=self._project_edit_revision
            saved_path=save_project(self.project,target)
        except ProjectIOError as exc:
            log_exception("save_project",exc)
            key={"save_directory":"error.save_directory","save_serialize":"error.save_serialize","save_temporary":"error.save_temporary","save_replace":"error.save_replace"}.get(exc.code,"error.save_failed_body")
            QMessageBox.critical(self,self.localization.text("error.save"),self.localization.text(key).format(reason=str(exc)))
            return False
        finally:
            self._save_in_progress=False;self.save_action.setEnabled(True);self.save_as_action.setEnabled(True)
        self.project_path=saved_path
        if self._project_edit_revision==saved_revision:
            self.dirty=False;self._non_undo_dirty=False;self.application_undo_stack.setClean()
        self._update_title()
        self.statusBar().showMessage(self.localization.text("status.saved").format(path=self.project_path), 4000)
        if self.preview_manager.dirty_generator_ids():
            self.statusBar().showMessage(
                self.localization.text("message.saved_without_preview"), 5000
            )
        runtime_logger().info("save_project success target=%s",safe_path_label(saved_path))
        return True

    def save_as(self) -> bool:
        runtime_logger().info("save_as start")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            str(Path("projects") / f"{self.project.name}.peffect.json"),
            "Pixel Effect Project (*.peffect.json)",
        )
        if not path:
            runtime_logger().info("save_as cancelled")
            return False
        saved=self._save_to_path(Path(path))
        runtime_logger().info("save_as result=%s", "success" if saved else "failed")
        return saved

    def export_frames(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Export PNG Frames", str(Path("exports").resolve())
        )
        if not directory:
            return
        runtime_logger().info("export_png start destination_type=directory")
        self._materialize_resource_transform_sequences()
        if self.preview_manager.dirty_generator_ids():
            self.statusBar().showMessage(
                self.localization.text("message.export_without_preview"), 5000
            )
        try:
            written = export_png_frames(self.project, directory)
        except ExportError as exc:
            log_exception("export_png",exc)
            QMessageBox.critical(self, self.localization.text("error.export"), str(exc))
            return
        QMessageBox.information(
            self, "Export Complete", f"Exported {len(written)} PNG frame(s)."
        )
        runtime_logger().info("export_png success frames=%s",len(written))

    def set_layer_visibility(self, index: int, visible: bool) -> None:
        if not 0 <= index < len(self.project.layers): return
        layer=self.project.layers[index];self.application_undo_stack.push(EditorValueCommand(self,layer.id,"effect_visibility",layer.visible,bool(visible),"Layer Visibility"))

    def import_source_asset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Source Asset", "", "PNG Images (*.png)"
        )
        if path:
            self.import_source_asset_path(path)

    def show_external_tools(self) -> None:
        ExternalToolsDialog(self.settings_service.settings,self.localization,self).exec()

    def import_resources(self, paths=None) -> list:
        if isinstance(paths,bool) or paths is None:
            paths,_=QFileDialog.getOpenFileNames(self,self.localization.text("resource.import"),"","Resources (*.png *.gif *.ase *.aseprite)")
        if not paths:return []
        imported=[];failures=[]
        for value in paths:
            path=Path(value)
            runtime_logger().info("import_resource start source=%s",safe_path_label(path))
            try:
                if path.suffix.lower() in {".ase",".aseprite"}:
                    executable=locate_aseprite(self.settings_service.settings)
                    if executable is None:
                        dialog=ExternalToolsDialog(self.settings_service.settings,self.localization,self)
                        if dialog.exec()!=QDialog.DialogCode.Accepted:raise ResourceImportError("Aseprite executable was not configured")
                        executable=locate_aseprite(self.settings_service.settings)
                    if executable is None:raise ResourceImportError("Aseprite executable was not found")
                    resource=import_aseprite(path,executable)
                else:resource=import_resource(path)
                all_names={r.name for r in self.project.source_assets}|{r.name for r in self.project.animation_clips};base=resource.name;number=2
                while resource.name in all_names:resource.name=f"{Path(base).stem} ({number}){Path(base).suffix}";number+=1
                (self.project.source_assets if isinstance(resource,SourceAsset) else self.project.animation_clips).append(resource);imported.append(resource)
                runtime_logger().info("import_resource success source=%s kind=%s",safe_path_label(path),type(resource).__name__)
            except (ResourceImportError,OSError,ValueError) as exc:
                log_exception("import_resource",exc);failures.append(f"{path.name}: {exc}")
        if imported:
            self._mark_dirty();first=imported[0];kind="source_asset" if isinstance(first,SourceAsset) else "animation_clip";self.resource_editor.refresh(self.project,(kind,first.id));self.set_workspace("resource");self._refresh_effect_panels()
        message=self.localization.text("resource.import_summary").format(success=len(imported),failed=len(failures));self.statusBar().showMessage(message,6000)
        if failures:QMessageBox.warning(self,self.localization.text("resource.import"),message+"\n"+"\n".join(failures))
        return imported

    def update_resource_pivot(self,kind: str,identifier: str,x: float,y: float) -> None:
        resources=self.project.source_assets if kind=="source_asset" else self.project.animation_clips;resource=next((r for r in resources if r.id==identifier),None)
        if resource is None:return
        resource.pivot_x=float(x);resource.pivot_y=float(y)
        for generator in self.project.generators:
            if kind=="source_asset" and generator.settings.source_asset_id==identifier:self.preview_manager.sessions.pop(generator.id,None)
        for emitter in self.project.particle_emitters:
            if emitter.settings.resource_type==kind and emitter.settings.resource_id==identifier:self.particle_preview_manager.sessions.pop(emitter.id,None)
        self._mark_dirty();self.statusBar().showMessage(self.localization.text("resource.preview_invalidated"),4000)

    def create_particle_from_resource(self,kind: str,identifier: str):
        if kind=="resource_composition":return self.create_resource_layer_from_resource(identifier,PLACEMENT_PARTICLE)
        if kind=="animation_clip":emitter=self.add_particle_emitter(identifier)
        else:
            source=next((r for r in self.project.source_assets if r.id==identifier),None)
            if source is None:return None
            emitter=ParticleEmitter(name=f"Resource Layer {len(self.project.effect_resource_layers)+1}",settings=ParticleEmitterSettings(identifier,resource_type="source_asset",origin_x=self.project.width/2,origin_y=self.project.height/2))
        if isinstance(emitter,EffectResourceLayer):return emitter
        if emitter:
            layer=EffectResourceLayer.from_particle_emitter(emitter);self.project.effect_resource_layers.append(layer);self._sync_resource_layer_adapters();self._mark_dirty();self.effect_library.refresh(self.project);self.set_workspace("effect");self.select_resource_layer(layer.id);return layer
        return None

    def _resource_add_to_effect(self, mode: str, kind: str, identifier: str) -> None:
        if kind=="resource_composition":self.create_resource_layer_from_resource(identifier)

    def _sync_resource_layer_adapters(self) -> None:
        self.project.effect_composition_layers=[item.as_composition_layer() for item in self.project.effect_resource_layers if item.placement_mode==PLACEMENT_SINGLE]
        self.project.particle_emitters=[item.as_particle_emitter() for item in self.project.effect_resource_layers if item.placement_mode==PLACEMENT_PARTICLE]
        self._update_resource_layer_display_names()

    def _update_resource_layer_display_names(self) -> None:
        for item in self.project.effect_resource_layers:
            generated=next((layer for layer in self.project.layers if layer.id==item.generated_layer_id),None)
            if generated is not None:
                mode_key="resource_layer.particle" if item.placement_mode==PLACEMENT_PARTICLE else "resource_layer.single"
                generated.name=f"{item.name} · {self.localization.text(mode_key)}"
        if hasattr(self,"timeline"):
            for row,layer in enumerate(reversed(self.project.layers)):
                item=self.timeline.table.item(row,self.timeline.NAME_COLUMN)
                if item is not None:item.setText(layer.name);item.setToolTip(layer.name)

    def create_resource_layer_from_resource(self, identifier: str, placement_mode: str = PLACEMENT_SINGLE):
        composition=next((item for item in self.project.resource_compositions if item.id==identifier),None)
        if composition is None:return None
        number=len(self.project.effect_resource_layers)+1
        layer=EffectResourceLayer(
            name=f"Resource Layer {number}",resource_composition_id=identifier,
            placement_mode=placement_mode,start_frame=0,end_frame=max(0,len(self.project.frames)-1),
        )
        layer.single_settings.start_x=layer.single_settings.end_x=self.project.width/2
        layer.single_settings.start_y=layer.single_settings.end_y=self.project.height/2
        layer.particle_settings.origin_x=self.project.width/2;layer.particle_settings.origin_y=self.project.height/2
        layer.particle_settings.line_end_x=self.project.width*.75;layer.particle_settings.line_end_y=self.project.height/2
        generated=apply_effect_resource_layer(self.project,layer)
        self.project.effect_resource_layers.append(layer);self._sync_resource_layer_adapters()
        self.layer_index=self.project.layers.index(generated);self.set_workspace("effect")
        state={"resource_layer":layer,"generated_layer":generated,"resource_index":len(self.project.effect_resource_layers)-1,"layer_index":self.layer_index,"pixels":[frame.layer_pixels[generated.id] for frame in self.project.frames],"initial_redo":True}
        self.application_undo_stack.push(EditorOperationCommand(self,"add_resource_layer",state,"Add Resource Layer"));self.select_resource_layer(layer.id)
        return layer

    def create_composition_layer_from_resource(self, identifier: str):
        return self.create_resource_layer_from_resource(identifier)

    def add_default_composition_layer(self) -> None:
        self.add_default_resource_layer()

    def add_default_resource_layer(self) -> None:
        if self.project.resource_compositions:
            compositions=self.project.resource_compositions
            if len(compositions)==1:self.create_resource_layer_from_resource(compositions[0].id);return
            names=[item.name for item in compositions];name,ok=QInputDialog.getItem(self,self.localization.text("resource_layer.add"),self.localization.text("resource_layer.title"),names,0,False)
            if ok:self.create_resource_layer_from_resource(compositions[names.index(name)].id)
        else:QMessageBox.information(self,self.localization.text("resource_layer.title"),self.localization.text("effect.resource_required"))

    def add_default_particle_system(self) -> None:
        if self.project.resource_compositions:self.create_particle_from_resource("resource_composition",self.project.resource_compositions[0].id)
        elif self.project.animation_clips:self.add_particle_emitter(self.project.animation_clips[0].id)
        else:QMessageBox.information(self,self.localization.text("effect.particle_system"),self.localization.text("effect.resource_required"))

    def resource_composition_changed(self,identifier: str) -> None:
        """Invalidate only previews that consume the edited composition."""
        if not self.resource_editor._applying_command:self._mark_dirty()
        for emitter in self.project.particle_emitters:
            if emitter.settings.resource_type=="resource_composition" and emitter.settings.resource_id==identifier:
                self.particle_preview_manager.sessions.pop(emitter.id,None)
        for layer in self.project.effect_composition_layers:
            if layer.resource_composition_id==identifier:
                apply_effect_composition_layer(self.project,layer,render_effect_composition_layer(self.project,layer))
        for layer in self.project.effect_resource_layers:
            if layer.resource_composition_id==identifier:apply_effect_resource_layer(self.project,layer)
        self._refresh_effect_panels()

    def reimport_resource(self,kind: str,identifier: str) -> bool:
        resources=self.project.source_assets if kind=="source_asset" else self.project.animation_clips;old=next((r for r in resources if r.id==identifier),None)
        if old is None:return False
        path=Path(old.source_path) if old.source_path else None
        if path is None or not path.exists():
            selected,_=QFileDialog.getOpenFileName(self,self.localization.text("resource.reimport"),"","Resources (*.png *.gif *.ase *.aseprite)")
            if not selected:return False
            path=Path(selected)
        try:
            if path.suffix.lower() in {".ase",".aseprite"}:
                executable=locate_aseprite(self.settings_service.settings)
                if executable is None:raise ResourceImportError("Aseprite executable was not found")
                new=import_aseprite(path,executable)
            else:new=import_resource(path)
            if (kind=="source_asset") != isinstance(new,SourceAsset):raise ResourceImportError("the selected file has a different resource type")
        except (ResourceImportError,OSError,ValueError) as exc:QMessageBox.warning(self,self.localization.text("resource.reimport"),str(exc));return False
        new.id=old.id;new.name=old.name;new.pivot_x=old.pivot_x;new.pivot_y=old.pivot_y;resources[resources.index(old)]=new
        for composition in self.project.resource_compositions:
            if any(layer.source_type==kind and layer.source_id==new.id for layer in composition.layers):composition.touch();invalidate_composition_cache(composition.id)
        self.update_resource_pivot(kind,new.id,new.pivot_x,new.pivot_y);self.resource_editor.refresh(self.project,(kind,new.id));return True

    def delete_resource(self,kind: str,identifier: str) -> bool:
        used=(kind=="source_asset" and any(g.settings.source_asset_id==identifier for g in self.project.generators)) or any(e.settings.resource_type==kind and e.settings.resource_id==identifier for e in self.project.particle_emitters)
        if used:QMessageBox.warning(self,self.localization.text("resource.delete"),self.localization.text("resource.in_use"));return False
        resources=self.project.source_assets if kind=="source_asset" else self.project.animation_clips;resource=next((r for r in resources if r.id==identifier),None)
        if resource is None:return False
        if QMessageBox.question(self,self.localization.text("resource.delete"),self.localization.text("resource.delete_confirm"))!=QMessageBox.StandardButton.Yes:return False
        resources.remove(resource);self._mark_dirty();self.resource_editor.resource=None;self.resource_editor.refresh(self.project);self._refresh_effect_panels();return True

    def import_source_asset_path(self, path: str | Path) -> SourceAsset | None:
        """Import and register one embedded source; exposed for UI-level tests."""
        runtime_logger().info("import_png start source=%s",safe_path_label(path))
        try:
            asset = import_source_asset(path)
        except SourceImportError as exc:
            log_exception("import_png",exc)
            QMessageBox.critical(self, self.localization.text("error.import"), str(exc))
            return None
        self.project.source_assets.append(asset)
        self._mark_dirty()
        self.effect_library.refresh(self.project)
        self.effect_library.select_asset(asset.id)
        self.select_source_asset(asset.id)
        self.statusBar().showMessage(self.localization.text("status.imported").format(name=asset.name), 4000)
        runtime_logger().info("import_png success source=%s",safe_path_label(path))
        return asset

    def add_transform_emitter(self) -> TransformEmitter | None:
        if not self.project.source_assets:
            QMessageBox.information(
                self, "Transform Emitter", "Import a Source Asset first."
            )
            return None
        asset_id = self.effect_library.current_asset_id()
        if asset_id not in {item.id for item in self.project.source_assets}:
            asset_id = self.project.source_assets[0].id
        number = 1
        names = {item.name for item in self.project.generators}
        while f"Transform Emitter {number}" in names:
            number += 1
        emitter = TransformEmitter(
            name=f"Transform Emitter {number}",
            settings=TransformEmitterSettings(
                source_asset_id=asset_id,
                origin_x=self.project.width / 2.0,
                origin_y=self.project.height / 2.0,
                line_end_x=self.project.width * 0.75,
                line_end_y=self.project.height / 2.0,
                radius=min(self.project.width, self.project.height) / 4.0,
            ),
        )
        self.project.generators.append(emitter)
        self._mark_dirty()
        self.effect_library.refresh(self.project)
        self.effect_library.select_generator(emitter.id)
        self.select_generator(emitter.id)
        return emitter

    def select_source_asset(self, asset_id: str) -> None:
        asset = next(
            (item for item in self.project.source_assets if item.id == asset_id), None
        )
        self.effect_library.show_asset(asset)
        self.canvas.set_effect_guide(None)
        self.effect_properties.set_generator(None, self.project)
        self.properties_stack.setCurrentWidget(self.effect_properties)

    def select_generator(self, generator_id: str) -> None:
        self.canvas.set_effect_guide(None)
        self.properties_stack.setCurrentWidget(self.effect_properties)
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        self.effect_properties.set_generator(generator, self.project)
        if generator is None:
            self._clear_preview()
            return
        draft = self.preview_manager.ensure_draft(generator)
        self.effect_properties.set_settings(draft.settings)
        self._set_gizmo_mode(self.effect_properties.current_gizmo_mode(), self.effect_properties.edit_end_check.isChecked())
        session = self.preview_manager.current_session(generator.id)
        if session is not None:
            self._activate_preview(generator, session.frames)
            self.effect_properties.set_preview_state("ready")
        else:
            self._clear_preview()
            self.effect_properties.set_preview_state(
                "settings_changed" if draft.is_dirty else "applied"
            )

    def create_animation_clip(self, generator_id: str):
        generator = next((g for g in self.project.generators if g.id == generator_id), None)
        if generator is None: return None
        try: clip = create_clip_from_generator(self.project, generator)
        except ValueError as exc:
            QMessageBox.information(self, self.localization.text("effects.create_clip"), str(exc)); return None
        self._mark_dirty(); self.effect_library.refresh(self.project); self.statusBar().showMessage(self.localization.text("status.created").format(name=clip.name), 4000); return clip

    def update_animation_clip(self, clip_id: str, generator_id: str) -> bool:
        clip=next((c for c in self.project.animation_clips if c.id==clip_id),None); generator=next((g for g in self.project.generators if g.id==generator_id),None)
        if clip is None or generator is None:return False
        try:update_clip_from_generator(self.project,clip,generator)
        except ValueError:return False
        for emitter in self.project.particle_emitters:
            if emitter.settings.clip_asset_id==clip.id:self.particle_preview_manager.sessions.pop(emitter.id,None)
        self._mark_dirty(); return True

    def select_animation_clip(self, clip_id: str) -> None:
        self._clear_preview(); self.canvas.set_gizmo(None); self.canvas.set_effect_guide(None); self.properties_stack.setCurrentWidget(self.effect_properties); self.effect_properties.set_generator(None,self.project)

    def select_effect_composition_layer(self, identifier: str) -> None:
        unified=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if unified is not None:self.select_resource_layer(identifier);return
        layer=next((item for item in self.project.effect_composition_layers if item.id==identifier),None)
        if layer is None:return
        self._clear_preview();self.canvas.set_gizmo(None);self.properties_stack.setCurrentWidget(self.composition_layer_properties)
        self.composition_layer_properties.set_layer(layer,self.project);self.canvas.set_effect_guide(layer.id,"composition_layer",layer)
        generated=next((item for item in self.project.layers if item.id==layer.generated_layer_id),None)
        if generated is not None:
            self.layer_index=self.project.layers.index(generated);self.canvas.set_layer(self.layer_index)

    def update_composition_layer(self, identifier: str, value: EffectCompositionLayer) -> None:
        unified=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if unified:
            after=deepcopy(unified);after.single_settings=deepcopy(value);after.start_frame=value.start_frame;after.end_frame=value.end_frame
            self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_settings",unified,after,"Resource Layer Settings",701));return
        layer=next((item for item in self.project.effect_composition_layers if item.id==identifier),None)
        if layer:self.application_undo_stack.push(EditorValueCommand(self,identifier,"composition_layer_settings",layer,value,"Composition Layer Path",701))

    def select_resource_layer(self, identifier: str) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        self._clear_preview();self.canvas.set_gizmo(None);self.project._current_effect_frame=self.frame_index
        if layer.placement_mode==PLACEMENT_PARTICLE:
            self.properties_stack.setCurrentWidget(self.particle_properties)
            self.particle_properties.set_resource_layer(layer,self.project)
            emitter=layer.as_particle_emitter();draft=self.particle_preview_manager.ensure_draft(emitter);self.particle_properties.set_settings(draft.settings)
            self.canvas.set_effect_guide(layer.id,"particle_system",draft.settings)
        else:
            self.properties_stack.setCurrentWidget(self.composition_layer_properties)
            self.composition_layer_properties.set_resource_layer(layer,self.project)
            self.canvas.set_effect_guide(layer.id,"composition_layer",layer.as_composition_layer())
        self.canvas.set_resource_layer_transform(layer.id,layer.layer_transform,mode=self.canvas.resource_transform_mode)
        generated=next((item for item in self.project.layers if item.id==layer.generated_layer_id),None)
        if generated is not None:self.layer_index=self.project.layers.index(generated);self.canvas.set_layer(self.layer_index)
        self._schedule_resource_transform_prewarm()

    def set_resource_layer_mode(self, identifier: str, mode: str) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None or mode==layer.placement_mode:return
        after=deepcopy(layer);after.set_placement_mode(mode)
        self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_settings",layer,after,"Placement Mode",702))

    def set_resource_layer_resource(self, identifier: str, resource_id: str) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None or layer.resource_composition_id==resource_id:return
        after=deepcopy(layer);after.resource_composition_id=resource_id;after.single_settings.resource_composition_id=resource_id
        after.particle_settings.resource_type="resource_composition";after.particle_settings.clip_asset_id=resource_id
        self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_settings",layer,after,"Resource Layer Resource",703))

    def update_resource_layer_transform(self,identifier,transform) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_transform",layer.layer_transform,transform,"Resource Layer 2.5D Transform",704))

    def update_resource_layer_transform_property(self,identifier,transform,property_id) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        self.application_undo_stack.push(EditorValueCommand(self,identifier,f"resource_layer_transform:{property_id}",layer.layer_transform,transform,"Resource Layer 2.5D Transform",704))

    def update_resource_surface_transform(self,identifier,transform) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_surface_transform",layer.surface_transform,transform,"Resource Layer Surface Transform",705))

    def finalize_resource_layer_transform(self,identifier=None) -> None:
        if identifier is not None and identifier not in self._pending_resource_transforms:return
        self.resource_transform_finalize_timer.stop();self._flush_resource_transform_final()

    def add_resource_layer_transform_keyframe(self,identifier,property_id,frame,value,easing) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        after=deepcopy(layer.layer_transform);after.set_keyframe(property_id,frame,value,easing)
        self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_transform",layer.layer_transform,after,"Add 2.5D Transform Keyframe"))

    def add_particle_motion_keyframe(self,identifier,property_id,value,easing) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None or layer.placement_mode!=PLACEMENT_PARTICLE:return
        before=deepcopy(layer);after=deepcopy(layer);after.particle_settings.motion.set_keyframe(property_id,self.frame_index,float(value),str(easing))
        self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_settings",before,after,"Add Particle Motion Keyframe"))

    def _set_resource_transform_gizmo(self,identifier,mode) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer:self.canvas.set_resource_layer_transform(identifier,layer.layer_transform,mode=mode)

    def _prepare_resource_transform_interaction(self,identifier) -> None:
        self._begin_effect_gizmo_interaction();self.interactive_proxy_prewarm.cancel()
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        base_key=effect_resource_layer_base_frame_key(self.project,layer,self.frame_index)
        if self.canvas.activate_proxy_prewarm(layer,base_key):
            self.canvas.apply_interactive_transform_proxy(layer);return
        token=self.canvas.proxy_prewarm_token(layer,base_key);self.interactive_proxy_prewarm.schedule(token,0)

    def _resource_transform_gizmo_changed(self,identifier,transform,final) -> None:
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        if not hasattr(self,"_resource_transform_before"):self._resource_transform_before={}
        self._resource_transform_before.setdefault(identifier,deepcopy(layer.layer_transform));transform=deepcopy(transform);transform.revision=max(transform.revision,layer.layer_transform.revision+1);self.project._current_effect_frame=self.frame_index
        panel=self.particle_properties.transform_panel if layer.placement_mode==PLACEMENT_PARTICLE else self.composition_layer_properties.transform_panel
        fields=self.canvas.resource_transform_changed_fields or tuple(panel.fields)
        self.canvas.resource_transform=deepcopy(transform);transient=deepcopy(layer);transient.layer_transform=deepcopy(transform)
        state=self.canvas.interactive_transform_proxy
        if layer.placement_mode==PLACEMENT_PARTICLE:
            self.interactive_gizmo_renderer.schedule(self.project,transient,self.frame_index,purpose="layer_transform")
        elif state is not None and state.active and state.resource_layer_id==identifier:
            state.queue(transform);self.canvas.apply_interactive_transform_proxy(transient)
        self._pending_transform_inspector=(panel,transient,self.frame_index,fields)
        if not self.transform_inspector_timer.isActive():self.transform_inspector_timer.start(33)
        if final:
            self.transform_inspector_timer.stop();before=self._resource_transform_before.pop(identifier);self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_transform",before,transform,"2.5D Transform Gizmo"));self.canvas.apply_interactive_transform_proxy(layer);self.finalize_resource_layer_transform(identifier);panel.set_layer(layer,self.frame_index);self._pending_transform_inspector=None

    def _resource_transform_gizmo_cancelled(self,identifier,transform) -> None:
        self.transform_inspector_timer.stop();self._pending_transform_inspector=None;before=getattr(self,"_resource_transform_before",{}).pop(identifier,transform);layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        self.interactive_gizmo_renderer.cancel();self.interactive_proxy_prewarm.cancel();self.canvas.clear_interactive_transform_proxy(update=True)
        if layer is not None:
            self.canvas.set_resource_layer_transform(identifier,before,mode=self.canvas.resource_transform_mode);panel=self.particle_properties.transform_panel if layer.placement_mode==PLACEMENT_PARTICLE else self.composition_layer_properties.transform_panel;panel.set_layer(layer,self.frame_index)

    def _flush_transform_inspector_sync(self):
        pending=self._pending_transform_inspector;self._pending_transform_inspector=None
        if pending is None:return
        started=perf_counter();panel,layer,frame,fields=pending;panel.set_transform_fields(layer,frame,fields);self.interactive_gizmo_renderer.collector.record("inspector_sync",(perf_counter()-started)*1000.0)

    def _begin_effect_gizmo_interaction(self):
        self._invalidate_playback_cache(stop=True);self.interactive_proxy_prewarm.cancel();self.interactive_gizmo_renderer.cancel();self._pending_interactive_gizmo_results.clear()

    def _effect_guide_started(self,identifier):
        self._begin_effect_gizmo_interaction()
        layer=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if layer is None:return
        base_key=effect_resource_layer_base_frame_key(self.project,layer,self.frame_index)
        if self.canvas.activate_proxy_prewarm(layer,base_key):return
        token=self.canvas.proxy_prewarm_token(layer,base_key);self.interactive_proxy_prewarm.schedule(token,0)

    def open_resource_editor(self,kind: str,identifier: str) -> None:
        self.set_workspace("resource");self.resource_editor.select_resource(kind,identifier)

    def add_particle_emitter(self, clip_id: str):
        clip=next((c for c in self.project.animation_clips if c.id==clip_id),None)
        if clip is None:return None
        emitter=ParticleEmitter(name=f"Resource Layer {len(self.project.effect_resource_layers)+1}",settings=ParticleEmitterSettings(clip_asset_id=clip.id,origin_x=self.project.width/2,origin_y=self.project.height/2,line_end_x=self.project.width*.75,line_end_y=self.project.height/2,radius=min(self.project.width,self.project.height)/4))
        layer=EffectResourceLayer.from_particle_emitter(emitter);self.project.effect_resource_layers.append(layer);self._sync_resource_layer_adapters();self._mark_dirty();self.effect_library.refresh(self.project);self.set_workspace("effect");self.select_resource_layer(layer.id);return layer

    def select_particle_emitter(self, emitter_id: str) -> None:
        unified=next((item for item in self.project.effect_resource_layers if item.id==emitter_id),None)
        if unified is not None:self.select_resource_layer(emitter_id);return
        emitter=next((e for e in self.project.particle_emitters if e.id==emitter_id),None); self.canvas.set_gizmo(None); self.properties_stack.setCurrentWidget(self.particle_properties); self.particle_properties.set_emitter(emitter,self.project)
        if emitter is None:return
        draft=self.particle_preview_manager.ensure_draft(emitter); self.particle_properties.set_settings(draft.settings)
        self.canvas.set_effect_guide(emitter.id,"particle_system",draft.settings)
        session=self.particle_preview_manager.sessions.get(emitter.id)
        if session:self._activate_particle_preview(emitter,session.frames)
        else:self._clear_preview()

    def update_particle_draft(self, emitter_id: str, settings: ParticleEmitterSettings) -> None:
        unified=next((item for item in self.project.effect_resource_layers if item.id==emitter_id),None)
        if unified:
            after=deepcopy(unified);after.particle_settings=deepcopy(settings)
            if settings.resource_type=="resource_composition":after.resource_composition_id=settings.resource_id;after.single_settings.resource_composition_id=settings.resource_id
            self.application_undo_stack.push(EditorValueCommand(self,emitter_id,"resource_layer_settings",unified,after,"Resource Layer Particle Settings",700));return
        emitter=next((e for e in self.project.particle_emitters if e.id==emitter_id),None)
        if emitter:
            draft=self.particle_preview_manager.ensure_draft(emitter);before=draft.settings
            self.application_undo_stack.push(EditorValueCommand(self,emitter_id,"particle_settings",before,settings,"Particle Settings",700))

    def _effect_guide_changed(self, identifier: str, settings, final: bool) -> None:
        unified=next((item for item in self.project.effect_resource_layers if item.id==identifier),None)
        if unified is not None:
            if self._effect_guide_before is None:self._effect_guide_before=deepcopy(unified)
            transient=deepcopy(unified)
            if isinstance(settings,EffectCompositionLayer):transient.single_settings=deepcopy(settings);transient.start_frame=settings.start_frame;transient.end_frame=settings.end_frame
            else:transient.particle_settings=deepcopy(settings)
            self._pending_guide_inspector=(transient,deepcopy(settings));self._queue_particle_motion_render(transient,final=False)
            if not self.guide_inspector_timer.isActive():self.guide_inspector_timer.start(33)
            if final:
                self.particle_motion_render_timer.stop();self.guide_inspector_timer.stop();self._pending_guide_inspector=None;before=self._effect_guide_before;self._effect_guide_before=None
                self.application_undo_stack.push(EditorValueCommand(self,identifier,"resource_layer_interaction",before,transient,"Resource Layer Content Guide"));self._sync_guide_inspector(transient,settings)
            return
        if self._effect_guide_before is None:
            if isinstance(settings,EffectCompositionLayer):
                current=next((item for item in self.project.effect_composition_layers if item.id==identifier),None)
                self._effect_guide_before=deepcopy(current)
            else:
                emitter=next((item for item in self.project.particle_emitters if item.id==identifier),None)
                draft=None if emitter is None else self.particle_preview_manager.ensure_draft(emitter)
                self._effect_guide_before=None if draft is None else deepcopy(draft.settings)
        if isinstance(settings,EffectCompositionLayer):
            layer=next((item for item in self.project.effect_composition_layers if item.id==identifier),None)
            if layer:
                layer.__dict__.update(deepcopy(settings).__dict__)
                apply_effect_composition_layer(self.project,layer,render_effect_composition_layer(self.project,layer))
                self.composition_layer_properties.set_layer(layer,self.project)
        else:
            emitter=next((item for item in self.project.particle_emitters if item.id==identifier),None)
            if emitter:
                draft=self.particle_preview_manager.ensure_draft(emitter);draft.settings=deepcopy(settings)
                self.particle_properties.set_settings(settings)
        if final and self._effect_guide_before is not None:
            before=self._effect_guide_before;self._effect_guide_before=None
            field="composition_layer_settings" if isinstance(settings,EffectCompositionLayer) else "particle_settings"
            self.application_undo_stack.push(EditorValueCommand(self,identifier,field,before,settings,"Effect Guide"))

    def _effect_guide_cancelled(self, identifier: str, before) -> None:
        stored=self._effect_guide_before;self._effect_guide_before=None
        if isinstance(stored,EffectResourceLayer):
            self.particle_motion_render_timer.stop();self.particle_motion_finalize_timer.stop();self.guide_inspector_timer.stop();self._pending_guide_inspector=None;self._pending_particle_motion.clear();self._pending_particle_motion_layers.clear();self._dirty_particle_motion_layers.discard(identifier);self.interactive_gizmo_renderer.cancel();self.canvas.finish_interactive_motion_proxy(identifier)
            self._sync_guide_inspector(stored,stored.particle_settings if stored.placement_mode==PLACEMENT_PARTICLE else stored.single_settings)
            return
        field="composition_layer_settings" if isinstance(before,EffectCompositionLayer) else "particle_settings"
        self.apply_undo_value(identifier,field,before)

    def _sync_guide_inspector(self,layer,settings):
        started=perf_counter()
        if isinstance(settings,EffectCompositionLayer):self.composition_layer_properties.set_resource_layer(layer,self.project)
        else:self.particle_properties.set_resource_layer(layer,self.project);self.particle_properties.set_settings(settings)
        self.interactive_gizmo_renderer.collector.record("guide_inspector_sync",(perf_counter()-started)*1000.0)

    def _flush_guide_inspector_sync(self):
        pending=self._pending_guide_inspector;self._pending_guide_inspector=None
        if pending is not None:self._sync_guide_inspector(*pending)

    def refresh_particle_preview(self, emitter_id: str) -> None:
        emitter=next((e for e in self.project.particle_emitters if e.id==emitter_id),None)
        if emitter:
            if emitter_id not in self.particle_preview_manager.drafts:self.particle_preview_manager.ensure_draft(emitter)
            self.particle_preview_manager.schedule(self.project,emitter_id)

    def _particle_preview_ready(self, emitter_id: str, revision: int, frames: list) -> None:
        if self.particle_properties.emitter_id!=emitter_id:return
        emitter=next((e for e in self.project.particle_emitters if e.id==emitter_id),None)
        if emitter:self._activate_particle_preview(emitter,frames)

    def _activate_particle_preview(self, emitter, frames):
        self.active_preview_generator_id=emitter.id; self.canvas.set_preview(frames,emitter.generated_layer_id); self.canvas.set_gizmo(None); self.frame_index=min(self.frame_index,len(frames)-1); self.timeline.refresh(self.project,self.layer_index,self.frame_index,display_frame_count=len(frames),preview=True); self._refresh_playback_status()

    def _particle_preview_failed(self, emitter_id: str, revision: int, message: str) -> None:
        if self.particle_properties.emitter_id==emitter_id:self.statusBar().showMessage(message,5000)

    def revert_particle_draft(self, emitter_id: str) -> None:
        emitter=next((e for e in self.project.particle_emitters if e.id==emitter_id),None)
        if emitter:self.particle_properties.set_settings(self.particle_preview_manager.revert(emitter).settings); self._clear_preview()

    def bake_particle_emitter(self, emitter_id: str, settings: ParticleEmitterSettings) -> bool:
        runtime_logger().info("bake_particle start emitter=%s", emitter_id[:12])
        self.finalize_resource_layer_transform(emitter_id)
        self.interactive_gizmo_renderer.cancel();self.canvas.clear_interactive_transform_proxy(update=False)
        unified = next(
            (item for item in self.project.effect_resource_layers if item.id == emitter_id),
            None,
        )
        if unified is not None:
            after = deepcopy(unified)
            after.particle_settings = deepcopy(settings)
            try:
                layer = apply_effect_resource_layer(self.project, after)
            except (ValueError, MemoryError) as exc:
                log_exception("bake_particle", exc)
                QMessageBox.critical(
                    self, self.localization.text("effects.bake"), str(exc)
                )
                return False
            unified.__dict__.update(after.__dict__)
            self._dirty_particle_motion_layers.discard(unified.id)
            self._sync_resource_layer_adapters()
            self._clear_preview()
            self.layer_index = self.project.layers.index(layer)
            self._mark_dirty()
            self._refresh_all()
            runtime_logger().info("bake_particle success emitter=%s", emitter_id[:12])
            return True
        emitter = next(
            (item for item in self.project.particle_emitters if item.id == emitter_id),
            None,
        )
        if emitter is None:
            return False
        draft = self.particle_preview_manager.update(
            self.project, emitter, settings, immediate=True
        )
        session = self.particle_preview_manager.sessions.get(emitter_id)
        try:
            outputs = (
                [frame.copy() for frame in session.frames]
                if session and session.revision == draft.revision
                else render_particle_frames(
                    self.project,
                    ParticleEmitter(
                        id=emitter.id,
                        name=emitter.name,
                        settings=deepcopy(settings),
                    ),
                )
            )
            layer = apply_particle_frames(self.project, emitter, outputs)
        except (ValueError, MemoryError) as exc:
            log_exception("bake_particle", exc)
            QMessageBox.critical(
                self, self.localization.text("effects.bake"), str(exc)
            )
            return False
        emitter.settings = deepcopy(settings)
        self.particle_preview_manager.mark_applied(emitter)
        self._clear_preview()
        self.layer_index = self.project.layers.index(layer)
        self._mark_dirty()
        self._refresh_all()
        runtime_logger().info("bake_particle success emitter=%s", emitter_id[:12])
        return True

    def export_particle_preview(self, emitter_id: str) -> None:
        self.finalize_resource_layer_transform(emitter_id)
        draft=self.particle_preview_manager.drafts.get(emitter_id); session=self.particle_preview_manager.sessions.get(emitter_id)
        if draft is None or session is None or session.revision!=draft.revision:return
        directory=QFileDialog.getExistingDirectory(self,self.localization.text("effects.export_preview"),str(Path("exports").resolve()))
        if not directory:return
        emitter=next(e for e in self.project.particle_emitters if e.id==emitter_id)
        frames=session.frames
        unified=next((item for item in self.project.effect_resource_layers if item.id==emitter_id),None)
        if unified is not None:
            preview_emitter=ParticleEmitter(id=emitter.id,name=emitter.name,settings=deepcopy(draft.settings))
            frames=render_particle_frames(self.project,preview_emitter,layer_space_transform=unified.layer_space_transform)
            from app.services.effect_layer_transform_3d_render_service import transform_rgba_frame
            frames=[transform_rgba_frame(frame,unified.surface_transform,index) for index,frame in enumerate(frames)]
        runtime_logger().info("export_particle_preview start emitter=%s",emitter_id[:12])
        try:
            export_preview_sequence(frames, directory, emitter.name)
        except (ValueError, FileExistsError, OSError) as exc:
            log_exception("export_particle_preview", exc)
            QMessageBox.critical(
                self, self.localization.text("effects.export_preview"), str(exc)
            )
            return
        runtime_logger().info(
            "export_particle_preview success emitter=%s frames=%s",
            emitter_id[:12], len(frames),
        )
    def _refresh_effect_panels(self) -> None:
        selected_generator = self.effect_library.current_generator_id()
        self.effect_library.refresh(self.project)
        generator = next(
            (
                item
                for item in self.project.generators
                if item.id == selected_generator
            ),
            None,
        )
        self.effect_properties.set_generator(generator, self.project)
        if generator is not None:
            draft = self.preview_manager.ensure_draft(generator)
            self.effect_properties.set_settings(draft.settings)

    def generate_effect(
        self, generator_id: str, settings: TransformEmitterSettings
    ) -> bool:
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        if generator is None:
            return False
        draft = self.preview_manager.update_draft(self.project, generator, settings)
        session = self.preview_manager.current_session(generator_id)
        try:
            if session is not None:
                outputs = [frame.copy() for frame in session.frames]
            else:
                snapshot = PreviewRenderSnapshot.from_project(
                    self.project, generator.id, draft.revision, draft.settings
                )
                outputs = render_preview_snapshot(snapshot)
            layer = apply_rendered_frames(self.project, generator, outputs)
        except (EffectRenderError, ValueError, MemoryError) as exc:
            QMessageBox.critical(self, self.localization.text("error.generation"), str(exc))
            return False
        generator.settings = deepcopy(draft.settings)
        self.preview_manager.mark_applied(generator.id, generator.settings)
        self._clear_preview()
        self.layer_index = self.project.layers.index(layer)
        self.frame_index = min(self.frame_index, len(self.project.frames) - 1)
        self._mark_dirty()
        self._refresh_all()
        self.effect_library.select_generator(generator.id)
        self.select_generator(generator.id)
        self.statusBar().showMessage(self.localization.text("status.generated").format(name=generator.name), 4000)
        return True

    def reset_generator_settings(self, generator_id: str) -> None:
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        if generator is None:
            return
        source_id = generator.settings.source_asset_id
        defaults = TransformEmitterSettings(
            source_asset_id=source_id,
            origin_x=self.project.width / 2.0,
            origin_y=self.project.height / 2.0,
            line_end_x=self.project.width * 0.75,
            line_end_y=self.project.height / 2.0,
            radius=min(self.project.width, self.project.height) / 4.0,
        )
        self.effect_properties.set_settings(defaults)
        self.update_generator_draft(generator.id, defaults)
        self.effect_properties.settings_status.setText(
            "Defaults loaded; Apply to Frames to commit"
        )

    def update_generator_draft(
        self, generator_id: str, settings: TransformEmitterSettings
    ) -> None:
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        if generator is None:
            return
        self.preview_manager.update_draft(self.project, generator, settings)
        if self.effect_properties.generator_id == generator_id:
            self.canvas.set_gizmo(generator_id, settings, mode=self.effect_properties.current_gizmo_mode(), edit_end=self.effect_properties.edit_end_check.isChecked(), locked=self.play_timer.isActive())

    def _set_gizmo_mode(self, mode: str, edit_end: bool) -> None:
        generator_id = self.effect_properties.generator_id
        draft = self.preview_manager.drafts.get(generator_id) if generator_id else None
        self.canvas.set_gizmo(generator_id, None if draft is None else draft.settings, mode=mode, edit_end=edit_end, locked=self.play_timer.isActive())

    def _set_effect_guides_visible(self, visible: bool) -> None:
        self.settings_service.settings.setValue("ui/show_effect_editing_guides",bool(visible))
        self.canvas.set_effect_guides_visible(visible)

    def _gizmo_changed(self, generator_id: str, settings: TransformEmitterSettings) -> None:
        if self.play_timer.isActive(): self.set_playing(False)
        self.effect_properties.set_settings(settings)
        self.update_generator_draft(generator_id, settings)

    def refresh_generator_preview(self, generator_id: str) -> None:
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        if generator is None:
            return
        self.preview_manager.ensure_draft(generator)
        self.preview_manager.schedule(self.project, generator_id, immediate=True)

    def revert_generator_draft(self, generator_id: str) -> None:
        if generator_id not in self.preview_manager.drafts:
            return
        draft = self.preview_manager.revert(generator_id)
        self._clear_preview()
        if self.effect_properties.generator_id == generator_id:
            self.effect_properties.set_settings(draft.settings)
            self.effect_properties.set_preview_state("applied")

    def _preview_state_changed(self, generator_id: str, state: str) -> None:
        if self.effect_properties.generator_id == generator_id:
            self.effect_properties.set_preview_state(state)

    def _preview_ready(
        self, generator_id: str, revision: int, frames: list
    ) -> None:
        if self.effect_properties.generator_id != generator_id:
            return
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        if generator is not None:
            self._activate_preview(generator, frames)

    def _preview_failed(self, generator_id: str, revision: int, message: str) -> None:
        if self.effect_properties.generator_id == generator_id:
            self.statusBar().showMessage(
                "Preview failed. Applied frames were not changed.", 5000
            )

    def _activate_preview(self, generator: TransformEmitter, frames: list) -> None:
        self._invalidate_playback_cache(stop=True)
        self.active_preview_generator_id = generator.id
        self.frame_index = min(self.frame_index, len(frames) - 1)
        self.canvas.set_preview(frames, generator.generated_layer_id)
        self.canvas.set_frame(self.frame_index)
        self.timeline.refresh(
            self.project,
            self.layer_index,
            self.frame_index,
            display_frame_count=len(frames),
            preview=True,
        )
        self._refresh_playback_status()

    def _clear_preview(self) -> None:
        if self.active_preview_generator_id is not None and self.play_timer.isActive():
            self.set_playing(False)
        self.active_preview_generator_id = None
        if hasattr(self,"effect_playback"):self._invalidate_playback_cache(stop=False)
        self.canvas.clear_preview()
        self.frame_index = min(self.frame_index, len(self.project.frames) - 1)
        self.canvas.set_frame(self.frame_index)
        self.timeline.refresh(self.project, self.layer_index, self.frame_index)
        self._refresh_playback_status()
        if hasattr(self,"interactive_proxy_prewarm") and not self._timeline_scrubbing:self._schedule_resource_transform_prewarm()

    def delete_source_asset(self, asset_id: str) -> None:
        asset = next(
            (item for item in self.project.source_assets if item.id == asset_id), None
        )
        if asset is None:
            return
        if any(
            item.settings.source_asset_id == asset_id for item in self.project.generators
        ):
            QMessageBox.warning(
                self,
                "Source Asset In Use",
                "Delete its Transform Emitter before deleting this Source Asset.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Delete Source Asset",
            f"Delete source asset '{asset.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.project.source_assets.remove(asset)
        self._mark_dirty()
        self._refresh_effect_panels()

    def delete_generator(self, generator_id: str) -> None:
        generator = next(
            (item for item in self.project.generators if item.id == generator_id), None
        )
        if generator is None:
            return
        if not self._resolve_generator_draft(generator_id):
            return
        answer = QMessageBox.question(
            self,
            "Delete Generator",
            f"Delete '{generator.name}' and its Generated Layer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        layer = next(
            (
                item
                for item in self.project.layers
                if item.id == generator.generated_layer_id
            ),
            None,
        )
        if layer is not None:
            if len(self.project.layers) == 1:
                self.project.add_layer()
            layer_index = self.project.layers.index(layer)
            self.project.delete_layer(layer_index)
        self.project.generators.remove(generator)
        self.layer_index = min(self.layer_index, len(self.project.layers) - 1)
        self._mark_dirty()
        self._refresh_all()

    def create_project_settings_dialog(self) -> ProjectSettingsDialog:
        """Create an editable dialog from the latest project values."""
        return ProjectSettingsDialog(
            self.project,
            self.project_path,
            self.apply_project_settings,
            self,
            localization=self.localization,
        )

    def show_project_settings(self) -> None:
        self.create_project_settings_dialog().exec()

    def apply_project_settings(self, values: ProjectSettingsValues) -> bool:
        """Validate and atomically apply general and canvas settings."""
        size_changed = (values.width, values.height) != (
            self.project.width,
            self.project.height,
        )
        general_changed = (
            values.name != self.project.name
            or values.fps != self.project.fps
            or values.loop != self.project.loop
        )
        if not size_changed and not general_changed:
            return True
        if size_changed and self._canvas_change_needs_confirmation(values):
            if not self._confirm_canvas_change(values):
                return False
        if size_changed:
            self.set_playing(False)
            self.preview_manager.reset_context()
            self.particle_preview_manager.reset_context()
            self._clear_preview()
            try:
                if values.resize_mode is CanvasResizeMode.SCALE:
                    scale_project(self.project, values.width, values.height)
                else:
                    resize_canvas(
                        self.project, values.width, values.height, values.anchor
                    )
            except CanvasResizeError as exc:
                QMessageBox.critical(self, self.localization.text("error.canvas_resize"), str(exc))
                return False
        self.project.name = values.name
        self.project.fps = values.fps
        self.project.loop = values.loop
        if self.play_timer.isActive():
            self.play_timer.setInterval(max(1, round(1000 / values.fps)))
        self._mark_dirty()
        self._refresh_all()
        return True

    def _canvas_change_needs_confirmation(
        self, values: ProjectSettingsValues
    ) -> bool:
        return (
            values.width < self.project.width
            or values.height < self.project.height
            or values.resize_mode is CanvasResizeMode.SCALE
            or self.dirty
        )

    def _confirm_canvas_change(self, values: ProjectSettingsValues) -> bool:
        answer = QMessageBox.question(
            self,
            "Confirm Canvas Change",
            f"Current size: {self.project.width} × {self.project.height}\n"
            f"New size: {values.width} × {values.height}\n"
            f"Mode: {values.resize_mode.value}\n\n"
            "This operation may crop or replace pixel data and cannot currently be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def create_playback_test(self) -> None:
        """Replace the current project with the built-in playback diagnostic."""
        if not self._confirm_unapplied_previews() or not self._confirm_discard():
            return
        self.set_playing(False)
        self._invalidate_playback_cache(stop=False)
        self.preview_manager.reset_context()
        self.particle_preview_manager.reset_context()
        self._clear_preview()
        self.project = create_playback_test_project()
        self.project_path = None
        self.frame_index = self.layer_index = 0
        self.dirty = True
        self._refresh_all()
        self.statusBar().showMessage(self.localization.text("status.playback_test"), 3000)

    def show_keyboard_shortcuts(self) -> None:
        dialog = KeyboardShortcutsDialog(
            self.shortcuts, self, localization=self.localization
        )
        dialog.shortcuts_applied.connect(self.apply_shortcuts)
        dialog.exec()

    def show_interface_settings(self) -> None:
        dialog=InterfaceSettingsDialog(self.settings_service.settings,self.localization,self)
        dialog.frame_width_changed.connect(self.apply_timeline_frame_width)
        dialog.exec()

    def show_project_overview(self) -> None:
        PreviewBuildNoticeDialog(
            self.localization,
            self.settings_service.settings,
            self,
            manual_open=True,
        ).exec()

    def copy_diagnostic_information(self) -> None:
        QApplication.clipboard().setText(build_diagnostic_text())
        self.statusBar().showMessage(self.localization.text("status.diagnostics_copied"), 4000)
        runtime_logger().info("diagnostic_information copied_to_clipboard")

    def apply_timeline_frame_width(self,width:int) -> None:
        width=max(20,min(96,int(width)));self.settings_service.settings.setValue("ui/timeline_frame_width",width)
        self.timeline.set_frame_cell_width(width);self.resource_editor.set_timeline_frame_width(width)

    def apply_shortcuts(self, shortcuts: dict[str, str | list[str]]) -> bool:
        """Persist shortcuts and update their QAction menu entries immediately."""
        try:
            normalized = self.settings_service.save(shortcuts)
        except (SettingsError, ValueError) as exc:
            QMessageBox.warning(self, self.localization.text("error.shortcuts"), str(exc))
            return False
        self.shortcuts = normalized
        self._update_action_shortcuts(normalized)
        self.playback_shortcut_controller.set_sequences(
            normalized.get("play_stop_animation", [])
        )
        self.frame_shortcut_controller.set_sequences(normalized)
        return True

    def _update_action_shortcuts(self, shortcuts: dict[str, list[str]]) -> None:
        for key, action in self.shortcut_actions.items():
            action.setShortcuts(
                [QKeySequence(item) for item in shortcuts.get(key, [])]
            )
        if hasattr(self, "localization"):
            self._refresh_tooltips()

    def add_frame(self) -> None:
        """Insert a transparent frame after the current frame and select it."""
        self.application_undo_stack.push(EditorOperationCommand(self,"add_frame",{"index":self.frame_index},"Add Frame"))

    def duplicate_frame(self) -> None:
        """Duplicate the current frame immediately after it and select the copy."""
        self.application_undo_stack.push(EditorOperationCommand(self,"duplicate_frame",{"index":self.frame_index},"Duplicate Frame"))

    def delete_frame(self) -> None:
        try:
            if len(self.project.frames)<=1:raise ProjectError("a project must contain at least one frame")
        except ProjectError as exc:
            QMessageBox.information(self, self.localization.text("error.delete_frame"), str(exc))
            return
        self.application_undo_stack.push(EditorOperationCommand(self,"delete_frame",{"index":self.frame_index,"frame":self.project.frames[self.frame_index]},"Delete Frame"))

    def add_layer(self) -> None:
        """Add the next collision-free default layer and select it."""
        self.application_undo_stack.push(EditorOperationCommand(self,"add_layer",{"name":self.project.next_layer_name()},"Add Layer"))

    def _effect_model_for_layer(self, layer):
        for collection_name, kind in (
            ("effect_resource_layers", "resource_layer"),
            ("effect_composition_layers", "composition_layer"),
            ("particle_emitters", "particle_system"),
            ("generators", "legacy_generator"),
        ):
            collection = getattr(self.project, collection_name)
            for index, model in enumerate(collection):
                if model.generated_layer_id == layer.id:
                    return collection_name, kind, index, model
        return None

    def _selected_layer_is_deletable(self) -> bool:
        if not self.project.layers or not (0 <= self.layer_index < len(self.project.layers)):
            return False
        return len(self.project.layers) > 1 or self._effect_model_for_layer(
            self.project.layers[self.layer_index]
        ) is not None

    def _delete_layer_at(self, layer_index: int) -> None:
        if 0 <= layer_index < len(self.project.layers):
            self.select_cell(layer_index, min(self.frame_index, self._display_frame_count() - 1))
            self.delete_layer()

    def _apply_effect_layer_delete(self, state: dict, forward: bool) -> None:
        layer = state["layer"]
        model_info = state.get("model_info")
        self.set_playing(False)
        self._clear_preview()
        self.canvas.set_gizmo(None)
        self.canvas.set_effect_guide(None)
        if forward:
            if model_info:
                collection = getattr(self.project, model_info["collection"])
                if model_info["model"] in collection:
                    collection.remove(model_info["model"])
                identifier = model_info["model"].id
                manager = self.particle_preview_manager if model_info["kind"] in {"particle_system","resource_layer"} else self.preview_manager
                manager.drafts.pop(identifier, None)
                manager.sessions.pop(identifier, None)
                if model_info["kind"]=="resource_layer":self._sync_resource_layer_adapters()
            if layer in self.project.layers:
                self.project.layers.remove(layer)
            for frame in self.project.frames:
                frame.layer_pixels.pop(layer.id, None)
            if not self.project.layers:
                placeholder = state.setdefault("placeholder", Layer(self.project.next_layer_name()))
                self.project.layers.append(placeholder)
                for frame in self.project.frames:
                    frame.layer_pixels[placeholder.id] = empty_pixels(self.project.width, self.project.height)
            self.layer_index = min(max(0, state["index"] - 1), len(self.project.layers) - 1)
            self.frame_index = min(state["frame_index"], len(self.project.frames) - 1)
        else:
            placeholder = state.get("placeholder")
            if placeholder in self.project.layers:
                self.project.layers.remove(placeholder)
                for frame in self.project.frames:
                    frame.layer_pixels.pop(placeholder.id, None)
            index = min(state["index"], len(self.project.layers))
            self.project.layers.insert(index, layer)
            for frame, pixels in zip(self.project.frames, state["pixels"]):
                frame.layer_pixels[layer.id] = pixels
            if model_info:
                collection = getattr(self.project, model_info["collection"])
                collection.insert(min(model_info["index"], len(collection)), model_info["model"])
                if model_info["kind"]=="resource_layer":self._sync_resource_layer_adapters()
            self.layer_index = index
            self.frame_index = min(state["frame_index"], len(self.project.frames) - 1)

    def delete_layer(self) -> None:
        if not self._selected_layer_is_deletable():
            return
        layer=self.project.layers[self.layer_index];pixels=[frame.layer_pixels[layer.id] for frame in self.project.frames]
        found = self._effect_model_for_layer(layer)
        model_info = None
        if found:
            collection, kind, index, model = found
            model_info = {"collection": collection, "kind": kind, "index": index, "model": model}
        state={"index":self.layer_index,"layer":layer,"pixels":pixels,"model_info":model_info,"frame_index":self.frame_index}
        self.application_undo_stack.push(EditorOperationCommand(self,"delete_effect_layer",state,"Delete Effect Layer"))

    def select_cell(self, layer_index: int, frame_index: int) -> None:
        """Synchronize a timeline cell selection with the canvas."""
        if not (0 <= layer_index < len(self.project.layers)):
            return
        if not (0 <= frame_index < self._display_frame_count()):
            return
        self.layer_index = layer_index
        self.frame_index = frame_index
        self.interactive_gizmo_renderer.cancel()
        self._render_dirty_particle_motion_frame(frame_index)
        self.canvas.set_layer(layer_index)
        self.canvas.set_frame(frame_index)
        layer=self.project.layers[layer_index]
        resource_layer=next((item for item in self.project.effect_resource_layers if item.generated_layer_id==layer.id),None)
        composition_layer=next((item for item in self.project.effect_composition_layers if item.generated_layer_id==layer.id),None)
        particle=next((item for item in self.project.particle_emitters if item.generated_layer_id==layer.id),None)
        if resource_layer:self.select_resource_layer(resource_layer.id)
        elif composition_layer:self.select_effect_composition_layer(composition_layer.id)
        elif particle:self.select_particle_emitter(particle.id)
        self.timeline.set_current_cell(
            self.project,
            layer_index,
            frame_index,
            display_frame_count=self._display_frame_count(),
        )
        self._refresh_selection_status()
        self._refresh_playback_status()
        if not self._timeline_scrubbing:self._schedule_resource_transform_prewarm()

    def select_frame(self, index: int) -> None:
        if 0 <= index < self._display_frame_count():
            self.frame_index = index
            self.interactive_gizmo_renderer.cancel()
            self._render_dirty_particle_motion_frame(index)
            self.canvas.set_frame(index)
            self.project._current_effect_frame=index
            if 0<=self.layer_index<len(self.project.layers):
                selected=next((item for item in self.project.effect_resource_layers if item.generated_layer_id==self.project.layers[self.layer_index].id),None)
                if selected:
                    panel=self.particle_properties.transform_panel if selected.placement_mode==PLACEMENT_PARTICLE else self.composition_layer_properties.transform_panel;panel.set_layer(selected,index);self.canvas.set_resource_layer_transform(selected.id,selected.layer_transform,mode=self.canvas.resource_transform_mode)
            self.timeline.set_current_cell(
                self.project,
                self.layer_index,
                index,
                display_frame_count=self._display_frame_count(),
            )
            self._refresh_selection_status()
            self._refresh_playback_status()
            if not self._timeline_scrubbing and not self.play_timer.isActive():self._schedule_resource_transform_prewarm()

    def set_fps(self, value: int) -> None:
        if self.project.fps != value:
            self.project.fps = value
            self._mark_dirty()
        self.play_timer.setInterval(max(1, round(1000 / value)))
        self._refresh_playback_status()

    def _playback_preview_identity(self) -> tuple:
        frames=self.canvas.preview_frames
        return () if frames is None else (self.active_preview_generator_id or "preview",id(frames),len(frames))

    def _playback_key(self,index: int):
        return self.effect_playback.key(self.project,self._project_edit_revision,index,self._playback_preview_identity())

    def _invalidate_playback_cache(self,stop=True) -> None:
        if stop and self._playback_state!=PLAYBACK_STOPPED:self.set_playing(False)
        self.effect_playback.invalidate();self.canvas.end_playback(False);self.canvas.clear_playback_frame(update=False)

    def _display_cached_playback_frame(self,index: int) -> bool:
        started=perf_counter()
        count=self._display_frame_count();value=self.effect_playback.get(self._playback_key(index))
        if value is None:
            if self._playback_state==PLAYBACK_PLAYING:
                self.effect_playback.collector.underruns+=1;self.effect_playback.collector.frame_holds+=1
            for delta in range(1,count):
                fallback=(index-delta)%count if self.project.loop else index-delta
                if fallback<0:break
                value=self.effect_playback.get(self._playback_key(fallback))
                if value is not None:break
        if value is None:
            self.effect_playback.collector.record("cache_lookup_display",(perf_counter()-started)*1000.0);return False
        canvas_started=perf_counter();self.canvas.set_playback_frame(value.pixmap,value.key.frame_index,value.key)
        self.effect_playback.collector.record("canvas_update",(perf_counter()-canvas_started)*1000.0);self.effect_playback.collector.record("cache_lookup_display",(perf_counter()-started)*1000.0);return True

    def _playback_frame_ready(self,value) -> None:
        if value.key.project_identity!=id(self.project) or value.key.render_revision!=self._project_edit_revision:return
        if self._playback_state==PLAYBACK_PREPARING:
            self._refresh_playback_status();self._start_prepared_playback_if_ready();return
        if self._playback_state==PLAYBACK_PLAYING and value.key.frame_index==self.frame_index:self.canvas.set_playback_frame(value.pixmap,value.key.frame_index,value.key)

    def _playback_preparation_failed(self,message: str) -> None:
        runtime_logger().error("effect_playback preparation_failed message=%s",message)
        if self._playback_state==PLAYBACK_PREPARING:self.set_playing(False)
        self.statusBar().showMessage("Playback frame preparation failed. The current exact frame is being held.",5000)

    def _start_prepared_playback_if_ready(self) -> bool:
        plan=self._playback_plan
        if self._playback_state!=PLAYBACK_PREPARING or plan is None or not self.effect_playback.all_ready(plan.required_keys):return False
        self._playback_state=PLAYBACK_PLAYING;self._playback_start_frame=self.frame_index;self._playback_last_step=0
        self._display_cached_playback_frame(self.frame_index);self._playback_clock.start();self.play_timer.start(max(1,round(1000/self.project.fps)));self.effect_playback.collector.clock_starts+=1
        self._refresh_playback_status();return True

    def _select_playback_frame(self,index: int) -> None:
        started=perf_counter()
        self.frame_index=index;self.canvas.set_frame(index);self.project._current_effect_frame=index;self._display_cached_playback_frame(index)
        timeline_started=perf_counter();self.timeline.set_current_cell(self.project,self.layer_index,index,display_frame_count=self._display_frame_count());self._refresh_selection_status();self._refresh_playback_status()
        self.effect_playback.collector.record("timeline_status_update",(perf_counter()-timeline_started)*1000.0);self.effect_playback.collector.record("playback_frame_selection",(perf_counter()-started)*1000.0)

    def set_playing(self, playing: bool) -> None:
        if self.play_action.isChecked() != playing:
            with QSignalBlocker(self.play_action):
                self.play_action.setChecked(playing)
        if playing:
            if self._playback_state in {PLAYBACK_PREPARING,PLAYBACK_PLAYING}:return
            self.interactive_proxy_prewarm.cancel()
            self._flush_resource_transform_final();self._flush_particle_motion_final()
            self.canvas.clear_interactive_transform_proxy(update=False)
            self.canvas.begin_playback();self._playback_start_frame=self.frame_index;self._playback_last_step=0
            preview=self.canvas.preview_frames
            self._playback_state=PLAYBACK_PREPARING
            self._playback_plan=self.effect_playback.prepare(self.project,self._project_edit_revision,self.frame_index,preview,self.canvas.preview_layer_id,self._playback_preview_identity())
            self.play_timer.start(max(1, round(1000 / self.project.fps)))
            self._start_prepared_playback_if_ready()
        else:
            if self._playback_state!=PLAYBACK_STOPPED:self.effect_playback.cancel_preparation()
            self._playback_state=PLAYBACK_STOPPED;self._playback_plan=None
            self.play_timer.stop()
            self.canvas.end_playback(True)
        self.timeline.set_playing(playing)
        self._refresh_tooltips()
        self._refresh_playback_status()
        if not playing and not self._timeline_scrubbing:self._schedule_resource_transform_prewarm()

    def _refresh_playback_status(self) -> None:
        preparing=self._playback_state==PLAYBACK_PREPARING;plan=self._playback_plan
        ready=0 if plan is None else self.effect_playback.ready_count(plan.required_keys)
        required=0 if plan is None else len(plan.required_keys)
        self.timeline.update_playback_status(
            self._playback_state==PLAYBACK_PLAYING,
            self.frame_index,
            self._display_frame_count(),
            self.project.fps,
            preview=self.active_preview_generator_id is not None,
            preparing=preparing,ready=ready,required=required,
        )

    def _advance_playback(self, force_step: bool = True) -> None:
        tick_started=perf_counter()
        if self._playback_state==PLAYBACK_PREPARING or (not force_step and self._playback_state!=PLAYBACK_PLAYING):return
        count=self._display_frame_count()
        if count<1:return
        if not force_step and self._playback_plan is not None and self._playback_plan.full_prebuffer:
            next_index=self.frame_index+1
            if next_index>=count:
                if self.project.loop:
                    next_index=0;self.effect_playback.collector.loop_ready_counts.append(self.effect_playback.ready_count(self._playback_plan.keys))
                else:self.set_playing(False);return
            self._playback_last_step+=1;self._select_playback_frame(next_index);self.effect_playback.collector.record("timeline_tick",(perf_counter()-tick_started)*1000.0);return
        if force_step:
            next_index=self.frame_index+1
            if next_index>=count:
                if self.project.loop:next_index=0
                else:self.set_playing(False);return
        else:
            step=int(self._playback_clock.elapsed()*self.project.fps/1000.0)
            if step<=self._playback_last_step:return
            previous_step=self._playback_last_step
            if step>previous_step+1:self.effect_playback.collector.frame_drops+=step-previous_step-1
            self._playback_last_step=step;absolute=self._playback_start_frame+step
            if not self.project.loop and absolute>=count:
                self._select_playback_frame(count-1);self.set_playing(False);return
            if self.project.loop and absolute//count>(self._playback_start_frame+previous_step)//count and self._playback_plan is not None:
                self.effect_playback.collector.loop_ready_counts.append(self.effect_playback.ready_count(self._playback_plan.keys))
            next_index=absolute%count if self.project.loop else absolute
        self._select_playback_frame(next_index);self.effect_playback.collector.record("timeline_tick",(perf_counter()-tick_started)*1000.0)

    def _resolve_generator_draft(self, generator_id: str) -> bool:
        draft = self.preview_manager.drafts.get(generator_id)
        if draft is None or not draft.is_dirty:
            return True
        choice = self._ask_unapplied_choice()
        if choice == "cancel":
            return False
        if choice == "apply":
            return self.generate_effect(generator_id, draft.settings)
        self.preview_manager.discard(generator_id)
        if self.active_preview_generator_id == generator_id:
            self._clear_preview()
        return True

    def _confirm_unapplied_previews(self) -> bool:
        dirty_ids = self.preview_manager.dirty_generator_ids()
        if not dirty_ids:
            return True
        choice = self._ask_unapplied_choice()
        if choice == "cancel":
            return False
        if choice == "apply":
            for generator_id in list(dirty_ids):
                draft = self.preview_manager.drafts.get(generator_id)
                if draft is not None and not self.generate_effect(
                    generator_id, draft.settings
                ):
                    return False
        else:
            for generator_id in list(dirty_ids):
                self.preview_manager.discard(generator_id)
            self._clear_preview()
        return True

    def _ask_unapplied_choice(self) -> str:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Unapplied Preview")
        dialog.setText(self.localization.text("message.unapplied"))
        apply_button = dialog.addButton("Apply", QMessageBox.ButtonRole.AcceptRole)
        discard_button = dialog.addButton(
            "Discard", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is apply_button:
            return "apply"
        if clicked is discard_button:
            return "discard"
        return "cancel"

    def previous_frame(self) -> None:
        self.set_playing(False)
        self.select_frame(max(0, self.frame_index - 1))

    def next_frame(self) -> None:
        self.set_playing(False)
        self.select_frame(min(self._display_frame_count() - 1, self.frame_index + 1))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._confirm_unapplied_previews() and self._confirm_discard():
            self.preview_manager.close()
            self.effect_playback.close()
            self.interactive_gizmo_renderer.close()
            self.particle_preview_manager.reset_context()
            self.particle_motion_render_timer.stop();self.particle_motion_finalize_timer.stop();self.transform_inspector_timer.stop();self.guide_inspector_timer.stop();self._pending_particle_motion.clear();self._pending_particle_motion_layers.clear()
            event.accept()
        else:
            event.ignore()
