"""Scrollable properties for the Particle System flow."""
from __future__ import annotations
from random import SystemRandom
from PySide6.QtCore import QSignalBlocker, Signal, Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget
from copy import deepcopy
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings, ParticleMotionSettings
from app.models.property_registry import NUMERIC_PROPERTY_SPECS
from .focus_wheel_widgets import FocusWheelComboBox, ScrollSafeDoubleSpinBox, ScrollSafeSpinBox
from .tooltip_helper import apply_tooltip
from .resource_layer_transform_panel import ResourceLayerTransformPanel

class ParticlePropertiesPanel(QScrollArea):
    draft_changed = Signal(str, object); refresh_requested = Signal(str); bake_requested = Signal(str, object)
    revert_requested = Signal(str); export_requested = Signal(str); gizmo_mode_changed = Signal(str)
    mode_changed = Signal(str, str)
    motion_reset_requested = Signal(str, object)
    motion_keyframe_requested = Signal(str, str, float, str)
    motion_keyframe_delete_requested = Signal(str, str, int)
    transform_changed = Signal(str, object);transform_keyframe_requested = Signal(str, str, int, float, str);transform_keyframe_delete_requested = Signal(str, str, int);transform_gizmo_changed = Signal(str, str)
    name_changed = Signal(str, str)
    def __init__(self, parent=None):
        super().__init__(parent); self.setWidgetResizable(True); self.setMinimumWidth(0); self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.emitter_id = None; self._loading = False; self._localization = None; self._motion_tracks={};self._motion_revision=0;self._motion_frame=0;self._motion_base_values={}
        body=QWidget();body.setObjectName("particleInspectorContent");body.setMinimumWidth(0);body.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); self.layout=QVBoxLayout(body);self.layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.title=QLabel("Resource Layer");self.title.setMinimumWidth(0);self.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); self.layout.addWidget(self.title);self.resource_layer_id=None;common=QGroupBox("Resource Layer");common.setMinimumWidth(0);common.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);self.common_form=QFormLayout(common);self.common_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);self.name=QLineEdit();self.common_form.addRow("Layer Name",self.name);self.name.editingFinished.connect(self._name_changed);self.mode=FocusWheelComboBox();self.mode.setMinimumWidth(0);self.mode.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);self.mode.addItem("Single","single");self.mode.addItem("Particle Emission","particle");self.common_form.addRow("Placement Mode",self.mode);self.mode_label=self.common_form.labelForField(self.mode);self.mode_label.setMinimumWidth(0);self.mode_label.setMaximumWidth(112);self.mode_label.setWordWrap(True);self.mode_label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred);self.mode_label.setBuddy(self.mode);self.layout.addWidget(common);self.mode_help=QLabel("Emit multiple instances of the same resource with direction, speed, and lifetime.");self.mode_help.setWordWrap(True);self.mode_help.setMinimumWidth(0);self.mode_help.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);self.layout.addWidget(self.mode_help);self.mode.currentIndexChanged.connect(self._mode_changed);self._group_records=[]
        self.transform_panel=ResourceLayerTransformPanel();self.transform_panel.transform_changed.connect(self.transform_changed);self.transform_panel.keyframe_requested.connect(self.transform_keyframe_requested);self.transform_panel.keyframe_delete_requested.connect(self.transform_keyframe_delete_requested);self.transform_panel.gizmo_mode_changed.connect(self.transform_gizmo_changed)
        self.clip=FocusWheelComboBox(); self.output_frame_count=self._i(1,512); self.start_frame=self._i(0,511)
        self.emission_mode=self._combo(("burst","over_time")); self.count_min=self._i(0,4096); self.count_max=self._i(0,4096); self.emission_duration=self._i(1,512)
        self.spawn_shape=self._combo(("point","line","circle","box")); self.origin_x=self._n(-4096,4096); self.origin_y=self._n(-4096,4096); self.line_end_x=self._n(-4096,4096); self.line_end_y=self._n(-4096,4096); self.radius=self._n(0,4096); self.box_width=self._n(0,4096); self.box_height=self._n(0,4096); self.start_angle=self._n(-3600,3600); self.end_angle=self._n(-3600,3600)
        self.direction_mode=self._combo(("fixed","radial_outward")); self.direction_degrees=self._n(-3600,3600); self.direction_spread_degrees=self._n(0,360)
        self.motion_mode=self._combo(("linear","orbit","helix"));self.motion_center_x=self._n(-4096,4096);self.motion_center_y=self._n(-4096,4096);self.motion_center_z=self._n(-4096,4096)
        self.motion_radius_start=self._n(0,4096);self.motion_radius_end=self._n(0,4096);self.motion_ellipse_x=self._n(0,16);self.motion_ellipse_y=self._n(0,16);self.motion_ellipse_x.setValue(1);self.motion_ellipse_y.setValue(1)
        self.motion_start_angle=self._n(-36000,36000);self.motion_turns=self._n(-100,100);self.motion_turns.setValue(1);self.motion_direction=self._combo(("clockwise","counter_clockwise"));self.motion_phase_spread=self._n(0,3600);self.motion_plane_rotation=self._n(-3600,3600)
        self.motion_helix_axis=self._combo(("x","y","z"));self.motion_axis_start=self._n(-4096,4096);self.motion_axis_end=self._n(-4096,4096);self.motion_perspective=self._bounded("normalized.perspective")
        self.motion_radius_easing=self._combo(("Linear","Ease In","Ease Out","Ease In/Out"));self.motion_angle_easing=self._combo(("Linear","Ease In","Ease Out","Ease In/Out"));self.motion_axis_easing=self._combo(("Linear","Ease In","Ease Out","Ease In/Out"));self.reset_motion=QPushButton("Reset Motion")
        self.motion_keyframe_property=self._combo(("center_x","center_y","center_z","radius_start","radius_end","start_angle_degrees","turns","axis_start","axis_end","perspective_strength"));self.motion_keyframe_easing=self._combo(("Linear","Ease In","Ease Out","Ease In/Out"));self.add_motion_keyframe=QPushButton("Add Keyframe")
        self.speed_min=self._n(0,1024); self.speed_max=self._n(0,1024); self.lifetime_min=self._i(1,512); self.lifetime_max=self._i(1,512); self.scale_min=self._n(.01,16); self.scale_max=self._n(.01,16); self.rotation_min=self._n(-3600,3600); self.rotation_max=self._n(-3600,3600); self.angular_velocity_min=self._n(-3600,3600); self.angular_velocity_max=self._n(-3600,3600); self.start_delay_min=self._i(0,512); self.start_delay_max=self._i(0,512); self.clip_speed_min=self._bounded("particle.clip_playback_speed"); self.clip_speed_max=self._bounded("particle.clip_playback_speed"); self.random_start_frame=QCheckBox("Random Start Frame"); self.opacity_start=self._bounded("normalized.opacity"); self.opacity_end=self._bounded("normalized.opacity"); self.seed=self._i(-2147483647,2147483647)
        self.clip_group=self._group("Particle Resource", (("Resource",self.clip),("Output Frames",self.output_frame_count),("Start Frame",self.start_frame)))
        self._group("Emission", (("Mode",self.emission_mode),("Count Min",self.count_min),("Count Max",self.count_max),("Duration",self.emission_duration)))
        self._group("Spawn Shape", (("Shape",self.spawn_shape),("Origin X",self.origin_x),("Origin Y",self.origin_y),("Line End X",self.line_end_x),("Line End Y",self.line_end_y),("Radius",self.radius),("Box Width",self.box_width),("Box Height",self.box_height),("Start Angle",self.start_angle),("End Angle",self.end_angle)))
        self.direction_group=self._group("Direction", (("Mode",self.direction_mode),("Direction",self.direction_degrees),("Spread",self.direction_spread_degrees),("Speed Min",self.speed_min),("Speed Max",self.speed_max)))
        self.motion_basic_group=self._group("Motion Basic", (("Motion Mode",self.motion_mode),("Reset Motion",self.reset_motion)))
        self.motion_center_group=self._group("Orbit Center", (("Center X",self.motion_center_x),("Center Y",self.motion_center_y),("Center Z",self.motion_center_z)))
        self.motion_shape_group=self._group("Orbit Shape", (("Radius Start",self.motion_radius_start),("Radius End",self.motion_radius_end),("Ellipse X",self.motion_ellipse_x),("Ellipse Y",self.motion_ellipse_y),("Start Angle",self.motion_start_angle),("Turns",self.motion_turns),("Direction",self.motion_direction),("Phase Spread",self.motion_phase_spread),("Orbit Plane Rotation",self.motion_plane_rotation)))
        self.motion_helix_group=self._group("Helix", (("Helix Axis",self.motion_helix_axis),("Axis Start",self.motion_axis_start),("Axis End",self.motion_axis_end)))
        self.motion_easing_group=self._group("Motion Interpolation", (("Radius Easing",self.motion_radius_easing),("Angle Easing",self.motion_angle_easing),("Axis Easing",self.motion_axis_easing)))
        self.motion_advanced_group=self._group("Motion Advanced", (("Local Perspective",self.motion_perspective),("Keyframe Property",self.motion_keyframe_property),("Keyframe Easing",self.motion_keyframe_easing),("Add Keyframe",self.add_motion_keyframe)))
        self._group("Random Range", (("Lifetime Min",self.lifetime_min),("Lifetime Max",self.lifetime_max),("Scale Min",self.scale_min),("Scale Max",self.scale_max),("Rotation Min",self.rotation_min),("Rotation Max",self.rotation_max),("Angular Velocity Min",self.angular_velocity_min),("Angular Velocity Max",self.angular_velocity_max),("Start Delay Min",self.start_delay_min),("Start Delay Max",self.start_delay_max),("Clip Speed Min",self.clip_speed_min),("Clip Speed Max",self.clip_speed_max),("Random Start Frame",self.random_start_frame),("Opacity Start",self.opacity_start),("Opacity End",self.opacity_end),("Seed",self.seed)))
        self.layout.addWidget(self.transform_panel)
        self.randomize=QPushButton("Randomize Seed"); self.refresh=QPushButton("Refresh Preview"); self.bake=QPushButton("Bake to Frames"); self.export=QPushButton("Export Preview Sequence…"); self.revert=QPushButton("Revert Changes")
        for w in (self.randomize,self.refresh,self.bake,self.export,self.revert):w.setMinimumWidth(0);w.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);self.layout.addWidget(w)
        self.layout.addStretch(); self.setWidget(body)
        self.controls=[w for w in body.findChildren(QSpinBox)+body.findChildren(QDoubleSpinBox)+body.findChildren(QComboBox) if not self.transform_panel.isAncestorOf(w) and w not in {self.motion_keyframe_property,self.motion_keyframe_easing}]
        for w in self.controls:
            signal=w.currentIndexChanged if isinstance(w,FocusWheelComboBox) else w.valueChanged; signal.connect(self._changed)
        self.random_start_frame.toggled.connect(self._changed); self.motion_mode.currentIndexChanged.connect(self._motion_mode_changed);self.motion_keyframe_property.currentIndexChanged.connect(self._sync_motion_key_state);self.reset_motion.clicked.connect(self._reset_motion);self.add_motion_keyframe.clicked.connect(self._add_motion_keyframe); self.randomize.clicked.connect(self._randomize); self.refresh.clicked.connect(lambda: self.emitter_id and self.refresh_requested.emit(self.emitter_id)); self.bake.clicked.connect(lambda: self.emitter_id and self.bake_requested.emit(self.emitter_id,self.settings())); self.export.clicked.connect(lambda: self.emitter_id and self.export_requested.emit(self.emitter_id)); self.revert.clicked.connect(lambda: self.emitter_id and self.revert_requested.emit(self.emitter_id))
    def _i(self,a,b): w=ScrollSafeSpinBox(); w.setRange(a,b);w.setMinimumWidth(70);w.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed); return w
    def _n(self,a,b): w=ScrollSafeDoubleSpinBox(); w.setRange(a,b); w.setDecimals(3);w.setMinimumWidth(70);w.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed); return w
    def _bounded(self,name):
        spec=NUMERIC_PROPERTY_SPECS[name];w=self._n(spec.minimum,spec.maximum);w.setSingleStep(spec.step);w.setDecimals(spec.decimals);w.setSuffix(spec.suffix);w.setProperty("numericSpec",name);return w
    def _combo(self, values): w=FocusWheelComboBox();w.setMinimumWidth(0);w.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed); [w.addItem(v,v) for v in values]; return w
    def _group(self,title,rows):
        g=QGroupBox(title);g.setMinimumWidth(0);g.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred);f=QFormLayout(g);f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);f.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows);records=[];motion_group=title in {"Motion Basic","Orbit Center","Orbit Shape","Helix","Motion Interpolation","Motion Advanced"}
        for name,w in rows:
            w.setMinimumWidth(0 if isinstance(w,(QComboBox,QCheckBox,QPushButton)) else 70);w.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);f.addRow(name,w);label=f.labelForField(w);label.setMinimumWidth(130 if motion_group else 0);label.setMaximumWidth(130);label.setWordWrap(not motion_group);label.setBuddy(w);label.setVisible(True);label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed);records.append((name,w))
        self._group_records.append((title,g,f,records));self.layout.addWidget(g);return g
    def set_emitter(self, emitter: ParticleEmitter|None, project):
        self._loading=True; self.emitter_id=None if emitter is None else emitter.id; self.clip.clear()
        t=self._localization.text if self._localization else lambda key:{"particle.resource_compositions":"Resource Compositions","resource.static":"Static Resources","resource.animated":"Animated Resources"}.get(key,key)
        self.clip.addItem(t("particle.resource_compositions"),None);self.clip.model().item(self.clip.count()-1).setEnabled(False);composition_heading=self.clip.count()-1
        [self.clip.addItem(c.name,("resource_composition",c.id)) for c in project.resource_compositions]
        self.clip.addItem(t("resource.static"),None);self.clip.model().item(self.clip.count()-1).setEnabled(False);static_heading=self.clip.count()-1
        [self.clip.addItem(c.name,("source_asset",c.id)) for c in project.source_assets]
        self.clip.addItem(t("resource.animated"),None);self.clip.model().item(self.clip.count()-1).setEnabled(False);animated_heading=self.clip.count()-1
        [self.clip.addItem(c.name,("animation_clip",c.id)) for c in project.animation_clips]
        self._heading_indexes=(composition_heading,static_heading,animated_heading)
        self.widget().setEnabled(emitter is not None)
        if emitter: self.set_settings(emitter.settings)
        self._loading=False
    def set_resource_layer(self, layer, project):
        self.resource_layer_id=None if layer is None else layer.id
        self.set_emitter(None if layer is None else layer.as_particle_emitter(),project)
        self.transform_panel.set_layer(layer,getattr(project,"_current_effect_frame",0))
        self._motion_frame=int(getattr(project,"_current_effect_frame",0))
        if layer is not None:
            self.name.setText(layer.name)
            self._set_motion_frame(layer.particle_settings.motion,self._motion_frame)
        self._loading=True
        if layer is not None:
            self.mode.setCurrentIndex(max(0,self.mode.findData(layer.placement_mode)))
            if layer.resource_composition_id:
                self.clip.clear();[self.clip.addItem(item.name,("resource_composition",item.id)) for item in project.resource_compositions];self.clip.setCurrentIndex(max(0,self.clip.findData(("resource_composition",layer.resource_composition_id))))
        self._loading=False
    def _mode_changed(self,*args):
        mode=str(self.mode.currentData());self.mode_help.setText(self._localization.text("resource_layer.single_help" if mode=="single" else "resource_layer.particle_help") if self._localization else ("Place one resource directly in the Effect Composition." if mode=="single" else "Emit multiple instances of the same resource with direction, speed, and lifetime."))
        if not self._loading and self.resource_layer_id:self.mode_changed.emit(self.resource_layer_id,mode)
    def set_locked(self,locked):
        if self.widget():self.widget().setEnabled(not bool(locked))
    def _name_changed(self):
        if not self._loading and self.resource_layer_id and self.name.text().strip():self.name_changed.emit(self.resource_layer_id,self.name.text().strip())
    def set_settings(self,s):
        self._loading=True
        self._motion_tracks=deepcopy(s.motion.tracks);self._motion_revision=s.motion.revision;self._motion_base_values={name:float(getattr(s.motion,name)) for name in self._motion_control_map()}
        mapping={"clip":"clip_asset_id","count_min":"particle_count_min","count_max":"particle_count_max"}
        for name in ("clip","output_frame_count","start_frame","emission_mode","count_min","count_max","emission_duration","spawn_shape","origin_x","origin_y","line_end_x","line_end_y","radius","box_width","box_height","start_angle","end_angle","direction_mode","direction_degrees","direction_spread_degrees","speed_min","speed_max","lifetime_min","lifetime_max","scale_min","scale_max","rotation_min","rotation_max","angular_velocity_min","angular_velocity_max","start_delay_min","start_delay_max","clip_speed_min","clip_speed_max","opacity_start","opacity_end","seed"):
            w=getattr(self,name); value=(s.resource_type,s.resource_id) if name=="clip" else getattr(s,mapping.get(name,name))
            if isinstance(w,FocusWheelComboBox):
                index=w.findData(value)
                if name=="clip" and index<0:
                    index=next((i for i in range(w.count()) if w.itemData(i) is not None and tuple(w.itemData(i))==value),-1)
                w.setCurrentIndex(max(0,index))
            else:w.setValue(value)
        self.random_start_frame.setChecked(s.random_start_frame); self._loading=False
        motion=s.motion
        motion_mapping={"motion_mode":motion.mode,"motion_center_x":motion.center_x,"motion_center_y":motion.center_y,"motion_center_z":motion.center_z,"motion_radius_start":motion.radius_start,"motion_radius_end":motion.radius_end,"motion_ellipse_x":motion.ellipse_scale_x,"motion_ellipse_y":motion.ellipse_scale_y,"motion_start_angle":motion.start_angle_degrees,"motion_turns":motion.turns,"motion_direction":motion.direction,"motion_phase_spread":motion.phase_spread_degrees,"motion_plane_rotation":motion.orbit_plane_rotation_degrees,"motion_helix_axis":motion.helix_axis,"motion_axis_start":motion.axis_start,"motion_axis_end":motion.axis_end,"motion_radius_easing":motion.radius_easing,"motion_angle_easing":motion.angle_easing,"motion_axis_easing":motion.axis_easing,"motion_perspective":motion.perspective_strength}
        self._loading=True
        for name,value in motion_mapping.items():
            w=getattr(self,name);w.setCurrentIndex(max(0,w.findData(value))) if isinstance(w,FocusWheelComboBox) else w.setValue(value)
        self._loading=False;self._update_motion_visibility();self._sync_motion_key_state()

    @staticmethod
    def _motion_control_map():
        return {"center_x":"motion_center_x","center_y":"motion_center_y","center_z":"motion_center_z","radius_start":"motion_radius_start","radius_end":"motion_radius_end","start_angle_degrees":"motion_start_angle","turns":"motion_turns","axis_start":"motion_axis_start","axis_end":"motion_axis_end","perspective_strength":"motion_perspective"}

    def _set_motion_frame(self,motion,frame):
        self._motion_tracks=deepcopy(motion.tracks);self._motion_revision=motion.revision;self._motion_base_values={name:float(getattr(motion,name)) for name in self._motion_control_map()};self._loading=True
        for property_id,control_name in self._motion_control_map().items():
            control=getattr(self,control_name);control.setValue(motion.value(property_id,frame));control.setEnabled(True)
        self._loading=False;self._sync_motion_key_state()

    def _sync_motion_key_state(self,*args):
        property_id=str(self.motion_keyframe_property.currentData());track=self._motion_tracks.get(property_id);current=bool(track and track.has_keyframe(self._motion_frame));animated=bool(track and track.keyframes);self.add_motion_keyframe.setText("◆ Delete Key" if current else "◇ Add Key");self.add_motion_keyframe.setProperty("keyState","current_key" if current else "animated_no_key" if animated else "static")
        if self._localization:
            ko=self._localization.language=="ko";self.add_motion_keyframe.setToolTip(("현재 프레임에 키가 있습니다. 클릭하면 이 키를 삭제합니다." if ko else "A keyframe exists at the current frame. Click to delete it.") if current else (("이 속성은 애니메이션 중입니다. 값을 변경하면 현재 프레임에 키프레임이 자동으로 추가됩니다." if ko else "This property is animated. Changing the value adds a keyframe at the current frame.") if animated else ("첫 키는 이 버튼으로 명시적으로 추가합니다." if ko else "Use this button to add the first key explicitly.")))
    def settings(self):
        def v(name): w=getattr(self,name); return w.currentData() if isinstance(w,FocusWheelComboBox) else w.value()
        resource=v("clip") or ("animation_clip","")
        motion=ParticleMotionSettings(mode=str(v("motion_mode")),center_x=v("motion_center_x"),center_y=v("motion_center_y"),center_z=v("motion_center_z"),radius_start=v("motion_radius_start"),radius_end=v("motion_radius_end"),ellipse_scale_x=v("motion_ellipse_x"),ellipse_scale_y=v("motion_ellipse_y"),start_angle_degrees=v("motion_start_angle"),turns=v("motion_turns"),direction=str(v("motion_direction")),phase_spread_degrees=v("motion_phase_spread"),orbit_plane_rotation_degrees=v("motion_plane_rotation"),helix_axis=str(v("motion_helix_axis")),axis_start=v("motion_axis_start"),axis_end=v("motion_axis_end"),perspective_strength=v("motion_perspective"),radius_easing=str(v("motion_radius_easing")),angle_easing=str(v("motion_angle_easing")),axis_easing=str(v("motion_axis_easing")),tracks=deepcopy(self._motion_tracks),revision=self._motion_revision)
        for property_id,value in self._motion_base_values.items():
            if property_id in motion.tracks and motion.tracks[property_id].keyframes:setattr(motion,property_id,value)
        return ParticleEmitterSettings(clip_asset_id=str(resource[1]),resource_type=str(resource[0]),output_frame_count=v("output_frame_count"),start_frame=v("start_frame"),emission_mode=str(v("emission_mode")),particle_count_min=v("count_min"),particle_count_max=v("count_max"),emission_duration=v("emission_duration"),spawn_shape=str(v("spawn_shape")),origin_x=v("origin_x"),origin_y=v("origin_y"),line_end_x=v("line_end_x"),line_end_y=v("line_end_y"),radius=v("radius"),box_width=v("box_width"),box_height=v("box_height"),start_angle=v("start_angle"),end_angle=v("end_angle"),direction_mode=str(v("direction_mode")),direction_degrees=v("direction_degrees"),direction_spread_degrees=v("direction_spread_degrees"),speed_min=v("speed_min"),speed_max=v("speed_max"),lifetime_min=v("lifetime_min"),lifetime_max=v("lifetime_max"),scale_min=v("scale_min"),scale_max=v("scale_max"),rotation_min=v("rotation_min"),rotation_max=v("rotation_max"),angular_velocity_min=v("angular_velocity_min"),angular_velocity_max=v("angular_velocity_max"),start_delay_min=v("start_delay_min"),start_delay_max=v("start_delay_max"),clip_speed_min=v("clip_speed_min"),clip_speed_max=v("clip_speed_max"),random_start_frame=self.random_start_frame.isChecked(),opacity_start=v("opacity_start"),opacity_end=v("opacity_end"),seed=v("seed"),motion=motion)
    def _motion_mode_changed(self,*args):
        self._update_motion_visibility();self._changed()
    def _update_motion_visibility(self):
        mode=str(self.motion_mode.currentData());self.direction_group.setEnabled(mode=="linear")
        active=mode in {"orbit","helix"}
        for group in (self.motion_center_group,self.motion_shape_group,self.motion_easing_group,self.motion_advanced_group):group.setVisible(active)
        self.motion_helix_group.setVisible(mode=="helix")
        self.motion_axis_easing.setVisible(mode=="helix")
        form=self.motion_easing_group.layout();label=form.labelForField(self.motion_axis_easing) if isinstance(form,QFormLayout) else None
        if label is not None:label.setVisible(mode=="helix")
    def _reset_motion(self):
        if self._loading:return
        current=self.settings();current.motion.reset_base();self.set_settings(current)
        if self.emitter_id:self.motion_reset_requested.emit(self.emitter_id,current);self.draft_changed.emit(self.emitter_id,current)
    def _add_motion_keyframe(self):
        if not self.emitter_id:return
        property_id=str(self.motion_keyframe_property.currentData());control={"center_x":self.motion_center_x,"center_y":self.motion_center_y,"center_z":self.motion_center_z,"radius_start":self.motion_radius_start,"radius_end":self.motion_radius_end,"start_angle_degrees":self.motion_start_angle,"turns":self.motion_turns,"axis_start":self.motion_axis_start,"axis_end":self.motion_axis_end,"perspective_strength":self.motion_perspective}[property_id]
        track=self._motion_tracks.get(property_id)
        if track and track.has_keyframe(self._motion_frame):self.motion_keyframe_delete_requested.emit(self.emitter_id,property_id,self._motion_frame)
        else:self.motion_keyframe_requested.emit(self.emitter_id,property_id,float(control.value()),str(self.motion_keyframe_easing.currentData()))
    def _changed(self,*args):
        if not self._loading and self.emitter_id:
            changed=self.sender()
            if changed is self.clip_speed_min and self.clip_speed_min.value()>self.clip_speed_max.value():
                with QSignalBlocker(self.clip_speed_max):self.clip_speed_max.setValue(self.clip_speed_min.value())
            elif changed is self.clip_speed_max and self.clip_speed_max.value()<self.clip_speed_min.value():
                with QSignalBlocker(self.clip_speed_min):self.clip_speed_min.setValue(self.clip_speed_max.value())
            reverse={getattr(self,name):property_id for property_id,name in self._motion_control_map().items()};property_id=reverse.get(self.sender())
            if property_id:
                track=self._motion_tracks.get(property_id);control=self.sender()
                if track and track.keyframes:
                    if float(track.evaluate(self._motion_frame))==float(control.value()):return
                    key=track.keyframe_at(self._motion_frame)
                    if key is None:track.set_keyframe(self._motion_frame,float(control.value()),"Linear")
                    else:key.value=float(control.value())
                else:self._motion_base_values[property_id]=float(control.value())
            if self.sender() in {self.motion_mode,self.motion_center_x,self.motion_center_y,self.motion_center_z,self.motion_radius_start,self.motion_radius_end,self.motion_ellipse_x,self.motion_ellipse_y,self.motion_start_angle,self.motion_turns,self.motion_direction,self.motion_phase_spread,self.motion_plane_rotation,self.motion_helix_axis,self.motion_axis_start,self.motion_axis_end,self.motion_radius_easing,self.motion_angle_easing,self.motion_axis_easing,self.motion_perspective}:self._motion_revision+=1
            self.draft_changed.emit(self.emitter_id,self.settings())
    def _randomize(self): self.seed.setValue(SystemRandom().randint(-2147483647,2147483647))
    def retranslate_ui(self,l):
        self._localization=l; t=l.text; self.title.setText(t("resource_layer.title"));self.common_form.labelForField(self.name).setText(t("resource_layer.name"));self.mode_label.setText(t("resource_layer.placement_mode"));self.mode.setItemText(0,t("resource_layer.single"));self.mode.setItemText(1,t("resource_layer.particle"));self.mode_help.setText(t("resource_layer.single_help" if self.mode.currentData()=="single" else "resource_layer.particle_help"));apply_tooltip(self.mode,l,"tooltip.resource_layer.mode",status=False);self.transform_panel.retranslate_ui(l); self.randomize.setText(t("particle.randomize_seed")); self.refresh.setText(t("effects.refresh_preview")); self.bake.setText(t("effects.bake")); self.export.setText(t("effects.export_preview")); self.revert.setText(t("effects.revert"))
        group_keys={"Particle Resource":"particle.resource","Emission":"particle.emission","Spawn Shape":"particle.spawn_shape","Direction":"particle.direction","Motion Basic":"particle.motion_basic","Orbit Center":"particle.motion_center","Orbit Shape":"particle.motion_shape","Helix":"particle.motion_helix","Motion Interpolation":"particle.motion_interpolation","Motion Advanced":"particle.motion_advanced","Random Range":"particle.random_range"}
        field_keys={"Resource":"particle.resource_label","Output Frames":"particle.output_frames","Start Frame":"particle.start_frame","Mode":"particle.mode","Count Min":"particle.count_min","Count Max":"particle.count_max","Duration":"particle.duration","Shape":"particle.shape","Origin X":"particle.origin_x","Origin Y":"particle.origin_y","Line End X":"particle.line_end_x","Line End Y":"particle.line_end_y","Radius":"particle.radius","Box Width":"particle.box_width","Box Height":"particle.box_height","Start Angle":"particle.motion_start_angle","End Angle":"particle.end_angle","Direction":"particle.motion_direction","Spread":"particle.spread","Speed Min":"particle.speed_min","Speed Max":"particle.speed_max","Motion Mode":"particle.motion_mode","Center X":"particle.motion_center_x","Center Y":"particle.motion_center_y","Center Z":"particle.motion_center_z","Radius Start":"particle.motion_radius_start","Radius End":"particle.motion_radius_end","Ellipse X":"particle.motion_ellipse_x","Ellipse Y":"particle.motion_ellipse_y","Turns":"particle.motion_turns","Phase Spread":"particle.motion_phase_spread","Orbit Plane Rotation":"particle.motion_plane_rotation","Helix Axis":"particle.motion_helix_axis","Axis Start":"particle.motion_axis_start","Axis End":"particle.motion_axis_end","Radius Easing":"particle.motion_radius_easing","Angle Easing":"particle.motion_angle_easing","Axis Easing":"particle.motion_axis_easing","Local Perspective":"particle.motion_perspective","Keyframe Property":"particle.motion_keyframe_property","Keyframe Easing":"particle.motion_keyframe_easing","Add Keyframe":"particle.motion_add_keyframe","Reset Motion":"particle.motion_reset","Lifetime Min":"particle.lifetime_min","Lifetime Max":"particle.lifetime_max","Scale Min":"particle.scale_min","Scale Max":"particle.scale_max","Rotation Min":"particle.rotation_min","Rotation Max":"particle.rotation_max","Angular Velocity Min":"particle.angular_velocity_min","Angular Velocity Max":"particle.angular_velocity_max","Start Delay Min":"particle.start_delay_min","Start Delay Max":"particle.start_delay_max","Clip Speed Min":"particle.clip_speed_min","Clip Speed Max":"particle.clip_speed_max","Random Start Frame":"particle.random_start_frame","Opacity Start":"particle.opacity_start","Opacity End":"particle.opacity_end","Seed":"particle.seed"}
        for title,group,form,records in self._group_records:
            group.setTitle(t(group_keys[title]))
            tooltip_key={"Particle Resource":"tooltip.particle.resource","Emission":"tooltip.particle.emission","Spawn Shape":"tooltip.particle.spawn","Direction":"tooltip.particle.direction","Motion Basic":"tooltip.particle.motion","Orbit Center":"tooltip.particle.motion_center","Orbit Shape":"tooltip.particle.motion_shape","Helix":"tooltip.particle.motion_helix","Motion Interpolation":"tooltip.particle.motion_interpolation","Motion Advanced":"tooltip.particle.motion_advanced","Random Range":"tooltip.particle.random"}[title]
            for name,widget in records:form.labelForField(widget).setText(t(field_keys[name]));apply_tooltip(widget,l,"tooltip.particle."+{"Center X":"motion_center","Center Y":"motion_center","Center Z":"motion_center","Radius Start":"motion_radius_start","Radius End":"motion_radius_end","Ellipse X":"motion_ellipse","Ellipse Y":"motion_ellipse","Start Angle":"motion_start_angle","Turns":"motion_turns","Direction":"motion_direction","Phase Spread":"motion_phase_spread","Orbit Plane Rotation":"motion_plane_rotation","Helix Axis":"motion_helix_axis","Axis Start":"motion_axis_range","Axis End":"motion_axis_range","Local Perspective":"motion_perspective"}.get(name,tooltip_key.removeprefix("tooltip.particle.")),status=False)
        combo_labels={self.motion_mode:{"linear":"particle.motion_linear","orbit":"particle.motion_orbit","helix":"particle.motion_helix_mode"},self.motion_direction:{"clockwise":"particle.motion_clockwise","counter_clockwise":"particle.motion_counter_clockwise"},self.motion_helix_axis:{"x":"particle.axis_x","y":"particle.axis_y","z":"particle.axis_z"}}
        keyframe_labels={"center_x":"particle.motion_center_x","center_y":"particle.motion_center_y","center_z":"particle.motion_center_z","radius_start":"particle.motion_radius_start","radius_end":"particle.motion_radius_end","start_angle_degrees":"particle.motion_start_angle","turns":"particle.motion_turns","axis_start":"particle.motion_axis_start","axis_end":"particle.motion_axis_end","perspective_strength":"particle.motion_perspective"}
        for combo,mapping in combo_labels.items():
            for index in range(combo.count()):combo.setItemText(index,t(mapping[str(combo.itemData(index))]))
        for index in range(self.motion_keyframe_property.count()):self.motion_keyframe_property.setItemText(index,t(keyframe_labels[str(self.motion_keyframe_property.itemData(index))]))
        for widget,suffix in ((self.motion_start_angle,"°"),(self.motion_plane_rotation,"°"),(self.motion_phase_spread,"°")):widget.setSuffix(suffix)
        self.motion_turns.setSuffix(" "+t("particle.motion_turns_unit"))
        self._update_motion_visibility()
        self._sync_motion_key_state()
        self.random_start_frame.setText("")
        apply_tooltip(self.clip,l,"tooltip.particle.resource",status=False);apply_tooltip(self.output_frame_count,l,"tooltip.particle.output",status=False);apply_tooltip(self.random_start_frame,l,"tooltip.particle.random_start",status=False)
        apply_tooltip(self.clip_speed_min,l,"tooltip.particle.clip_speed_range",status=False);apply_tooltip(self.clip_speed_max,l,"tooltip.particle.clip_speed_range",status=False)
        for widget,key in ((self.randomize,"tooltip.particle.randomize"),(self.refresh,"tooltip.particle.preview"),(self.bake,"tooltip.particle.bake"),(self.export,"tooltip.particle.export"),(self.revert,"tooltip.particle.revert")):apply_tooltip(widget,l,key)
        if hasattr(self,"_heading_indexes"):
            for index,key in zip(self._heading_indexes,("particle.resource_compositions","resource.static","resource.animated")):self.clip.setItemText(index,t(key))
