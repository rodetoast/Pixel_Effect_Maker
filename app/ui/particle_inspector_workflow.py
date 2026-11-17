"""View-only Particle workflow. Owns layout/navigation, never settings or commands."""
from PySide6.QtCore import QEvent, QObject, QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QFormLayout, QGroupBox, QLabel, QLayout, QLineEdit, QVBoxLayout, QWidget

from .focus_wheel_widgets import FocusWheelComboBox
from .inspector_components import InspectorSection
from .layout_metrics import SPACING_SM
from app.services.localization_service import EN, KO


CATEGORIES = {
    "source": ("Source", "소스"), "emit": ("Emit", "방출"),
    "motion": ("Motion", "움직임"), "look": ("Lifetime / Look", "수명 / 외형"),
    "trail": ("Trail", "잔상 궤적"), "events": ("Events", "이벤트"),
    "rendering": ("Rendering", "합성"), "transform": ("Transform / Advanced", "변환 / 고급"),
}


class ParticleInspectorWorkflow(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.sections = {}
        self._context = None
        self._positions = {}
        self._revealed = set()
        self._queued = False
        self._syncing = False
        self.registry = []
        self._reorganize()
        self._build_navigation()
        panel.trail_status.message_changed.connect(self.sync)
        panel.sub_status.message_changed.connect(self.sync)
        panel.cycle_status.message_changed.connect(self.sync)
        panel.lifetime_group.installEventFilter(self)
        self.begin_context(None)
        self.sync()

    @property
    def ko(self):
        return bool(self.panel._localization and self.panel._localization.language == "ko")

    def _reorganize(self):
        p = self.panel
        self._groups = {title: group for title, group, _, _ in p._group_records}
        common = p.common_form.parentWidget()
        # Remove layout items, not widgets/signals. Legacy adapters stay parked.
        while p.layout.count():
            p.layout.takeAt(0)
        p.title.hide(); p.mode_help.hide()
        for key in CATEGORIES:
            section = p.trail_group if key == "trail" else p.sub_group if key == "events" else InspectorSection(key, p.inspector_view_state)
            self.sections[key] = section
            if key not in {"trail", "events"}:
                layout = QVBoxLayout(section.body)
                layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
                layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(SPACING_SM)
            p.layout.addWidget(section)
        group_categories = {
            "Particle Resource": "source", "Emission": "emit", "Spawn Shape": "emit", "Direction": "emit",
            "Motion Basic": "motion", "Orbit Center": "motion", "Orbit Shape": "motion", "Helix": "motion",
            "Motion Interpolation": "motion", "Motion Advanced": "motion", "Natural Motion": "motion",
            "Over Lifetime": "look", "Rendering": "rendering",
        }
        # Output/start are emission timing, not source sprite playback.
        clip_record = next(record for record in p._group_records if record[0] == "Particle Resource")
        emit_record = next(record for record in p._group_records if record[0] == "Emission")
        for name, editor in list(clip_record[3]):
            if editor in {p.output_frame_count, p.start_frame}:
                row = clip_record[2].takeRow(editor)
                emit_record[2].addRow(row.labelItem.widget(), editor)
                clip_record[3].remove((name, editor)); emit_record[3].append((name, editor))
        self.sections["transform"].body.layout().addWidget(common)
        self.sections["transform"].body.layout().addWidget(p.mode_help); p.mode_help.show()
        for title, category in group_categories.items():
            self.sections[category].body.layout().addWidget(self._groups[title])
        self.source_timing_help=QLabel();self.source_timing_help.setWordWrap(True);self.source_timing_help.setMinimumWidth(0)
        self.sections["source"].body.layout().addWidget(self.source_timing_help)
        # Split mixed Random Range by meaning, retaining each original editor.
        random_record = next(record for record in p._group_records if record[0] == "Random Range")
        _, parked, old_form, records = random_record
        p._group_records.remove(random_record)
        self._row_forms = {}
        allocations = {
            "source": {p.clip_speed_min, p.clip_speed_max, p.random_start_frame},
            "emit": {p.lifetime_min, p.lifetime_max, p.start_delay_min, p.start_delay_max, p.seed},
            "motion": {p.angular_velocity_min, p.angular_velocity_max},
            "look": {p.scale_min, p.scale_max, p.rotation_min, p.rotation_max},
        }
        for category, editors in allocations.items():
            container = QWidget(); form = QFormLayout(container)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            form.setVerticalSpacing(4); form.setContentsMargins(0, 0, 0, 0)
            moved = []
            for name, editor in records:
                if editor not in editors:
                    continue
                row = old_form.takeRow(editor)
                label = row.labelItem.widget()
                label.setMinimumWidth(130)
                form.addRow(label, editor)
                self._row_forms[editor] = form
                moved.append((name, editor))
            self.sections[category].body.layout().addWidget(container)
            # Existing translation/tooltip registry still addresses the same labels.
            p._group_records.append(("Random Range", parked, form, moved))
        parked.hide()
        self.sections["emit"].body.layout().addWidget(p.randomize)
        self.sections["transform"].body.layout().addWidget(p.transform_panel)
        self.surface_section = InspectorSection("surface_compatibility", p.inspector_view_state)
        surface_layout = QVBoxLayout(self.surface_section.body)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        p.transform_panel.advanced_body.layout().removeWidget(p.transform_panel.surface_group)
        surface_layout.addWidget(p.transform_panel.surface_group)
        p.transform_panel.advanced_body.layout().addWidget(self.surface_section)
        self.action_area = QGroupBox()
        actions = QVBoxLayout(self.action_area)
        self.action_help = QLabel(); self.action_help.setWordWrap(True); self.action_help.setMinimumWidth(0)
        actions.addWidget(self.action_help)
        for button in (p.refresh, p.bake, p.export, p.revert):actions.addWidget(button)
        self.sections["source"].body.layout().addWidget(self.action_area)
        p.layout.addStretch()
        self._index_properties()

    def _index_properties(self):
        p = self.panel
        for title, _, form, records in p._group_records:
            for alias, editor in records:
                self._register(editor, form.labelForField(editor), alias)
        for editor in (p.name, p.parent_layer, p.mode):
            self._register(editor, p.common_form.labelForField(editor), "Parent Parenting 부모" if editor is p.parent_layer else "")
        for editor, row in p.trail_form.rows.items():
            self._register(editor, row.label, "Trail 잔상")
        for editor, row in p.sub_form.rows.items():
            self._register(editor, row.label, "Birth Death Sub-emitter 생성 사망 하위 방출기")
        for point in p._point_editors:
            point.title.setWordWrap(True)
            self._register(point, point.title, "Lifetime " + point.channel + " 수명 RGB 색상 불투명도 크기")
            for editor in (point.time, point.color if point.channel == "color" else point.value, point.easing, point.add, point.remove):
                self._register(editor, point.title, "Lifetime " + point.channel)
        for name, editor in p.transform_panel.fields.items():
            self._register(editor, p.transform_panel.form.labelForField(p.transform_panel.field_rows[name]), name)
        for name, editor in p.transform_panel.surface_fields.items():
            self._register(editor, p.transform_panel.surface_form.labelForField(editor), "Surface Compatibility 호환 " + name)
        for name, editor in p.transform_panel.key_buttons.items():
            self._register(editor, None, "Key Auto-Key 키 " + name)
        for name, editor in p.transform_panel.easings.items():
            self._register(editor, None, "Easing 보간 " + name)
        for name, editor in p.transform_panel.gizmo_buttons.items():
            self._register(editor, None, "Gizmo 기즈모 " + name)
        for editor in (p.randomize, p.refresh, p.bake, p.export, p.revert, p.transform_panel.reset, p.transform_panel.surface_reset):
            self._register(editor, None, "Export 내보내기" if editor is p.export else "")
        self._register(p.transform_panel, None, "Advanced Bypass 고급 적용")

    def _register(self, editor, label, alias):
        category = next(key for key, section in self.sections.items() if section.isAncestorOf(editor))
        editor.setProperty("inspectorCategory", category)
        translations = " ".join(KO.get(key, "") for key, text in EN.items() if text == alias)
        self.registry.append((category, editor, label, alias + " " + translations))

    def _build_navigation(self):
        p = self.panel
        self.navigation = QWidget(p)
        self.navigation.setObjectName("particleInspectorNavigation")
        layout = QVBoxLayout(self.navigation); layout.setContentsMargins(6, 3, 6, 3); layout.setSpacing(3)
        self.selection = QLabel(); self.selection.setWordWrap(True); self.selection.setMinimumWidth(0)
        self.jump_combo = FocusWheelComboBox(); self.search = QLineEdit(); self.results = FocusWheelComboBox()
        self.warnings = FocusWheelComboBox(); self.notice = QLabel(); self.notice.setWordWrap(True)
        for widget in (self.selection, self.jump_combo, self.search, self.results, self.warnings, self.notice):
            widget.setMinimumWidth(0); layout.addWidget(widget)
        self.results.hide(); self.notice.hide(); self.warnings.hide()
        self.jump_combo.activated.connect(lambda index: self.jump(self.jump_combo.itemData(index)))
        self.search.textChanged.connect(self._search_changed)
        self.results.activated.connect(self._activate_result)
        self.warnings.activated.connect(lambda index: self.jump(self.warnings.itemData(index)))
        self.navigation.show()

    def pending_numeric(self):
        widget = QApplication.focusWidget()
        while widget is not None and not isinstance(widget, QAbstractSpinBox):
            widget = widget.parentWidget()
        return widget is not None and self.panel.widget().isAncestorOf(widget) and widget.lineEdit().isModified()

    def begin_context(self, selection_id):
        if selection_id == self._context and hasattr(self, "_initialized"):
            return
        self._positions[self._context] = self.panel.verticalScrollBar().value()
        self._context = selection_id; self._initialized = True; self._revealed.clear()
        state = self.panel.inspector_view_state
        for key, section in (*self.sections.items(), ("surface", self.surface_section)):
            if state.expanded("particle", selection_id, section.section_id, default=None) is None:
                state.remember("particle", selection_id, section.section_id, key in {"source", "emit"})
            section.set_context("particle", selection_id)
        QTimer.singleShot(0, lambda context=selection_id: self._restore_scroll(context))

    def _restore_scroll(self, context):
        if context == self._context:
            self.panel.verticalScrollBar().setValue(self._positions.get(context, 0))

    def jump(self, category, editor=None):
        if category not in self.sections:
            return False
        if self.pending_numeric():
            self.notice.setText("입력을 확정한 뒤 이동하세요." if self.ko else "Finish editing before navigating.")
            self.notice.show(); self.layout_navigation(); return False
        section = self.sections[category]; section.set_expanded(True)
        if editor is not None:
            self._revealed.add(editor)
            for _, group, _, records in self.panel._group_records:
                if any(widget is editor for _, widget in records):
                    # A deliberate search reveal may expose inactive-mode values;
                    # it never changes the mode/feature enable or its settings.
                    if group is not self._groups["Random Range"]:
                        group.show()
            if self.surface_section.isAncestorOf(editor):
                self.surface_section.set_expanded(True)
            self._disclose()
        target = editor or section.disclosure
        self.panel.widget().layout().activate()
        self.panel.ensureWidgetVisible(target, 8, 8)
        if target.isEnabled():
            target.setFocus(Qt.FocusReason.OtherFocusReason)
        self.notice.setText("사용하려면 해당 기능을 켜세요." if self.ko else "Enable the feature to edit this field.")
        self.notice.setVisible(not target.isEnabled())
        self.layout_navigation()
        return True

    def search_properties(self, query):
        terms = query.casefold().split()
        return [(category, editor, label, alias) for category, editor, label, alias in self.registry
                if terms and all(term in (alias + " " + (label.text() if label else "") + " " + editor.toolTip()).casefold() for term in terms)]

    def _search_changed(self, query):
        self._matches = self.search_properties(query)
        with QSignalBlocker(self.results):
            self.results.clear()
            for category, editor, label, alias in self._matches:
                text = label.text() if label else (editor.text() if hasattr(editor, "text") else alias)
                if editor is self.panel.export:
                    text="미리보기 PNG 내보내기 — 선택 입자" if self.ko else "Preview PNG Export — selected emitter"
                self.results.addItem(self.sections[category].title() + " · " + text)
            if query and not self._matches:
                self.results.addItem("일치하는 속성 없음" if self.ko else "No matching properties")
        self.results.setVisible(bool(query)); self.layout_navigation()

    def _activate_result(self, index):
        if 0 <= index < len(self._matches):
            category, editor, _, _ = self._matches[index]
            self.jump(category, editor)

    def _field_visible(self, editor, visible):
        p = self.panel
        for _, _, form, records in p._group_records:
            if any(widget is editor for _, widget in records):
                form.setRowVisible(editor, visible or editor in self._revealed)
                return

    def _disclose(self):
        p = self.panel; shape = p.spawn_shape.currentData()
        for editors, visible in (
            ((p.line_end_x, p.line_end_y), shape == "line"),
            ((p.radius, p.start_angle, p.end_angle), shape == "circle"),
            ((p.box_width, p.box_height), shape == "box"),
            ((p.gravity_strength,), p.gravity_enabled.isChecked()),
            ((p.drag_strength,), p.drag_enabled.isChecked()),
            ((p.noise_strength, p.noise_frequency), p.noise_enabled.isChecked()),
            ((p.emission_period_frames,), p.emission_cycle_mode.currentData() == "cyclic_steady"),
        ):
            for editor in editors:
                self._field_visible(editor, visible)
        p.scale_point_editor.setVisible(p.scale_lifetime_enabled.isChecked() or any(p.scale_point_editor is w or p.scale_point_editor.isAncestorOf(w) for w in self._revealed))
        p.color_point_editor.setVisible(p.color_lifetime_enabled.isChecked() or any(p.color_point_editor is w or p.color_point_editor.isAncestorOf(w) for w in self._revealed))
        for editor in self._revealed:
            if editor in p.trail_form.rows:
                p.trail_form.set_field_visible(editor, True)
            if editor in p.sub_form.rows:
                p.sub_form.set_field_visible(editor, True)

    def sync(self, *args):
        if self._syncing:
            return
        self._syncing = True
        try:
            p = self.panel; ko = self.ko
            self._readable_labels()
            for key, section in self.sections.items():
                section.set_language(ko)
                # Retain UX-1's localized Trail/Sub-emitter API titles.
                if key not in {"trail", "events"}:
                    section.setTitle(CATEGORIES[key][int(ko)])
            emission = p.emission_cycle_mode.currentText()
            emission += f" {p.emission_period_frames.value()}f" if p.emission_cycle_mode.currentData() == "cyclic_steady" else " · " + p.emission_mode.currentText()
            summaries = {
                "source": f"{p.clip.currentText()} · {p.clip_speed_min.value():g}–{p.clip_speed_max.value():g}×",
                "emit": f"{p.count_min.value()}–{p.count_max.value()} · {emission} · {p.spawn_shape.currentText()}",
                "motion": " · ".join([p.motion_mode.currentText()] + [name for enabled, name in ((p.gravity_enabled, "중력" if ko else "Gravity"), (p.drag_enabled, "감쇠" if ko else "Drag"), (p.noise_enabled, "노이즈" if ko else "Noise")) if enabled.isChecked()]),
                "look": " · ".join(["Opacity / 불투명도" if ko else "Opacity"] + (["Scale / 크기" if ko else "Scale"] if p.scale_lifetime_enabled.isChecked() else []) + (["RGB"] if p.color_lifetime_enabled.isChecked() else [])),
                "rendering": p.blend_mode.currentText(),
            }
            layer = p.transform_panel.layer
            if layer is not None:
                animated = any(track.keyframes for track in layer.layer_transform.tracks.values())
                surface_animated = any(track.keyframes for track in layer.surface_transform.tracks.values())
                surface = " · ".join((["Animated / 애니메이션" if ko else "Animated"] if surface_animated else []) + (["Nonidentity / 변환 있음" if ko else "Nonidentity"] if not layer.surface_transform.is_identity() else [])) or ("기본값" if ko else "Identity")
                summaries["transform"] = ("적용" if ko else "Enabled") if layer.advanced_transform_enabled else ("우회" if ko else "Bypassed")
                summaries["transform"] += " · " + ("Animated" if animated else f"Z {p.transform_panel.fields['rotation_z'].value():g}°") + " · Surface: " + surface
                if not layer.layer_transform.is_identity():
                    summaries["transform"] += " · " + ("시스템 변환 있음" if ko else "System nonidentity")
                self.surface_section.set_summary(surface)
                self.selection.setText(f"{layer.name} · " + ("입자" if ko else "Particle") + (" · 🔒" if layer.locked else "") + f" · {p.parent_layer.currentText()}")
            else:
                self.selection.setText("선택 없음" if ko else "No selection")
            self.surface_section.setTitle("표면 변환 (호환)" if ko else "Surface (Compatibility)")
            self.surface_section.set_language(ko)
            for key, text in summaries.items():
                self.sections[key].set_summary(text)
            self._disclose()
            messages = [("emit", p.cycle_status), ("trail", p.trail_status), ("events", p.sub_status)]
            issues = [(key, status.text()) for key, status in messages if status.text() and status.severity != "info"]
            point_messages = [editor.status.text() for editor in p._point_editors if editor.status.text()]
            if point_messages:
                issues.append(("look", "\n".join(point_messages)))
            for key in ("emit", "look"):
                text = next((text for category, text in issues if category == key), "")
                self.sections[key].set_warning(text, "error")
            with QSignalBlocker(self.warnings), QSignalBlocker(self.jump_combo):
                current = self.jump_combo.currentData(); self.jump_combo.clear()
                for key in CATEGORIES:
                    self.jump_combo.addItem(CATEGORIES[key][int(ko)], key)
                self.jump_combo.setCurrentIndex(max(0, self.jump_combo.findData(current)))
                self.warnings.clear()
                self.warnings.addItem((f"경고 {len(issues)}개 — 위치 선택" if ko else f"{len(issues)} warnings — choose location"), None)
                for key, text in issues:
                    self.warnings.addItem(CATEGORIES[key][int(ko)] + " · " + text, key)
            self.warnings.setVisible(bool(issues))
            self.jump_combo.setAccessibleName("범주 이동" if ko else "Category jump")
            self.jump_combo.setToolTip("범주를 펼치고 이동합니다. 설정을 바꾸지 않습니다." if ko else "Expand and reveal a category without changing settings.")
            self.search.setPlaceholderText("속성 검색…" if ko else "Search properties…")
            self.search.setAccessibleName(self.search.placeholderText())
            self.results.setAccessibleName("검색 결과" if ko else "Search results")
            self.warnings.setAccessibleName("경고 위치" if ko else "Warning locations")
            self.layout_navigation()
        finally:
            self._syncing = False

    def layout_navigation(self):
        width = max(1, self.panel.width() - 4)
        height = self.navigation.layout().totalHeightForWidth(width)
        height = max(self.navigation.sizeHint().height(), height)
        if self.panel.viewportMargins().top() != height:
            self.panel.setViewportMargins(0, height, 0, 0)
        self.navigation.setGeometry(2, 2, width, height)
        self.navigation.raise_()

    def _readable_labels(self):
        p = self.panel; ko = self.ko
        self.source_timing_help.setText((KO if ko else EN)["timing.source_speed_help"])
        labels = {p.clip_speed_min: ("Min Speed", "최소 속도"), p.clip_speed_max: ("Max Speed", "최대 속도"),
                  p.random_start_frame: ("Random Start", "시작 무작위"),
                  p.scale_lifetime_enabled: ("Scale Curve", "크기 곡선"), p.color_lifetime_enabled: ("RGB Curve", "RGB 곡선")}
        for _, _, form, records in p._group_records:
            for _, editor in records:
                if editor in labels:form.labelForField(editor).setText(labels[editor][int(ko)])
        for combo, names in ((p.emission_mode, {"burst": ("Burst", "한꺼번에"), "over_time": ("Over Time", "나눠 방출")}),
            (p.spawn_shape, {"point": ("Point", "점"), "line": ("Line", "선"), "circle": ("Ring / Arc", "원둘레 / 호"), "box": ("Box", "상자 영역")}),
            (p.direction_mode, {"fixed": ("Fixed Direction", "방향 지정"), "radial_outward": ("Radial Outward", "바깥 방사형")})):
            for i in range(combo.count()):combo.setItemText(i, names[combo.itemData(i)][int(ko)])
        if p.parent_layer.count() and p.parent_layer.itemData(0) is None:
            p.parent_layer.setItemText(0, "부모 없음" if ko else "No Parent")
        self.action_area.setTitle("작업" if ko else "Actions")
        self.action_help.setText("아래 내보내기는 선택 입자의 미리보기입니다. 전체 Effect PNG는 전역 내보내기 메뉴를 사용하세요." if ko else "Export below writes the selected particle preview. Use the Export menu for the full Effect PNG sequence.")

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.LayoutRequest and not self._queued:
            self._queued = True
            QTimer.singleShot(0, self._sync_queued)
        return False

    def _sync_queued(self):
        self._queued = False
        self.sync()
